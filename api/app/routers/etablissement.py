import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from PIL import Image
import io

from ..db import get_cursor
from ..deps import get_administratif_connecte
from ..schemas import (EtablissementInfo, ModificationEtablissement, ReferentielPedagogique,
                        CreationReferentiel, ChapitreCalendrier, CreationChapitre,
                        AdministratifConnecte)

router = APIRouter(prefix="/administration/etablissement", tags=["etablissement"])

# Répertoire de stockage local des fichiers uploadés (logo, règlement).
# En V1 : disque du serveur, servi en statique par FastAPI (voir main.py).
# Suffisant pour un logo + un PDF par établissement — à revoir seulement si
# le volume de fichiers stockés grandit beaucoup (alors : stockage objet
# externe type S3/R2, mais inutile de complexifier avant d'en avoir besoin).
DOSSIER_UPLOADS = Path(__file__).resolve().parent.parent.parent / "uploads"


def _dossier_etablissement(etablissement_id: str) -> Path:
    dossier = DOSSIER_UPLOADS / etablissement_id
    dossier.mkdir(parents=True, exist_ok=True)
    return dossier


@router.get("", response_model=EtablissementInfo)
def obtenir_etablissement(admin: AdministratifConnecte = Depends(get_administratif_connecte)):
    with get_cursor() as cur:
        cur.execute(
            "SELECT id, nom, pays, ville, logo_url, reglement_url FROM etablissements WHERE id = %s",
            (admin.etablissement_id,),
        )
        row = cur.fetchone()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Établissement introuvable")
    id_, nom, pays, ville, logo_url, reglement_url = row
    return EtablissementInfo(id=str(id_), nom=nom, pays=pays, ville=ville,
                               logo_url=logo_url, reglement_url=reglement_url)


@router.patch("", response_model=EtablissementInfo)
def modifier_etablissement(
    payload: ModificationEtablissement,
    admin: AdministratifConnecte = Depends(get_administratif_connecte),
):
    champs = {k: v for k, v in payload.model_dump().items() if v is not None}
    if not champs:
        raise HTTPException(status_code=422, detail="Aucune modification fournie")

    with get_cursor(commit=True) as cur:
        assignations = ", ".join(f"{k} = %s" for k in champs)
        cur.execute(f"UPDATE etablissements SET {assignations} WHERE id = %s",
                    (*champs.values(), admin.etablissement_id))
        cur.execute(
            "SELECT id, nom, pays, ville, logo_url, reglement_url FROM etablissements WHERE id = %s",
            (admin.etablissement_id,),
        )
        id_, nom, pays, ville, logo_url, reglement_url = cur.fetchone()

    return EtablissementInfo(id=str(id_), nom=nom, pays=pays, ville=ville,
                               logo_url=logo_url, reglement_url=reglement_url)


@router.post("/logo", response_model=EtablissementInfo)
async def uploader_logo(
    fichier: UploadFile = File(...),
    admin: AdministratifConnecte = Depends(get_administratif_connecte),
):
    contenu = await fichier.read()

    # On ne fait jamais confiance à l'extension ou au Content-Type déclarés
    # par le navigateur — on ouvre réellement le fichier avec Pillow pour
    # vérifier que c'est une vraie image, et on la ré-encode en PNG propre
    # (élimine toute donnée cachée dans le fichier d'origine, standardise
    # le format servi ensuite).
    try:
        image = Image.open(io.BytesIO(contenu))
        image.verify()
        image = Image.open(io.BytesIO(contenu)).convert("RGBA")
    except Exception:
        raise HTTPException(status_code=422, detail="Fichier image invalide (formats acceptés : PNG, JPEG, WebP...)")

    image.thumbnail((512, 512))  # un logo n'a jamais besoin d'être plus grand

    dossier = _dossier_etablissement(admin.etablissement_id)
    chemin = dossier / "logo.png"
    image.save(chemin, format="PNG")

    logo_url = f"/uploads/{admin.etablissement_id}/logo.png"
    with get_cursor(commit=True) as cur:
        cur.execute("UPDATE etablissements SET logo_url = %s WHERE id = %s", (logo_url, admin.etablissement_id))
        cur.execute(
            "SELECT id, nom, pays, ville, logo_url, reglement_url FROM etablissements WHERE id = %s",
            (admin.etablissement_id,),
        )
        id_, nom, pays, ville, logo_url, reglement_url = cur.fetchone()

    return EtablissementInfo(id=str(id_), nom=nom, pays=pays, ville=ville,
                               logo_url=logo_url, reglement_url=reglement_url)


