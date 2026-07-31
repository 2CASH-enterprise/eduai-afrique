-- Migration 002 : base de connaissance documentaire (programmes officiels,
-- notes de cours) — alimente la génération IA (RAG), jamais consultable ni
-- téléchargeable en retour par qui que ce soit. Voir la discussion produit :
-- seuls des contenus au statut juridique clair (documents publics, notes
-- rédigées par l'enseignant/l'établissement lui-même) doivent y être
-- déposés — jamais un manuel scolaire commercial scanné.

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS documents_pedagogiques (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    etablissement_id    UUID NOT NULL REFERENCES etablissements(id) ON DELETE CASCADE,
    depose_par_id       UUID REFERENCES utilisateurs(id),
    type_document        TEXT NOT NULL DEFAULT 'notes_cours'
                        CHECK (type_document IN ('programme_officiel', 'notes_cours')),
    niveau_id           UUID REFERENCES niveaux(id),
    matiere_id          UUID REFERENCES matieres(id),
    titre               TEXT NOT NULL,
    nombre_pages        INTEGER,
    statut              TEXT NOT NULL DEFAULT 'en_traitement'
                        CHECK (statut IN ('en_traitement', 'indexe', 'erreur')),
    erreur_traitement   TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_documents_etablissement ON documents_pedagogiques(etablissement_id);
CREATE INDEX IF NOT EXISTS idx_documents_niveau_matiere ON documents_pedagogiques(niveau_id, matiere_id);

-- Le texte brut du document N'EST PAS stocké tel quel dans une seule colonne
-- géante : il est découpé en passages, chacun avec son propre vecteur
-- d'embedding — c'est ce qui permet la recherche "par sens" au moment de
-- la génération, plutôt qu'une simple recherche de mots-clés.
CREATE TABLE IF NOT EXISTS passages_documents (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id         UUID NOT NULL REFERENCES documents_pedagogiques(id) ON DELETE CASCADE,
    ordre               INTEGER NOT NULL,
    contenu             TEXT NOT NULL,
    embedding           vector(1024)  -- dimension du modèle mistral-embed
);
CREATE INDEX IF NOT EXISTS idx_passages_document ON passages_documents(document_id);

-- Index de recherche par similarité vectorielle (IVFFlat — bon compromis
-- vitesse/précision pour un volume de quelques milliers à dizaines de
-- milliers de passages ; à revoir pour un volume bien plus grand).
CREATE INDEX IF NOT EXISTS idx_passages_embedding ON passages_documents
    USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
