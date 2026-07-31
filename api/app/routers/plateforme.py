import secrets

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from .. import rag
from ..db import get_cursor
from ..deps import get_admin_plateforme_connecte
from ..security import hacher_mot_de_passe
from ..schemas import (AdminPlateformeConnecte, DocumentPedagogique, PassageRecherche,
                        EtablissementResume, CreationEtablissement, EtablissementCree, CompteCree,
                        ExerciceBiblioCommune)

router = APIRouter(prefix="/plateforme", tags=["admin-plateforme"])


def _generer_mot_de_passe_provisoire() -> str:
    return secrets.token_urlsafe(8)


# ---------------------------------------------------------------------------
# Documents partagés (programmes officiels) — portée plateforme entière.
# Seul point de dépôt désormais : /administration/documents ne permet plus
# que la LECTURE (transparence pour les établissements), plus le dépôt ni
# la suppression, réservés à l'Admin Plateforme.
# ---------------------------------------------------------------------------

@router.post("/documents", response_model=DocumentPedagogique, status_code=status.HTTP_201_CREATED)
async def deposer_programme_officiel(
    titre: str,
    niveau_id: str | None = None,
    matiere_id: str | None = None,
    fichier: UploadFile = File(...),
    admin: AdminPlateformeConnecte = Depends(get_admin_plateforme_connecte),
):
    contenu = await fichier.read()
    if not contenu.startswith(b"%PDF-"):
        raise HTTPException(status_code=422, detail="Fichier invalide — un PDF est attendu")

    with get_cursor(commit=True) as cur:
        cur.execute(
            """
            INSERT INTO documents_pedagogiques
                (etablissement_id, depose_par_id, type_document, niveau_id, matiere_id, titre, statut)
            VALUES (NULL, %s, 'programme_officiel', %s, %s, %s, 'en_traitement')
            RETURNING id
            """,
            (admin.id, niveau_id, matiere_id, titre),
        )
        document_id = cur.fetchone()[0]

    rag.ingerer_document(document_id, contenu)

    with get_cursor() as cur:
        cur.execute(
            """
            SELECT d.id, d.type_document, n.nom, m.nom, d.titre, d.nombre_pages, d.statut, d.erreur_traitement,
                   (SELECT COUNT(*) FROM passages_documents p WHERE p.document_id = d.id)
            FROM documents_pedagogiques d
            LEFT JOIN niveaux n ON n.id = d.niveau_id
            LEFT JOIN matieres m ON m.id = d.matiere_id
            WHERE d.id = %s
            """,
            (document_id,),
        )
        row = cur.fetchone()

    id_, type_doc, niveau, matiere, titre_, nb_pages, statut, erreur, nb_passages = row
    return DocumentPedagogique(id=str(id_), type_document=type_doc, niveau=niveau, matiere=matiere,
                                 titre=titre_, nombre_pages=nb_pages, statut=statut,
                                 erreur_traitement=erreur, nombre_passages=nb_passages)


@router.get("/documents", response_model=list[DocumentPedagogique])
def lister_programmes_officiels(admin: AdminPlateformeConnecte = Depends(get_admin_plateforme_connecte)):
    with get_cursor() as cur:
        cur.execute(
            """
            SELECT d.id, d.type_document, n.nom, m.nom, d.titre, d.nombre_pages, d.statut, d.erreur_traitement,
                   (SELECT COUNT(*) FROM passages_documents p WHERE p.document_id = d.id)
            FROM documents_pedagogiques d
            LEFT JOIN niveaux n ON n.id = d.niveau_id
            LEFT JOIN matieres m ON m.id = d.matiere_id
            WHERE d.type_document = 'programme_officiel'
            ORDER BY d.created_at DESC
            """
        )
        lignes = cur.fetchall()
    return [DocumentPedagogique(id=str(id_), type_document=t, niveau=n, matiere=m, titre=titre,
                                  nombre_pages=np, statut=s, erreur_traitement=e, nombre_passages=npass)
            for id_, t, n, m, titre, np, s, e, npass in lignes]


