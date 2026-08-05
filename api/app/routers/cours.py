import json
import io
import re
import urllib.parse
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse

from .. import rag
from .. import generation_cours
from .. import credits
from .. import pdf_export
from ..db import get_cursor
from ..deps import get_enseignant_connecte
from ..schemas import (DepotCours, CoursResume, CoursDetail, ModificationRessource, EnseignantConnecte,
                        ModificationEcheanceCours, DuplicationCours)
from ..text_utils import aplatir_en_texte

router = APIRouter(prefix="/enseignant/cours", tags=["cours"])


def _entete_telechargement(nom_fichier: str) -> dict:
    """Un nom de fichier accentué ("Résumé.pdf") ne peut pas être mis tel
    quel dans un en-tête HTTP (UTF-8 brut invalide en Latin-1, confirmé par
    un test qui plantait dessus le 04/08) — encodage RFC 5987 pour les
    navigateurs modernes, repli ASCII pour les autres."""
    nom_ascii = re.sub(r"[^\x20-\x7E]", "_", nom_fichier)
    nom_encode = urllib.parse.quote(nom_fichier)
    return {"Content-Disposition": f"attachment; filename=\"{nom_ascii}\"; filename*=UTF-8''{nom_encode}"}

TYPES_RESSOURCE = ["fiche_pedagogique", "resume", "qcm", "exercices", "devoir", "controle"]

LABELS_RESSOURCE = {
    "fiche_pedagogique": "Fiche pédagogique",
    "resume": "Résumé",
    "exercices": "Exercices",
    "qcm": "QCM",
    "devoir": "Devoir",
    "controle": "Contrôle",
}



def _verifier_cours_du_enseignant(cur, cours_id: str, enseignant_id: str):
    cur.execute(
        """
        SELECT c.id, c.titre, c.contenu_texte, c.created_at, m.nom, COALESCE(cl.nom, cp.nom),
               c.date_echeance, c.difficulte, c.matiere_id, c.classe_id, c.classe_personnelle_id
        FROM cours c
        JOIN matieres m ON m.id = c.matiere_id
        LEFT JOIN classes cl ON cl.id = c.classe_id
        LEFT JOIN classes_personnelles cp ON cp.id = c.classe_personnelle_id
        WHERE c.id = %s AND c.enseignant_id = %s
        """,
        (cours_id, enseignant_id),
    )
    row = cur.fetchone()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                             detail="Cours introuvable dans votre banque personnelle")
    return row


