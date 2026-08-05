"""Logique partagée pour la base documentaire (RAG). Pas un router — importé
par documents.py (programmes officiels, côté Administration) et
documents_enseignant.py (notes de cours privées + partage, côté Enseignant),
ainsi que par les endpoints de validation (exercices, cours) pour la
réinjection du contenu généré-validé.
"""
import io
import os

from pypdf import PdfReader
from mistralai.client import Mistral

from .db import get_cursor

MODELE_EMBEDDING = "mistral-embed"
TAILLE_PASSAGE_MOTS = 220        # ~= 300 tokens, garde le contexte d'un paragraphe
CHEVAUCHEMENT_MOTS = 40           # évite de couper une idée à la frontière de deux passages


def extraire_texte_pdf(contenu: bytes) -> tuple[str, int]:
    """Retourne (texte_complet, nombre_pages). Une page illisible ne fait
    jamais échouer tout le document, juste un texte plus pauvre pour elle."""
    lecteur = PdfReader(io.BytesIO(contenu))
    pages_texte = []
    for page in lecteur.pages:
        try:
            pages_texte.append(page.extract_text() or "")
        except Exception:
            pages_texte.append("")
    return "\n\n".join(pages_texte), len(lecteur.pages)


def decouper_en_passages(texte: str) -> list[str]:
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


def obtenir_client_mistral() -> Mistral | None:
    cle = os.environ.get("MISTRAL_API_KEY")
    return Mistral(api_key=cle) if cle else None


def generer_embeddings(client: Mistral, textes: list[str]) -> list[list[float]]:
    """Par lots de 32 — évite des centaines d'allers-retours réseau pour un
    document de plusieurs dizaines de pages."""
    resultats = []
    taille_lot = 32
    for i in range(0, len(textes), taille_lot):
        lot = textes[i:i + taille_lot]
        reponse = client.embeddings.create(model=MODELE_EMBEDDING, inputs=lot)
        resultats.extend([d.embedding for d in reponse.data])
    return resultats


def vers_pgvector(vecteur: list[float]) -> str:
    return "[" + ",".join(str(x) for x in vecteur) + "]"


