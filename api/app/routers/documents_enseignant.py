from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel

from .. import rag
from ..db import get_cursor
from ..deps import get_enseignant_connecte
from ..schemas import EnseignantConnecte, DocumentPedagogique

router = APIRouter(prefix="/enseignant/documents", tags=["documents-enseignant"])


class CollegueResume(BaseModel):
    id: str
    nom: str
    prenom: str


class PartageAvec(BaseModel):
    utilisateur_id: str


@router.post("", response_model=DocumentPedagogique, status_code=status.HTTP_201_CREATED)
async def deposer_notes_cours(
    titre: str,
    niveau_id: str | None = None,
    matiere_id: str | None = None,
    fichier: UploadFile = File(...),
    enseignant: EnseignantConnecte = Depends(get_enseignant_connecte),
):
    """Toujours privé par défaut — visible seulement par l'enseignant qui
    dépose, jamais par ses collègues sans partage explicite (voir
    POST /{id}/partager), jamais par un autre établissement."""
    contenu = await fichier.read()
    if not contenu.startswith(b"%PDF-"):
        raise HTTPException(status_code=422, detail="Fichier invalide — un PDF est attendu")

    with get_cursor(commit=True) as cur:
        cur.execute(
            """
            INSERT INTO documents_pedagogiques
                (etablissement_id, depose_par_id, type_document, niveau_id, matiere_id, titre, statut)
            VALUES (%s, %s, 'notes_cours', %s, %s, %s, 'en_traitement')
            RETURNING id
            """,
            (enseignant.etablissement_id, enseignant.id, niveau_id, matiere_id, titre),
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


@router.get("", response_model=list[DocumentPedagogique])
def lister_mes_notes_cours(enseignant: EnseignantConnecte = Depends(get_enseignant_connecte)):
    """Mes propres notes déposées + celles qu'un collègue a partagées avec
    moi — jamais celles d'un collègue non partagées, jamais d'un autre
    établissement."""
    with get_cursor() as cur:
        cur.execute(
            """
            SELECT d.id, d.type_document, n.nom, m.nom, d.titre, d.nombre_pages, d.statut, d.erreur_traitement,
                   (SELECT COUNT(*) FROM passages_documents p WHERE p.document_id = d.id)
            FROM documents_pedagogiques d
            LEFT JOIN niveaux n ON n.id = d.niveau_id
            LEFT JOIN matieres m ON m.id = d.matiere_id
            WHERE d.type_document = 'notes_cours'
              AND (
                    d.depose_par_id = %s
                    OR EXISTS (SELECT 1 FROM documents_partages dp WHERE dp.document_id = d.id AND dp.partage_avec_id = %s)
                  )
            ORDER BY d.created_at DESC
            """,
            (enseignant.id, enseignant.id),
        )
        lignes = cur.fetchall()
    return [DocumentPedagogique(id=str(id_), type_document=t, niveau=n, matiere=m, titre=titre,
                                  nombre_pages=np, statut=s, erreur_traitement=e, nombre_passages=npass)
            for id_, t, n, m, titre, np, s, e, npass in lignes]


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def supprimer_mes_notes_cours(document_id: str, enseignant: EnseignantConnecte = Depends(get_enseignant_connecte)):
    with get_cursor(commit=True) as cur:
        cur.execute(
            "DELETE FROM documents_pedagogiques WHERE id = %s AND depose_par_id = %s",
            (document_id, enseignant.id),
        )
        if cur.rowcount == 0:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                 detail="Document introuvable, ou vous n'en êtes pas l'auteur")


@router.get("/collegues", response_model=list[CollegueResume])
def lister_collegues(enseignant: EnseignantConnecte = Depends(get_enseignant_connecte)):
    """Pour peupler le sélecteur de partage — collègues enseignants du même
    établissement uniquement, jamais d'un autre établissement."""
    with get_cursor() as cur:
        cur.execute(
            """
            SELECT u.id, u.nom, u.prenom
            FROM utilisateurs u
            WHERE u.role = 'enseignant' AND u.etablissement_id = %s AND u.id != %s
              AND u.actif = true AND u.deleted_at IS NULL
            ORDER BY u.nom
            """,
            (enseignant.etablissement_id, enseignant.id),
        )
        lignes = cur.fetchall()
    return [CollegueResume(id=str(id_), nom=nom, prenom=prenom) for id_, nom, prenom in lignes]


@router.post("/{document_id}/partager", status_code=status.HTTP_204_NO_CONTENT)
def partager_avec_collegue(
    document_id: str,
    payload: PartageAvec,
    enseignant: EnseignantConnecte = Depends(get_enseignant_connecte),
):
    with get_cursor(commit=True) as cur:
        cur.execute(
            "SELECT 1 FROM documents_pedagogiques WHERE id = %s AND depose_par_id = %s",
            (document_id, enseignant.id),
        )
        if cur.fetchone() is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                 detail="Document introuvable, ou vous n'en êtes pas l'auteur")

        cur.execute(
            "SELECT 1 FROM utilisateurs WHERE id = %s AND role = 'enseignant' AND etablissement_id = %s",
            (payload.utilisateur_id, enseignant.etablissement_id),
        )
        if cur.fetchone() is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                 detail="Collègue introuvable dans votre établissement")

        cur.execute(
            "INSERT INTO documents_partages (document_id, partage_avec_id) VALUES (%s, %s) "
            "ON CONFLICT (document_id, partage_avec_id) DO NOTHING",
            (document_id, payload.utilisateur_id),
        )


@router.delete("/{document_id}/partager/{utilisateur_id}", status_code=status.HTTP_204_NO_CONTENT)
def revoquer_partage(
    document_id: str,
    utilisateur_id: str,
    enseignant: EnseignantConnecte = Depends(get_enseignant_connecte),
):
    with get_cursor(commit=True) as cur:
        cur.execute(
            """
            DELETE FROM documents_partages dp
            USING documents_pedagogiques d
            WHERE dp.document_id = d.id AND d.id = %s AND d.depose_par_id = %s AND dp.partage_avec_id = %s
            """,
            (document_id, enseignant.id, utilisateur_id),
        )
        if cur.rowcount == 0:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Partage introuvable")