@router.post("", response_model=CoursDetail, status_code=status.HTTP_201_CREATED)
def deposer_cours(
    payload: DepotCours,
    enseignant: EnseignantConnecte = Depends(get_enseignant_connecte),
):
    if bool(payload.classe_id) == bool(payload.classe_personnelle_id):
        raise HTTPException(status_code=422, detail="Précisez classe_id (établissement) OU classe_personnelle_id, pas les deux")

    with get_cursor(commit=True) as cur:
        if payload.classe_id:
            # Vraie classe d'établissement — vérifie l'affectation.
            cur.execute(
                "SELECT 1 FROM affectations_enseignants WHERE enseignant_id = %s AND classe_id = %s AND matiere_id = %s",
                (enseignant.id, payload.classe_id, payload.matiere_id),
            )
            if cur.fetchone() is None:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                     detail="Vous n'êtes pas affecté à cette classe pour cette matière")
        else:
            # Classe personnelle — vérifie qu'elle appartient bien à
            # l'enseignant ET que la matière du dépôt correspond à celle
            # déclarée pour cette classe. Même rigueur que pour une classe
            # d'établissement — faille de validation trouvée et corrigée
            # le 05/08 (rien n'empêchait jusque-là un appel API direct de
            # déposer un cours de SVT sur une classe personnelle nominalement
            # Mathématiques ; l'interface elle-même ne le permettait pas,
            # puisqu'elle combine classe et matière dans un seul sélecteur).
            cur.execute(
                "SELECT 1 FROM classes_personnelles WHERE id = %s AND enseignant_id = %s AND matiere_id = %s",
                (payload.classe_personnelle_id, enseignant.id, payload.matiere_id),
            )
            if cur.fetchone() is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                     detail="Classe personnelle introuvable, ou matière ne correspondant pas à celle déclarée pour cette classe")

        # Vérifie et débite les crédits AVANT toute génération IA — pas de
        # sens à appeler Mistral (coût réel) si l'enseignant ne peut de
        # toute façon pas se permettre ce dépôt. Ne fait rien pendant les 3
        # premiers mois du compte (voir credits.py).
        credits.verifier_et_debiter_depot_cours(cur, enseignant.id)

        cur.execute(
            """
            INSERT INTO cours (enseignant_id, classe_id, classe_personnelle_id, matiere_id, titre, contenu_texte,
                                fichier_url, date_seance, date_echeance, difficulte)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id, titre, contenu_texte, created_at, date_echeance, difficulte
            """,
            (enseignant.id, payload.classe_id, payload.classe_personnelle_id, payload.matiere_id,
             payload.titre, payload.contenu_texte, payload.fichier_url, payload.date_seance,
             payload.date_echeance, payload.difficulte),
        )
        cours_id, titre, contenu_texte, created_at, date_echeance, difficulte = cur.fetchone()

        cur.execute("SELECT nom FROM matieres WHERE id = %s", (payload.matiere_id,))
        matiere_nom = cur.fetchone()[0]

        if payload.classe_id:
            cur.execute(
                "SELECT c.nom, c.niveau_id, n.nom, c.etablissement_id, e.pays FROM classes c "
                "JOIN niveaux n ON n.id = c.niveau_id JOIN etablissements e ON e.id = c.etablissement_id "
                "WHERE c.id = %s",
                (payload.classe_id,),
            )
            classe_nom, niveau_id, niveau_nom, etablissement_id, pays = cur.fetchone()
            niveau_id, etablissement_id = str(niveau_id), str(etablissement_id)
        else:
            # Pas de niveau_id (texte libre, aucune table de niveaux
            # globale) ni d'établissement — le RAG se limite alors au
            # contenu partagé plateforme entière, filtré par matière et
            # par le pays propre de l'enseignant indépendant.
            cur.execute("SELECT nom, niveau FROM classes_personnelles WHERE id = %s", (payload.classe_personnelle_id,))
            classe_nom, niveau_nom = cur.fetchone()
            niveau_id, etablissement_id = None, None
            pays = enseignant.pays

        ressources = []
        for type_ressource in TYPES_RESSOURCE:
            contenu = generation_cours.generer_ressource(
                type_ressource, titre, contenu_texte, matiere_nom, niveau_nom,
                niveau_id, payload.matiere_id, etablissement_id, enseignant.id, pays, payload.difficulte,
            )
            cur.execute(
                """
                INSERT INTO ressources_generees (cours_id, type_ressource, contenu, statut)
                VALUES (%s, %s, %s, 'en_attente') RETURNING id, type_ressource, contenu, statut
                """,
                (cours_id, type_ressource, json.dumps(contenu)),
            )
            r_id, r_type, r_contenu, r_statut = cur.fetchone()
            ressources.append({"id": str(r_id), "type_ressource": r_type, "label": LABELS_RESSOURCE[r_type],
                                "contenu": r_contenu, "statut": r_statut})

    return CoursDetail(id=str(cours_id), titre=titre, matiere=matiere_nom, classe=classe_nom,
                        contenu_texte=contenu_texte, created_at=created_at,
                        date_echeance=str(date_echeance) if date_echeance else None,
                        difficulte=difficulte, ressources=ressources)


@router.get("", response_model=list[CoursResume])
def lister_mes_cours(enseignant: EnseignantConnecte = Depends(get_enseignant_connecte)):
    with get_cursor() as cur:
        cur.execute(
            """
            SELECT c.id, c.titre, m.nom, COALESCE(cl.nom, cp.nom), c.created_at, c.date_echeance, c.difficulte,
                   COUNT(*) FILTER (WHERE r.statut = 'valide') AS validees,
                   COUNT(*) AS total
            FROM cours c
            JOIN matieres m ON m.id = c.matiere_id
            LEFT JOIN classes cl ON cl.id = c.classe_id
            LEFT JOIN classes_personnelles cp ON cp.id = c.classe_personnelle_id
            LEFT JOIN ressources_generees r ON r.cours_id = c.id
            WHERE c.enseignant_id = %s
            GROUP BY c.id, c.titre, m.nom, cl.nom, cp.nom, c.created_at, c.date_echeance, c.difficulte
            ORDER BY c.date_echeance ASC NULLS LAST, c.created_at DESC
            """,
            (enseignant.id,),
        )
        lignes = cur.fetchall()

    return [CoursResume(id=str(id_), titre=titre, matiere=matiere, classe=classe, created_at=created_at,
                         date_echeance=str(date_echeance) if date_echeance else None, difficulte=difficulte,
                         nombre_ressources_validees=validees, nombre_ressources_total=total)
            for id_, titre, matiere, classe, created_at, date_echeance, difficulte, validees, total in lignes]


