-- Migration 003 : corrige la portée de partage du corpus documentaire,
-- suite à la discussion produit sur la propriété du contenu.
--
-- Décisions retenues :
--   - programme_officiel : partagé à toute la plateforme (etablissement_id
--     NULL, même principe que la bibliothèque commune d'exercices)
--   - notes_cours : privé à l'enseignant qui les a déposées par défaut ;
--     partage explicite possible avec des collègues du même établissement
--     (jamais entre établissements) via documents_partages
--   - genere_valide (nouveau) : contenu généré + validé par la plateforme
--     (cours, exercices) réinjecté automatiquement dans le corpus, portée
--     plateforme entière, jamais consultable comme document — sert
--     uniquement de matière première invisible pour la recherche

ALTER TABLE documents_pedagogiques ALTER COLUMN etablissement_id DROP NOT NULL;

ALTER TABLE documents_pedagogiques DROP CONSTRAINT IF EXISTS documents_pedagogiques_type_document_check;
ALTER TABLE documents_pedagogiques ADD CONSTRAINT documents_pedagogiques_type_document_check
    CHECK (type_document IN ('programme_officiel', 'notes_cours', 'genere_valide'));

-- Garde-fou en base, pas seulement dans le code applicatif : un document de
-- type 'notes_cours' doit toujours avoir un établissement ET un déposant
-- (nécessaire pour déterminer qui peut le partager, et avec qui) ; les deux
-- autres types n'appartiennent à personne en particulier.
ALTER TABLE documents_pedagogiques DROP CONSTRAINT IF EXISTS documents_pedagogiques_notes_cours_proprietaire;
ALTER TABLE documents_pedagogiques ADD CONSTRAINT documents_pedagogiques_notes_cours_proprietaire
    CHECK (
        type_document != 'notes_cours'
        OR (etablissement_id IS NOT NULL AND depose_par_id IS NOT NULL)
    );

CREATE TABLE IF NOT EXISTS documents_partages (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id         UUID NOT NULL REFERENCES documents_pedagogiques(id) ON DELETE CASCADE,
    partage_avec_id     UUID NOT NULL REFERENCES utilisateurs(id) ON DELETE CASCADE,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (document_id, partage_avec_id)
);
CREATE INDEX IF NOT EXISTS idx_documents_partages_document ON documents_partages(document_id);
CREATE INDEX IF NOT EXISTS idx_documents_partages_utilisateur ON documents_partages(partage_avec_id);
