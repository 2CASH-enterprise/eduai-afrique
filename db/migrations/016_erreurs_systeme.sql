-- Migration 016 : monitoring des bugs (discuté et cadré le 06/08, suite à
-- l'incident React #31 découvert le jour même). Trois sources unifiées
-- dans un même écran Admin Plateforme :
--   1. generation_ia — échecs d'appel à Mistral (y compris crédits
--      épuisés), aujourd'hui avalés silencieusement dans le contenu généré
--      ("[Erreur de génération : ...]") sans que personne côté équipe ne
--      le sache.
--   2. plantage_navigateur — erreurs React côté client, remontées par un
--      Error Boundary global (voir web/components/ErrorBoundary.jsx),
--      impossibles à connaître autrement sans qu'un utilisateur envoie
--      une capture d'écran.
--   3. Les documents mal indexés existent déjà (documents_pedagogiques.
--      erreur_traitement) — pas dans cette table, juste rassemblés dans
--      le même écran de monitoring côté frontend.

CREATE TABLE IF NOT EXISTS erreurs_systeme (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    type_erreur  TEXT NOT NULL CHECK (type_erreur IN ('generation_ia', 'plantage_navigateur', 'autre')),
    message      TEXT NOT NULL,
    contexte     JSONB,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_erreurs_systeme_type ON erreurs_systeme(type_erreur);
CREATE INDEX IF NOT EXISTS idx_erreurs_systeme_created ON erreurs_systeme(created_at DESC);

GRANT SELECT, INSERT, UPDATE, DELETE ON erreurs_systeme TO eduai_app;