@router.get("/{cours_id}", response_model=CoursDetail)
def detail_cours(cours_id: str, enseignant: EnseignantConnecte = Depends(get_enseignant_connecte)):
    with get_cursor() as cur:
        (cours_id_v, titre, contenu_texte, created_at, matiere_nom, classe_nom,
         date_echeance, difficulte, _matiere_id, _classe_id, _classe_perso_id) = _verifier_cours_du_enseignant(
            cur, cours_id, enseignant.id)

        cur.execute(
            "SELECT id, type_ressource, contenu, statut FROM ressources_generees WHERE cours_id = %s "
            "AND statut != 'supprime'",
            (cours_id,),
        )
        ressources = sorted(
            ({"id": str(r_id), "type_ressource": r_type, "label": LABELS_RESSOURCE[r_type],
              "contenu": r_contenu, "statut": r_statut}
             for r_id, r_type, r_contenu, r_statut in cur.fetchall()),
            key=lambda r: TYPES_RESSOURCE.index(r["type_ressource"]) if r["type_ressource"] in TYPES_RESSOURCE else 99,
        )

    return CoursDetail(id=str(cours_id_v), titre=titre, matiere=matiere_nom, classe=classe_nom,
                        contenu_texte=contenu_texte, created_at=created_at,
                        date_echeance=str(date_echeance) if date_echeance else None,
                        difficulte=difficulte, ressources=ressources)


@router.patch("/{cours_id}/echeance", response_model=CoursDetail)
def modifier_echeance(cours_id: str, payload: ModificationEcheanceCours,
                       enseignant: EnseignantConnecte = Depends(get_enseignant_connecte)):
    """TODO.md point 19.3 — assigner une échéance à un cours déjà déposé,
    sans avoir à le régénérer. Passer date_echeance à null la retire."""
    with get_cursor(commit=True) as cur:
        _verifier_cours_du_enseignant(cur, cours_id, enseignant.id)
        cur.execute("UPDATE cours SET date_echeance = %s WHERE id = %s", (payload.date_echeance, cours_id))
    return detail_cours(cours_id, enseignant)


