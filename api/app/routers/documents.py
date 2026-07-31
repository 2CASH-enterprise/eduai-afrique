import io
import json
import os

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pypdf import PdfReader
from mistralai.client import Mistral

from ..db import get_cursor
from ..deps import get_administratif_connecte
from ..schemas import AdministratifConnecte, DocumentPedagogique, PassageRecherche

router = APIRouter(prefix="/administration/documents", tags=["documents-rag"])

MODELE_EMBEDDING = "mistral-embed"
TAILLE_PASSAGE_MOTS = 220        # ~= 300 tokens, une granularité qui garde le contexte d'un paragraphe
CHEVAUCHEMENT_MOTS = 40           # évite de couper une idée pile à la frontière de deux passages


def _extraire_texte_pdf(contenu: bytes) -> tuple[str, int]:
    """Extrait le texte brut d'un PDF. Retourne (texte_complet, nombre_pages).
    Ne lève jamais d'exception pour une page illisible individuelle — un
    scan de mauvaise qualité sur une page ne doit pas faire échouer tout
    le document, juste produire un texte plus pauvre pour cette page.
    """
    lecteur = PdfReader(io.BytesIO(contenu))
    pages_texte = []
    for page in lecteur.pages:
        try:
            pages_texte.append(page.extract_text() or "")
        except Exception:
            pages_texte.append("")
    return "\n\n".join(pages_texte), len(lecteur.pages)


def _decouper_en_passages(texte: str) -> list[str]:
    """Découpe le texte en passages chevauchants, par mots plutôt que par
    caractères — plus robuste aux variations de longueur de mots entre le
    français et d'éventuels termes techniques/anglais dans le document.
    """
    mots = texte.split()
    if not mots:
        return []
    passages = []
    debut = 0
    while debut < len(mots):
        fin = min(debut + TAILLE_PASSAGE_MOTS, len(mots))
        passage = " ".join(mots[debut:fin])
        if passage.strip():
            passages.append(passage)
        if fin == len(mots):
            break
        debut = fin - CHEVAUCHEMENT_MOTS
    return passages


def _obtenir_client_mistral() -> Mistral | None:
    cle = os.environ.get("MISTRAL_API_KEY")
    return Mistral(api_key=cle) if cle else None


def _generer_embeddings(client: Mistral, textes: list[str]) -> list[list[float]]:
    """Appelle l'API Mistral par lots de 32 passages (limite raisonnable par
    requête) plutôt qu'un par un — évite des centaines d'allers-retours
    réseau pour un document de plusieurs dizaines de pages."""
    resultats = []
    taille_lot = 32
    for i in range(0, len(textes), taille_lot):
        lot = textes[i:i + taille_lot]
        reponse = client.embeddings.create(model=MODELE_EMBEDDING, inputs=lot)
        resultats.extend([d.embedding for d in reponse.data])
    return resultats


def _vers_pgvector(vecteur: list[float]) -> str:
    """pgvector attend un littéral texte '[0.1,0.2,...]', pas une liste Python."""
    return "[" + ",".join(str(x) for x in vecteur) + "]"


def _ingerer_document(document_id: str, contenu_pdf: bytes) -> None:
    """Extraction + découpage + embeddings + stockage, isolé de la couche
    HTTP pour être testable directement (voir tests : on monkeypatch
    _obtenir_client_mistral plutôt que d'injecter un paramètre dans
    l'endpoint FastAPI, qui ne l'accepterait pas proprement).

    Le traitement est fait ici de façon synchrone pour cette V1 — simple et
    suffisant pour des documents de quelques dizaines de pages. À faire
    passer en tâche de fond (Celery/RQ) si des documents beaucoup plus
    volumineux deviennent courants.
    """
    try:
        texte, nb_pages = _extraire_texte_pdf(contenu_pdf)
        passages = _decouper_en_passages(texte)
        if not passages:
            raise ValueError("Aucun texte exploitable extrait du PDF (scan de mauvaise qualité ?)")

        client = _obtenir_client_mistral()
        if client is None:
            raise ValueError("MISTRAL_API_KEY absente — impossible de générer les embeddings")

        embeddings = _generer_embeddings(client, passages)

        with get_cursor(commit=True) as cur:
            for i, (texte_passage, vecteur) in enumerate(zip(passages, embeddings)):
                cur.execute(
                    "INSERT INTO passages_documents (document_id, ordre, contenu, embedding) VALUES (%s, %s, %s, %s)",
                    (document_id, i, texte_passage, _vers_pgvector(vecteur)),
                )
            cur.execute(
                "UPDATE documents_pedagogiques SET statut = 'indexe', nombre_pages = %s WHERE id = %s",
                (nb_pages, document_id),
            )
    except Exception as e:
        with get_cursor(commit=True) as cur:
            cur.execute(
                "UPDATE documents_pedagogiques SET statut = 'erreur', erreur_traitement = %s WHERE id = %s",
                (str(e), document_id),
            )
        # Pas de relance HTTP : le document existe (statut 'erreur' visible
        # dans la liste), l'admin voit pourquoi et peut réessayer, plutôt
        # qu'un 500 opaque qui masquerait la vraie cause.