@router.delete("/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def supprimer_programme_officiel(document_id: str, admin: AdminPlateformeConnecte = Depends(get_admin_plateforme_connecte)):
    with get_cursor(commit=True) as cur:
        cur.execute(
            "DELETE FROM documents_pedagogiques WHERE id = %s AND type_document = 'programme_officiel'",
            (document_id,),
        )
        if cur.rowcount == 0:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document introuvable")


@router.get("/documents/{document_id}/tester-recherche", response_model=list[PassageRecherche])
def tester_recherche(document_id: str, q: str, admin: AdminPlateformeConnecte = Depends(get_admin_plateforme_connecte)):
    with get_cursor() as cur:
        cur.execute(
            "SELECT 1 FROM documents_pedagogiques WHERE id = %s AND type_document = 'programme_officiel'",
            (document_id,),
        )
        if cur.fetchone() is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document introuvable")

        client = rag.obtenir_client_mistral()
        if client is None:
            raise HTTPException(status_code=503, detail="MISTRAL_API_KEY absente sur le serveur")
        embedding_requete = rag.generer_embeddings(client, [q])[0]

        cur.execute(
            """
            SELECT p.contenu, 1 - (p.embedding <=> %s::vector) AS similarite
            FROM passages_documents p
            WHERE p.document_id = %s
            ORDER BY p.embedding <=> %s::vector
            LIMIT 5
            """,
            (rag.vers_pgvector(embedding_requete), document_id, rag.vers_pgvector(embedding_requete)),
        )
        resultats = cur.fetchall()

    return [PassageRecherche(extrait=contenu[:300], similarite=round(float(sim), 3)) for contenu, sim in resultats]


# ---------------------------------------------------------------------------
# Établissements — supervision multi-écoles
# ---------------------------------------------------------------------------

@router.get("/etablissements", response_model=list[EtablissementResume])
def lister_etablissements(admin: AdminPlateformeConnecte = Depends(get_admin_plateforme_connecte)):
    with get_cursor() as cur:
        cur.execute(
            """
            SELECT e.id, e.nom, e.pays, e.ville, e.niveau_abonnement, e.actif, e.created_at,
                   COUNT(DISTINCT u.id) FILTER (WHERE u.deleted_at IS NULL) AS nb_utilisateurs,
                   COUNT(DISTINCT el.utilisateur_id) AS nb_eleves
            FROM etablissements e
            LEFT JOIN utilisateurs u ON u.etablissement_id = e.id
            LEFT JOIN eleves el ON el.utilisateur_id = u.id
            GROUP BY e.id
            ORDER BY e.created_at DESC
            """
        )
        lignes = cur.fetchall()
    return [EtablissementResume(id=str(id_), nom=nom, pays=pays, ville=ville, niveau_abonnement=abo,
                                  actif=actif, created_at=created, nombre_utilisateurs=nb_u, nombre_eleves=nb_e)
            for id_, nom, pays, ville, abo, actif, created, nb_u, nb_e in lignes]


@router.post("/etablissements", response_model=EtablissementCree, status_code=status.HTTP_201_CREATED)
def creer_etablissement(payload: CreationEtablissement, admin: AdminPlateformeConnecte = Depends(get_admin_plateforme_connecte)):
    """Crée un nouvel établissement ET son premier compte administratif dans
    la même opération — sans ce compte, personne ne pourrait se connecter
    pour gérer la nouvelle école. Si la création du compte échoue après que
    l'établissement a été créé, l'établissement reste en base (visible,
    corrigible), plutôt que de tout annuler sur un échec partiel."""
    with get_cursor(commit=True) as cur:
        cur.execute("SELECT 1 FROM utilisateurs WHERE email = %s", (payload.admin_email,))
        if cur.fetchone() is not None:
            raise HTTPException(status_code=409, detail="Cet email est déjà utilisé par un autre compte")

        cur.execute(
            """
            INSERT INTO etablissements (nom, pays, ville, email_contact, telephone_contact, niveau_abonnement)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id, nom, pays, ville, niveau_abonnement, actif, created_at
            """,
            (payload.nom, payload.pays, payload.ville, payload.email_contact,
             payload.telephone_contact, payload.niveau_abonnement),
        )
        etab_id, nom, pays, ville, abo, actif, created = cur.fetchone()

        mot_de_passe = _generer_mot_de_passe_provisoire()
        cur.execute(
            """
            INSERT INTO utilisateurs (etablissement_id, role, email, mot_de_passe_hash, nom, prenom)
            VALUES (%s, 'administratif', %s, %s, %s, %s)
            RETURNING id
            """,
            (etab_id, payload.admin_email, hacher_mot_de_passe(mot_de_passe), payload.admin_nom, payload.admin_prenom),
        )
        compte_id = cur.fetchone()[0]

    return EtablissementCree(
        etablissement=EtablissementResume(id=str(etab_id), nom=nom, pays=pays, ville=ville,
                                            niveau_abonnement=abo, actif=actif, created_at=created,
                                            nombre_utilisateurs=1, nombre_eleves=0),
        compte_admin=CompteCree(id=str(compte_id), email=payload.admin_email, mot_de_passe_provisoire=mot_de_passe),
    )


@router.patch("/etablissements/{etablissement_id}/desactiver", status_code=status.HTTP_204_NO_CONTENT)
def desactiver_etablissement(etablissement_id: str, admin: AdminPlateformeConnecte = Depends(get_admin_plateforme_connecte)):
    with get_cursor(commit=True) as cur:
        cur.execute("UPDATE etablissements SET actif = false WHERE id = %s RETURNING id", (etablissement_id,))
        if cur.fetchone() is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Établissement introuvable")


@router.patch("/etablissements/{etablissement_id}/reactiver", status_code=status.HTTP_204_NO_CONTENT)
def reactiver_etablissement(etablissement_id: str, admin: AdminPlateformeConnecte = Depends(get_admin_plateforme_connecte)):
    with get_cursor(commit=True) as cur:
        cur.execute("UPDATE etablissements SET actif = true WHERE id = %s RETURNING id", (etablissement_id,))
        if cur.fetchone() is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Établissement introuvable")


# ---------------------------------------------------------------------------
# Bibliothèque commune d'exercices (etablissement_id NULL) — modération
# ---------------------------------------------------------------------------

@router.get("/exercices", response_model=list[ExerciceBiblioCommune])
def lister_bibliotheque_commune(admin: AdminPlateformeConnecte = Depends(get_admin_plateforme_connecte)):
    with get_cursor() as cur:
        cur.execute(
            """
            SELECT e.id, n.nom, m.nom, e.theme, e.difficulte, e.statut, e.source, e.created_at
            FROM exercices e
            JOIN niveaux n ON n.id = e.niveau_id
            JOIN matieres m ON m.id = e.matiere_id
            WHERE e.etablissement_id IS NULL AND e.deleted_at IS NULL
            ORDER BY e.created_at DESC
            """
        )
        lignes = cur.fetchall()
    return [ExerciceBiblioCommune(id=str(id_), niveau=niveau, matiere=matiere, theme=theme,
                                    difficulte=diff, statut=statut, source=source, created_at=created)
            for id_, niveau, matiere, theme, diff, statut, source, created in lignes]


@router.delete("/exercices/{exercice_id}", status_code=status.HTTP_204_NO_CONTENT)
def retirer_de_la_bibliotheque_commune(exercice_id: str, admin: AdminPlateformeConnecte = Depends(get_admin_plateforme_connecte)):
    """Retrait doux (deleted_at), pas une suppression physique — cohérent
    avec le reste de la plateforme, et permet de revenir en arrière si besoin."""
    with get_cursor(commit=True) as cur:
        cur.execute(
            "UPDATE exercices SET deleted_at = now() WHERE id = %s AND etablissement_id IS NULL AND deleted_at IS NULL RETURNING id",
            (exercice_id,),
        )
        if cur.fetchone() is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exercice introuvable dans la bibliothèque commune")
