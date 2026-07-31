from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from .. import rag
from ..db import get_cursor
from ..deps import get_administratif_connecte
from ..schemas import AdministratifConnecte, DocumentPedagogique, PassageRecherche

router = APIRouter(prefix="/administration/documents", tags=["documents-rag"])

# Politique retenue en attendant un vrai module Admin Plateforme : n'importe
# quel administrateur d'établissement peut déposer un programme officiel,
# qui devient alors immédiatement visible par TOUTE la plateforme
# (confiance mutuelle assumée pour cette phase — un vrai contrôle d'accès
# dédié viendra avec le rôle admin_plateforme).


@router.post("", response_model=DocumentPedagogique, status_code=status.HTTP_201_CREATED)
async def deposer_programme_officiel(
    titre: str,
    niveau_id: str | None = None,
    matiere_id: str | None = None,
    fichier: UploadFile = File(...),
    admin: AdministratifConnecte = Depends(get_administratif_connecte),
):
    """Seul type_document accepté ici : 'programme_officiel'. Les notes de
    cours privées relèvent du module Enseignant (/enseignant/documents),
    jamais de celui-ci — l'admin d'établissement ne doit pas pouvoir
    déposer au nom d'un enseignant ni décider de sa portée de partage."""
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


@router.get("", response_model=list[DocumentPedagogique])
def lister_programmes_officiels(admin: AdministratifConnecte = Depends(get_administratif_connecte)):
    """Liste les programmes officiels visibles par toute la plateforme —
    PAS les notes de cours (privées, jamais listées ici) ni le contenu
    généré-validé (jamais consultable comme document, par construction)."""
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


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def supprimer_programme_officiel(document_id: str, admin: AdministratifConnecte = Depends(get_administratif_connecte)):
    with get_cursor(commit=True) as cur:
        cur.execute(
            "DELETE FROM documents_pedagogiques WHERE id = %s AND type_document = 'programme_officiel'",
            (document_id,),
        )
        if cur.rowcount == 0:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document introuvable")


@router.get("/{document_id}/tester-recherche", response_model=list[PassageRecherche])
def tester_recherche(
    document_id: str,
    q: str,
    admin: AdministratifConnecte = Depends(get_administratif_connecte),
):
    """Diagnostic : vérifier la qualité de l'indexation avant de brancher la
    génération dessus — pas un usage final."""
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