@router.post("", response_model=DocumentPedagogique, status_code=status.HTTP_201_CREATED)
async def deposer_document(
    titre: str,
    type_document: str,
    niveau_id: str | None = None,
    matiere_id: str | None = None,
    fichier: UploadFile = File(...),
    admin: AdministratifConnecte = Depends(get_administratif_connecte),
):
    if type_document not in ("programme_officiel", "notes_cours"):
        raise HTTPException(status_code=422, detail="type_document doit être 'programme_officiel' ou 'notes_cours'")

    contenu = await fichier.read()
    if not contenu.startswith(b"%PDF-"):
        raise HTTPException(status_code=422, detail="Fichier invalide — un PDF est attendu")

    with get_cursor(commit=True) as cur:
        cur.execute(
            """
            INSERT INTO documents_pedagogiques
                (etablissement_id, depose_par_id, type_document, niveau_id, matiere_id, titre, statut)
            VALUES (%s, %s, %s, %s, %s, %s, 'en_traitement')
            RETURNING id
            """,
            (admin.etablissement_id, admin.id, type_document, niveau_id, matiere_id, titre),
        )
        document_id = cur.fetchone()[0]

    _ingerer_document(document_id, contenu)

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
def lister_documents(admin: AdministratifConnecte = Depends(get_administratif_connecte)):
    with get_cursor() as cur:
        cur.execute(
            """
            SELECT d.id, d.type_document, n.nom, m.nom, d.titre, d.nombre_pages, d.statut, d.erreur_traitement,
                   (SELECT COUNT(*) FROM passages_documents p WHERE p.document_id = d.id)
            FROM documents_pedagogiques d
            LEFT JOIN niveaux n ON n.id = d.niveau_id
            LEFT JOIN matieres m ON m.id = d.matiere_id
            WHERE d.etablissement_id = %s
            ORDER BY d.created_at DESC
            """,
            (admin.etablissement_id,),
        )
        lignes = cur.fetchall()
    return [DocumentPedagogique(id=str(id_), type_document=t, niveau=n, matiere=m, titre=titre,
                                  nombre_pages=np, statut=s, erreur_traitement=e, nombre_passages=npass)
            for id_, t, n, m, titre, np, s, e, npass in lignes]


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def supprimer_document(document_id: str, admin: AdministratifConnecte = Depends(get_administratif_connecte)):
    with get_cursor(commit=True) as cur:
        cur.execute(
            "DELETE FROM documents_pedagogiques WHERE id = %s AND etablissement_id = %s",
            (document_id, admin.etablissement_id),
        )
        if cur.rowcount == 0:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document introuvable")


def rechercher_passages_pertinents(cur, etablissement_id: str, requete_embedding: list[float],
                                     niveau_id: str | None = None, matiere_id: str | None = None,
                                     k: int = 5) -> list[str]:
    """Fonction de récupération RAG — PAS un endpoint public. Utilisée en
    interne par les futures fonctions de génération (cours, exercices) pour
    retrouver les passages les plus pertinents avant d'appeler le LLM.
    Ne renvoie jamais le document dans son ensemble, ni son titre/origine —
    uniquement le texte des passages, pour usage interne au prompt.
    """
    cur.execute(
        """
        SELECT p.contenu
        FROM passages_documents p
        JOIN documents_pedagogiques d ON d.id = p.document_id
        WHERE d.etablissement_id = %s AND d.statut = 'indexe'
          AND (%s::uuid IS NULL OR d.niveau_id = %s::uuid)
          AND (%s::uuid IS NULL OR d.matiere_id = %s::uuid)
        ORDER BY p.embedding <=> %s::vector
        LIMIT %s
        """,
        (etablissement_id, niveau_id, niveau_id, matiere_id, matiere_id,
         _vers_pgvector(requete_embedding), k),
    )
    return [row[0] for row in cur.fetchall()]


@router.get("/{document_id}/tester-recherche", response_model=list[PassageRecherche])
def tester_recherche(
    document_id: str,
    q: str,
    admin: AdministratifConnecte = Depends(get_administratif_connecte),
):
    """Endpoint de diagnostic pour l'admin : vérifier que l'indexation
    fonctionne en cherchant un passage par similarité de sens. Utile pour
    contrôler la qualité de l'indexation avant de brancher la génération
    dessus — pas destiné à un usage final en dehors du débogage.
    """
    with get_cursor() as cur:
        cur.execute(
            "SELECT etablissement_id, niveau_id, matiere_id FROM documents_pedagogiques "
            "WHERE id = %s AND etablissement_id = %s",
            (document_id, admin.etablissement_id),
        )
        row = cur.fetchone()
        if row is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document introuvable")

        client = _obtenir_client_mistral()
        if client is None:
            raise HTTPException(status_code=503, detail="MISTRAL_API_KEY absente sur le serveur")
        embedding_requete = _generer_embeddings(client, [q])[0]

        cur.execute(
            """
            SELECT p.contenu, 1 - (p.embedding <=> %s::vector) AS similarite
            FROM passages_documents p
            WHERE p.document_id = %s
            ORDER BY p.embedding <=> %s::vector
            LIMIT 5
            """,
            (_vers_pgvector(embedding_requete), document_id, _vers_pgvector(embedding_requete)),
        )
        resultats = cur.fetchall()

    return [PassageRecherche(extrait=contenu[:300], similarite=round(float(sim), 3)) for contenu, sim in resultats]