@router.post("/reglement", response_model=EtablissementInfo)
async def uploader_reglement(
    fichier: UploadFile = File(...),
    admin: AdministratifConnecte = Depends(get_administratif_connecte),
):
    contenu = await fichier.read()

    # Vérification de l'en-tête PDF réel (%PDF-), pas juste l'extension du nom
    # de fichier — même logique de prudence que pour le logo.
    if not contenu.startswith(b"%PDF-"):
        raise HTTPException(status_code=422, detail="Fichier invalide — un PDF est attendu")

    dossier = _dossier_etablissement(admin.etablissement_id)
    chemin = dossier / "reglement.pdf"
    chemin.write_bytes(contenu)

    reglement_url = f"/uploads/{admin.etablissement_id}/reglement.pdf"
    with get_cursor(commit=True) as cur:
        cur.execute("UPDATE etablissements SET reglement_url = %s WHERE id = %s",
                    (reglement_url, admin.etablissement_id))
        cur.execute(
            "SELECT id, nom, pays, ville, logo_url, reglement_url FROM etablissements WHERE id = %s",
            (admin.etablissement_id,),
        )
        id_, nom, pays, ville, logo_url, reglement_url = cur.fetchone()

    return EtablissementInfo(id=str(id_), nom=nom, pays=pays, ville=ville,
                               logo_url=logo_url, reglement_url=reglement_url)


# ----------------------------------------------------------------------
# Programme pédagogique — référentiels (programme + manuel par niveau/matière)
# et calendrier (chapitre par mois)
# ----------------------------------------------------------------------

@router.get("/referentiels", response_model=list[ReferentielPedagogique])
def lister_referentiels(admin: AdministratifConnecte = Depends(get_administratif_connecte)):
    with get_cursor() as cur:
        cur.execute(
            """
            SELECT r.id, r.niveau_id, n.nom, r.matiere_id, m.nom,
                   r.programme_officiel, r.manuel_titre, r.manuel_editeur, r.manuel_edition
            FROM referentiels_pedagogiques r
            JOIN niveaux n ON n.id = r.niveau_id
            JOIN matieres m ON m.id = r.matiere_id
            WHERE r.etablissement_id = %s
            ORDER BY n.ordre, m.nom
            """,
            (admin.etablissement_id,),
        )
        lignes = cur.fetchall()
    return [ReferentielPedagogique(id=str(id_), niveau_id=str(nid), niveau=niveau, matiere_id=str(mid),
                                     matiere=matiere, programme_officiel=prog, manuel_titre=mt,
                                     manuel_editeur=me, manuel_edition=med)
            for id_, nid, niveau, mid, matiere, prog, mt, me, med in lignes]