@router.post("/{cours_id}/dupliquer", response_model=CoursDetail, status_code=status.HTTP_201_CREATED)
def dupliquer_cours(cours_id: str, payload: DuplicationCours,
                     enseignant: EnseignantConnecte = Depends(get_enseignant_connecte)):
    """TODO.md point 19.4 — copie un cours déjà déposé (titre, contenu
    enseigné, les 6 ressources) vers une autre classe (ou la même), sans
    nouvel appel IA — donc sans coût en crédits, contrairement à un dépôt
    normal. Chaque ressource copiée repart de 'en_attente' : à valider à
    nouveau pour cette classe, l'occasion d'adapter si besoin."""
    if bool(payload.classe_id) == bool(payload.classe_personnelle_id):
        raise HTTPException(status_code=422, detail="Précisez classe_id (établissement) OU classe_personnelle_id, pas les deux")

    with get_cursor(commit=True) as cur:
        (_, titre, contenu_texte, _, matiere_nom, _,
         date_echeance, difficulte, matiere_id, _, _) = _verifier_cours_du_enseignant(cur, cours_id, enseignant.id)

        if payload.classe_id:
            cur.execute(
                "SELECT 1 FROM affectations_enseignants WHERE enseignant_id = %s AND classe_id = %s AND matiere_id = %s",
                (enseignant.id, payload.classe_id, matiere_id),
            )
            if cur.fetchone() is None:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                     detail="Vous n'êtes pas affecté à cette classe pour cette matière")
        else:
            cur.execute("SELECT 1 FROM classes_personnelles WHERE id = %s AND enseignant_id = %s AND matiere_id = %s",
                        (payload.classe_personnelle_id, enseignant.id, matiere_id))
            if cur.fetchone() is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                     detail="Classe personnelle introuvable, ou matière ne correspondant pas à celle déclarée pour cette classe")

        cur.execute(
            """
            INSERT INTO cours (enseignant_id, classe_id, classe_personnelle_id, matiere_id, titre, contenu_texte, difficulte)
            VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id, created_at
            """,
            (enseignant.id, payload.classe_id, payload.classe_personnelle_id, matiere_id, titre, contenu_texte, difficulte),
        )
        nouveau_cours_id, created_at = cur.fetchone()

        cur.execute("SELECT type_ressource, contenu FROM ressources_generees WHERE cours_id = %s AND statut != 'supprime'",
                    (cours_id,))
        ressources_source = cur.fetchall()

        ressources = []
        for type_ressource, contenu in ressources_source:
            cur.execute(
                """
                INSERT INTO ressources_generees (cours_id, type_ressource, contenu, statut)
                VALUES (%s, %s, %s, 'en_attente') RETURNING id, type_ressource, contenu, statut
                """,
                (nouveau_cours_id, type_ressource, json.dumps(contenu)),
            )
            r_id, r_type, r_contenu, r_statut = cur.fetchone()
            ressources.append({"id": str(r_id), "type_ressource": r_type, "label": LABELS_RESSOURCE[r_type],
                                "contenu": r_contenu, "statut": r_statut})

        cur.execute("SELECT COALESCE(cl.nom, cp.nom) FROM cours c "
                    "LEFT JOIN classes cl ON cl.id = c.classe_id "
                    "LEFT JOIN classes_personnelles cp ON cp.id = c.classe_personnelle_id "
                    "WHERE c.id = %s", (nouveau_cours_id,))
        classe_nom = cur.fetchone()[0]

    return CoursDetail(id=str(nouveau_cours_id), titre=titre, matiere=matiere_nom, classe=classe_nom,
                        contenu_texte=contenu_texte, created_at=created_at, date_echeance=None,
                        difficulte=difficulte, ressources=ressources)


@router.patch("/{cours_id}/ressources/{ressource_id}")
def modifier_ressource(
    cours_id: str,
    ressource_id: str,
    payload: ModificationRessource,
    enseignant: EnseignantConnecte = Depends(get_enseignant_connecte),
):
    with get_cursor(commit=True) as cur:
        _verifier_cours_du_enseignant(cur, cours_id, enseignant.id)

        cur.execute(
            "SELECT statut FROM ressources_generees WHERE id = %s AND cours_id = %s",
            (ressource_id, cours_id),
        )
        row = cur.fetchone()
        if row is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ressource introuvable")
        statut_avant = row[0]

        champs = {}
        if payload.contenu is not None:
            champs["contenu"] = json.dumps(payload.contenu)
        if payload.statut is not None:
            if payload.statut not in ("en_attente", "valide", "corrige", "supprime"):
                raise HTTPException(status_code=422, detail="Statut invalide")
            champs["statut"] = payload.statut

        if not champs:
            raise HTTPException(status_code=422, detail="Aucune modification fournie")

        assignations = ", ".join(f"{k} = %s" for k in champs)
        cur.execute(f"UPDATE ressources_generees SET {assignations} WHERE id = %s",
                    (*champs.values(), ressource_id))

        # Système de crédits : gagné dès la validation, quel que soit le
        # mois (voir credits.py) — +2 si la ressource avait été corrigée
        # au préalable (preuve d'une vraie relecture), +1 sinon.
        if payload.statut == "valide" and statut_avant != "valide":
            credits.recompenser_validation(cur, enseignant.id, ressource_id, statut_avant)

        # Type 3 du corpus documentaire : une ressource de cours validée par
        # l'enseignant est une création propre de la plateforme, réinjectée
        # pour enrichir les futures générations — jamais consultable comme
        # document par ailleurs (voir rag.reinjecter_contenu_valide).
        texte, niveau_id, matiere_id, titre_reinjection, pays = None, None, None, None, None
        if payload.statut == "valide":
            cur.execute(
                """
                SELECT c.matiere_id, cl.niveau_id, c.titre, r.type_ressource, r.contenu, e.pays
                FROM ressources_generees r
                JOIN cours c ON c.id = r.cours_id
                LEFT JOIN classes cl ON cl.id = c.classe_id
                LEFT JOIN etablissements e ON e.id = cl.etablissement_id
                WHERE r.id = %s
                """,
                (ressource_id,),
            )
            matiere_id, niveau_id, titre_cours, type_ressource, contenu_json, pays = cur.fetchone()
            pays = pays or enseignant.pays  # classe personnelle : pas d'établissement, on retombe sur l'enseignant
            if contenu_json:
                donnees = contenu_json if isinstance(contenu_json, dict) else json.loads(contenu_json)
                # La plupart des ressources sont désormais structurées (pas
                # de clé "texte" unique, voir generation_cours.SCHEMAS_PAR_TYPE)
                # — on aplatit systématiquement plutôt que de ne réinjecter
                # que le cas de repli en texte simple (bug corrigé le 04/08 :
                # la réinjection ne se déclenchait quasiment plus jamais
                # depuis l'introduction des schémas dédiés par type).
                texte = aplatir_en_texte(donnees)
            titre_reinjection = f"{titre_cours} — {LABELS_RESSOURCE.get(type_ressource, type_ressource)}"

    if texte:
        rag.reinjecter_contenu_valide(titre=titre_reinjection, texte=texte,
                                        niveau_id=niveau_id, matiere_id=matiere_id, pays=pays)

    return {"statut": "ok"}


