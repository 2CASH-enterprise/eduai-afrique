-- Migration 007 : classes personnelles pour l'enseignant indépendant, qui
-- lui permettent enfin d'utiliser le vrai flux "Déposer un cours" (avec sa
-- file de validation), plutôt que seulement la Génération libre éphémère
-- (voir la discussion produit du 01/08 sur le système de crédits, qui a
-- révélé ce manque).
--
-- Distincte des vraies classes d'établissement (classes) : pas d'élèves
-- réels, pas de bulletins, pas d'année scolaire — juste un contexte que
-- l'enseignant déclare lui-même pour organiser sa génération de contenu.
-- Niveau en texte libre, comme la Génération libre : aucune table de
-- niveaux globale n'existe (niveaux est propre à chaque établissement).

CREATE TABLE IF NOT EXISTS classes_personnelles (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    enseignant_id       UUID NOT NULL REFERENCES utilisateurs(id) ON DELETE CASCADE,
    nom                 TEXT NOT NULL,
    matiere_id          UUID NOT NULL REFERENCES matieres(id),
    niveau              TEXT NOT NULL,
    effectif            INTEGER,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_classes_personnelles_enseignant ON classes_personnelles(enseignant_id);

ALTER TABLE cours ALTER COLUMN classe_id DROP NOT NULL;
ALTER TABLE cours ADD COLUMN IF NOT EXISTS classe_personnelle_id UUID REFERENCES classes_personnelles(id) ON DELETE CASCADE;

ALTER TABLE cours DROP CONSTRAINT IF EXISTS cours_une_seule_classe;
ALTER TABLE cours ADD CONSTRAINT cours_une_seule_classe
    CHECK ((classe_id IS NULL) != (classe_personnelle_id IS NULL));

GRANT SELECT, INSERT, UPDATE, DELETE ON classes_personnelles TO eduai_app;
