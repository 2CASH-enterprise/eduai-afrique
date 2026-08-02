-- Migration 009 : segmentation par pays du corpus documentaire RAG,
-- discutée et cadrée le 01/08. Corrige un vrai risque identifié : sans
-- champ pays, un programme officiel camerounais pouvait influencer une
-- génération demandée au Sénégal (et inversement), puisque la recherche
-- ne filtrait jusqu'ici que par niveau et matière.
--
-- Note : `exercices.pays` existait déjà (construit dans une session
-- antérieure) — c'est `documents_pedagogiques` qui avait été oublié.

ALTER TABLE documents_pedagogiques ADD COLUMN IF NOT EXISTS pays TEXT;

-- Rétro-remplissage des documents existants : on déduit le pays depuis
-- l'établissement quand c'est possible (notes_cours), sinon 'Cameroun'
-- par défaut (seul pays travaillé jusqu'ici sur la plateforme).
UPDATE documents_pedagogiques d
SET pays = e.pays
FROM etablissements e
WHERE d.etablissement_id = e.id AND d.pays IS NULL;

UPDATE documents_pedagogiques SET pays = 'Cameroun' WHERE pays IS NULL;

ALTER TABLE documents_pedagogiques ALTER COLUMN pays SET NOT NULL;
CREATE INDEX IF NOT EXISTS idx_documents_pays ON documents_pedagogiques(pays);

-- Pays de l'enseignant indépendant (etablissement_id NULL) — pour tout
-- enseignant rattaché à un établissement, c'est celui de l'établissement
-- qui prévaut ; ce champ ne sert que pour les indépendants, qui n'ont
-- justement aucun établissement pour le déduire.
ALTER TABLE utilisateurs ADD COLUMN IF NOT EXISTS pays TEXT;