@router.get("/{cours_id}/ressources/{ressource_id}/export-pdf")
def exporter_ressource_pdf(cours_id: str, ressource_id: str,
                             enseignant: EnseignantConnecte = Depends(get_enseignant_connecte)):
    """TODO.md point 19.1 — imprimer UNE ressource précise (ex : le contrôle)."""
    with get_cursor() as cur:
        (_, titre_cours, _, _, matiere_nom, classe_nom, *_rest) = _verifier_cours_du_enseignant(cur, cours_id, enseignant.id)
        cur.execute("SELECT type_ressource, contenu FROM ressources_generees WHERE id = %s AND cours_id = %s AND statut != 'supprime'",
                    (ressource_id, cours_id))
        row = cur.fetchone()
        if row is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ressource introuvable")
        type_ressource, contenu = row

    pdf = pdf_export.construire_pdf_ressource(titre_cours, matiere_nom, classe_nom,
                                                LABELS_RESSOURCE[type_ressource], type_ressource, contenu)
    nom_fichier = f"{titre_cours} - {LABELS_RESSOURCE[type_ressource]}.pdf".replace("/", "-")
    return StreamingResponse(io.BytesIO(pdf), media_type="application/pdf", headers=_entete_telechargement(nom_fichier))


@router.get("/{cours_id}/export-pdf")
def exporter_cours_pdf(cours_id: str, enseignant: EnseignantConnecte = Depends(get_enseignant_connecte)):
    """TODO.md point 19.1 — toutes les ressources d'un cours dans un seul PDF."""
    with get_cursor() as cur:
        (_, titre_cours, _, _, matiere_nom, classe_nom, *_rest) = _verifier_cours_du_enseignant(cur, cours_id, enseignant.id)
        cur.execute("SELECT type_ressource, contenu FROM ressources_generees WHERE cours_id = %s AND statut != 'supprime'",
                    (cours_id,))
        ressources = sorted(
            ({"type_ressource": t, "label": LABELS_RESSOURCE[t], "contenu": c} for t, c in cur.fetchall()),
            key=lambda r: TYPES_RESSOURCE.index(r["type_ressource"]) if r["type_ressource"] in TYPES_RESSOURCE else 99,
        )
        if not ressources:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Aucune ressource à exporter")

    pdf = pdf_export.construire_pdf_cours_complet(titre_cours, matiere_nom, classe_nom, ressources)
    nom_fichier = f"{titre_cours}.pdf".replace("/", "-")
    return StreamingResponse(io.BytesIO(pdf), media_type="application/pdf", headers=_entete_telechargement(nom_fichier))
