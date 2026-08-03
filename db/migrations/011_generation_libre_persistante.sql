-- Migration 011 : redéfinit "Génération libre", discuté et cadré le 03/08.
--
-- Avant : génération éphémère d'UN exercice, jamais sauvegardé, jamais
-- validable, sans effet sur le corpus documentaire.
-- Après : l'enseignant choisit niveau (texte libre) + matière + thème +
-- quantité (1 à 5), génère une série d'exercices corrigés, les valide
-- (comme les ressources de "Déposer un cours"), et chaque validation
-- réinjecte silencieusement le corpus — exactement la même logique que
-- pour les cours, mais appliquée à des exercices autonomes plutôt qu'à un
-- cours complet en 6 ressources.
--
-- Table séparée de `exercices` (qui sert la bibliothèque commune et le
-- pipeline hors-ligne, avec niveau_id en FK obligatoire) plutôt que
-- réutilisée : même logique que classes_personnelles vs classes — niveau
-- reste en texte libre ici, aucune table de niveaux globale n'existe.
--
-- Reste gratuite, sans condition, à la différence de "Déposer un cours"
-- (décision du 03/08) — le système de crédits ne s'applique jamais ici.

CREATE TABLE IF NOT EXISTS exercices_generation_libre (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    enseignant_id       UUID NOT NULL REFERENCES utilisateurs(id) ON DELETE CASCADE,
    matiere_id          UUID NOT NULL REFERENCES matieres(id),
    niveau              TEXT NOT NULL,
    theme               TEXT NOT NULL,
    pays                TEXT NOT NULL,
    sous_theme          TEXT,
    enonce              TEXT NOT NULL,
    corrige             TEXT NOT NULL,
    etapes              TEXT[],
    contexte            TEXT,
    tags                TEXT[] DEFAULT '{}',
    statut              TEXT NOT NULL DEFAULT 'en_attente'
                        CHECK (statut IN ('en_attente', 'valide', 'rejete')),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_exgl_enseignant ON exercices_generation_libre(enseignant_id);
CREATE INDEX IF NOT EXISTS idx_exgl_statut ON exercices_generation_libre(statut);

GRANT SELECT, INSERT, UPDATE, DELETE ON exercices_generation_libre TO eduai_app;
