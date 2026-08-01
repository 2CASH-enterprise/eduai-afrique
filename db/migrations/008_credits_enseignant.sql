-- Migration 008 : système de crédits enseignant, discuté et cadré le 01/08.
--
-- Modèle retenu :
--   - Gagner : valider une ressource sans la modifier (+1), ou après
--     correction (+2) — dès le premier jour, pour habituer l'enseignant.
--   - Dépenser : uniquement "Déposer un cours" (−2), et uniquement à
--     partir du 4e mois suivant la création du compte. Avant ça, gratuit
--     et illimité, mais les crédits s'accumulent déjà en arrière-plan.
--   - Génération libre : toujours gratuite, à vie, sans condition.
--   - Pas de suivi côté établissement — jauge strictement personnelle.
--
-- Registre (ledger) plutôt qu'un simple solde : traçabilité complète,
-- l'enseignant peut voir pourquoi son solde a bougé.

CREATE TABLE IF NOT EXISTS credits_enseignant (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    enseignant_id       UUID NOT NULL REFERENCES utilisateurs(id) ON DELETE CASCADE,
    delta               INTEGER NOT NULL,
    motif               TEXT NOT NULL
                        CHECK (motif IN ('validation_simple', 'validation_corrigee', 'depot_cours')),
    reference_id        UUID,  -- id de la ressource validée, ou du cours déposé
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_credits_enseignant ON credits_enseignant(enseignant_id);

GRANT SELECT, INSERT, UPDATE, DELETE ON credits_enseignant TO eduai_app;
