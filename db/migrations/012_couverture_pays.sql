-- Migration 012 : blocage des inscriptions pour les pays sans corpus
-- documentaire suffisant, discuté et cadré le 04/08.
--
-- Statut explicite par pays (décidé par l'Admin Plateforme, pas déduit
-- automatiquement du nombre de documents) — un pays reste bloqué tant que
-- l'équipe n'a pas jugé son corpus suffisant, même s'il contient déjà
-- quelques documents.
--
-- Seule la Côte d'Ivoire est active au lancement (74 documents indexés,
-- large couverture collège+lycée) — les autres pays restent bloqués
-- jusqu'à activation manuelle, y compris le Cameroun (corpus encore
-- minimal) et le Sénégal (14 documents, jugé encore insuffisant pour
-- l'instant).

CREATE TABLE IF NOT EXISTS pays_couverture (
    pays        TEXT PRIMARY KEY,
    actif       BOOLEAN NOT NULL DEFAULT false,
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

INSERT INTO pays_couverture (pays, actif) VALUES
    ('Cameroun', false),
    ('Sénégal', false),
    ('Côte d''Ivoire', true),
    ('République démocratique du Congo', false),
    ('Bénin', false),
    ('Togo', false),
    ('Gabon', false)
ON CONFLICT (pays) DO NOTHING;

-- Conserve les tentatives d'inscription pour un pays non couvert — permet
-- de recontacter ces personnes dès l'activation de leur pays.
CREATE TABLE IF NOT EXISTS liste_attente_inscriptions (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email       TEXT NOT NULL,
    pays        TEXT NOT NULL,
    role        TEXT NOT NULL DEFAULT 'enseignant',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (email, pays)
);

GRANT SELECT, INSERT, UPDATE, DELETE ON pays_couverture TO eduai_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON liste_attente_inscriptions TO eduai_app;