@router.post("/referentiels", response_model=ReferentielPedagogique, status_code=status.HTTP_201_CREATED)
def creer_ou_modifier_referentiel(
    payload: CreationReferentiel,
    admin: AdministratifConnecte = Depends(get_administratif_connecte),
):
    with get_cursor(commit=True) as cur:
        cur.execute(
            """
            INSERT INTO referentiels_pedagogiques
                (etablissement_id, niveau_id, matiere_id, programme_officiel, manuel_titre, manuel_editeur, manuel_edition)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (etablissement_id, niveau_id, matiere_id)
            DO UPDATE SET programme_officiel = EXCLUDED.programme_officiel,
                          manuel_titre = EXCLUDED.manuel_titre,
                          manuel_editeur = EXCLUDED.manuel_editeur,
                          manuel_edition = EXCLUDED.manuel_edition
            RETURNING id, niveau_id, matiere_id, programme_officiel, manuel_titre, manuel_editeur, manuel_edition
            """,
            (admin.etablissement_id, payload.niveau_id, payload.matiere_id, payload.programme_officiel,
             payload.manuel_titre, payload.manuel_editeur, payload.manuel_edition),
        )
        id_, nid, mid, prog, mt, me, med = cur.fetchone()
        cur.execute("SELECT nom FROM niveaux WHERE id = %s", (nid,))
        niveau = cur.fetchone()[0]
        cur.execute("SELECT nom FROM matieres WHERE id = %s", (mid,))
        matiere = cur.fetchone()[0]

    return ReferentielPedagogique(id=str(id_), niveau_id=str(nid), niveau=niveau, matiere_id=str(mid),
                                    matiere=matiere, programme_officiel=prog, manuel_titre=mt,
                                    manuel_editeur=me, manuel_edition=med)


@router.get("/referentiels/{referentiel_id}/calendrier", response_model=list[ChapitreCalendrier])
def lister_calendrier(
    referentiel_id: str,
    admin: AdministratifConnecte = Depends(get_administratif_connecte),
):
    with get_cursor() as cur:
        cur.execute(
            "SELECT 1 FROM referentiels_pedagogiques WHERE id = %s AND etablissement_id = %s",
            (referentiel_id, admin.etablissement_id),
        )
        if cur.fetchone() is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Référentiel introuvable")

        cur.execute(
            "SELECT id, mois, chapitre_titre, competences, ordre FROM calendrier_pedagogique "
            "WHERE referentiel_id = %s ORDER BY mois, ordre",
            (referentiel_id,),
        )
        lignes = cur.fetchall()
    return [ChapitreCalendrier(id=str(id_), mois=str(mois), chapitre_titre=titre,
                                 competences=comp or [], ordre=ordre)
            for id_, mois, titre, comp, ordre in lignes]


@router.post("/calendrier", response_model=ChapitreCalendrier, status_code=status.HTTP_201_CREATED)
def ajouter_chapitre(
    payload: CreationChapitre,
    admin: AdministratifConnecte = Depends(get_administratif_connecte),
):
    with get_cursor(commit=True) as cur:
        cur.execute(
            "SELECT 1 FROM referentiels_pedagogiques WHERE id = %s AND etablissement_id = %s",
            (payload.referentiel_id, admin.etablissement_id),
        )
        if cur.fetchone() is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Référentiel introuvable")

        cur.execute(
            """
            INSERT INTO calendrier_pedagogique (referentiel_id, mois, chapitre_titre, competences, ordre)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id, mois, chapitre_titre, competences, ordre
            """,
            (payload.referentiel_id, payload.mois, payload.chapitre_titre, payload.competences, payload.ordre),
        )
        id_, mois, titre, comp, ordre = cur.fetchone()

    return ChapitreCalendrier(id=str(id_), mois=str(mois), chapitre_titre=titre, competences=comp or [], ordre=ordre)


@router.delete("/calendrier/{chapitre_id}", status_code=status.HTTP_204_NO_CONTENT)
def supprimer_chapitre(
    chapitre_id: str,
    admin: AdministratifConnecte = Depends(get_administratif_connecte),
):
    with get_cursor(commit=True) as cur:
        cur.execute(
            """
            DELETE FROM calendrier_pedagogique c
            USING referentiels_pedagogiques r
            WHERE c.id = %s AND c.referentiel_id = r.id AND r.etablissement_id = %s
            """,
            (chapitre_id, admin.etablissement_id),
        )
        if cur.rowcount == 0:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chapitre introuvable")