def ingerer_document(document_id: str, contenu_pdf: bytes) -> None:
    """Extraction + découpage + embeddings + stockage. Synchrone pour cette
    V1 — suffisant pour des documents de quelques dizaines de pages ; à
    passer en tâche de fond si des documents beaucoup plus gros deviennent
    courants. Ne lève jamais d'exception HTTP : en cas d'échec, le document
    reste visible avec statut='erreur' et le motif, plutôt qu'un 500 opaque.
    """
    try:
        texte, nb_pages = extraire_texte_pdf(contenu_pdf)
        passages = decouper_en_passages(texte)
        if not passages:
            raise ValueError("Aucun texte exploitable extrait du PDF (scan de mauvaise qualité ?)")

        client = obtenir_client_mistral()
        if client is None:
            raise ValueError("MISTRAL_API_KEY absente — impossible de générer les embeddings")

        embeddings = generer_embeddings(client, passages)

        with get_cursor(commit=True) as cur:
            for i, (texte_passage, vecteur) in enumerate(zip(passages, embeddings)):
                cur.execute(
                    "INSERT INTO passages_documents (document_id, ordre, contenu, embedding) VALUES (%s, %s, %s, %s)",
                    (document_id, i, texte_passage, vers_pgvector(vecteur)),
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


def reinjecter_contenu_valide(titre: str, texte: str, niveau_id: str | None, matiere_id: str | None,
                                pays: str) -> None:
    """Type 3 du corpus documentaire : une fois qu'un cours ou un exercice a
    été généré par l'IA ET validé par un enseignant, son contenu enrichit
    silencieusement le corpus — portée plateforme entière (etablissement_id
    NULL, comme programme_officiel), jamais consultable comme document
    (aucun endpoint de listing ne l'expose), aucun problème de droit
    d'auteur puisque c'est une création de la plateforme elle-même. Le pays
    est celui du contexte qui a produit ce contenu (établissement ou
    enseignant indépendant) — évite qu'un contenu généré au Cameroun
    enrichisse les générations au Sénégal (voir migration 009).

    Appelée depuis les endpoints de validation (exercices.py, cours.py).
    Best-effort : une panne d'embedding ne doit jamais faire échouer la
    validation elle-même (l'action principale que l'utilisateur voulait
    faire) — on avale l'exception après avoir marqué le document en erreur.
    """
    try:
        passages = decouper_en_passages(texte)
        if not passages:
            return

        with get_cursor(commit=True) as cur:
            cur.execute(
                """
                INSERT INTO documents_pedagogiques
                    (etablissement_id, depose_par_id, type_document, niveau_id, matiere_id, titre, pays, statut)
                VALUES (NULL, NULL, 'genere_valide', %s, %s, %s, %s, 'en_traitement')
                RETURNING id
                """,
                (niveau_id, matiere_id, titre, pays),
            )
            document_id = cur.fetchone()[0]

        _indexer_texte_direct(document_id, texte)
    except Exception:
        pass  # best-effort — ne doit jamais faire échouer la validation appelante


def _indexer_texte_direct(document_id: str, texte: str) -> None:
    """Comme ingerer_document, mais à partir de texte déjà disponible (pas
    d'un PDF à extraire) — utilisé par la réinjection de contenu généré."""
    try:
        passages = decouper_en_passages(texte)
        if not passages:
            raise ValueError("Texte vide, rien à indexer")
        client = obtenir_client_mistral()
        if client is None:
            raise ValueError("MISTRAL_API_KEY absente")
        embeddings = generer_embeddings(client, passages)
        with get_cursor(commit=True) as cur:
            for i, (texte_passage, vecteur) in enumerate(zip(passages, embeddings)):
                cur.execute(
                    "INSERT INTO passages_documents (document_id, ordre, contenu, embedding) VALUES (%s, %s, %s, %s)",
                    (document_id, i, texte_passage, vers_pgvector(vecteur)),
                )
            cur.execute("UPDATE documents_pedagogiques SET statut = 'indexe' WHERE id = %s", (document_id,))
    except Exception as e:
        with get_cursor(commit=True) as cur:
            cur.execute(
                "UPDATE documents_pedagogiques SET statut = 'erreur', erreur_traitement = %s WHERE id = %s",
                (str(e), document_id),
            )


SEUIL_SIMILARITE_MINIMUM = 0.3
# Réflexion du 04/08 : sans seuil, la recherche renvoyait toujours ses k
# meilleurs résultats même quand rien n'était vraiment pertinent — comme
# chercher "le moins pire" plutôt que "vraiment utile". En dessous de ce
# seuil, mieux vaut ne rien injecter dans le prompt (l'IA génère alors
# sans enrichissement, comme avant l'existence du corpus) que d'injecter
# du bruit. Valeur de départ raisonnable, à ajuster une fois de vraies
# données d'usage disponibles (voir TODO.md — mesure de la qualité du RAG,
# volontairement pas construite tout de suite).


def rechercher_passages_pertinents(cur, requete_embedding: list[float],
                                     niveau_id: str | None = None, matiere_id: str | None = None,
                                     etablissement_id: str | None = None,
                                     utilisateur_id_demandeur: str | None = None,
                                     pays: str | None = None,
                                     k: int = 5, seuil_similarite: float = SEUIL_SIMILARITE_MINIMUM) -> list[str]:
    """Fonction de récupération RAG — PAS un endpoint public. Combine trois
    sources selon les règles de partage retenues :
      - programme_officiel et genere_valide (etablissement_id NULL) :
        inclus si le pays correspond (voir migration 009 — évite qu'un
        programme camerounais influence une génération au Sénégal)
      - notes_cours de l'établissement du demandeur : seulement si le
        demandeur en est l'auteur, OU si le document a été explicitement
        partagé avec lui (table documents_partages)
    Ne renvoie jamais le document dans son ensemble ni son origine —
    uniquement le texte des passages, pour usage interne au prompt.
    """
    cur.execute(
        """
        SELECT p.contenu
        FROM passages_documents p
        JOIN documents_pedagogiques d ON d.id = p.document_id
        WHERE d.statut = 'indexe'
          AND (%s::uuid IS NULL OR d.niveau_id = %s::uuid)
          AND (%s::uuid IS NULL OR d.matiere_id = %s::uuid)
          AND (
                (d.etablissement_id IS NULL AND (%s::text IS NULL OR d.pays = %s::text))
                OR (
                    d.etablissement_id = %s::uuid
                    AND d.type_document = 'notes_cours'
                    AND (
                        d.depose_par_id = %s::uuid
                        OR EXISTS (
                            SELECT 1 FROM documents_partages dp
                            WHERE dp.document_id = d.id AND dp.partage_avec_id = %s::uuid
                        )
                    )
                )
              )
          AND 1 - (p.embedding <=> %s::vector) >= %s
        ORDER BY p.embedding <=> %s::vector
        LIMIT %s
        """,
        (niveau_id, niveau_id, matiere_id, matiere_id,
         pays, pays,
         etablissement_id, utilisateur_id_demandeur, utilisateur_id_demandeur,
         vers_pgvector(requete_embedding), seuil_similarite,
         vers_pgvector(requete_embedding), k),
    )
    return [row[0] for row in cur.fetchall()]
