-- Migration 015 : contrôle de quelles cartes apparaissent sur le portail
-- public (discuté et cadré le 05/08), en préparation du lancement en test
-- ouvert du seul module Enseignant.
--
-- Option retenue : cartes inactives complètement invisibles (pas de
-- "Bientôt disponible" grisé) — plus propre, aucune ambiguïté.
--
-- Admin Plateforme n'est PAS dans cette table : ce n'est pas un module
-- qu'on active un jour pour le grand public, c'est un outil interne pour
-- l'équipe, retiré définitivement du portail public (accessible par URL
-- directe uniquement) — logique différente de "en attente d'activation".

CREATE TABLE IF NOT EXISTS modules_actifs (
    module      TEXT PRIMARY KEY,
    actif       BOOLEAN NOT NULL DEFAULT false,
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

INSERT INTO modules_actifs (module, actif) VALUES
    ('eleve', false),
    ('enseignant', true),
    ('direction', false),
    ('parent', false),
    ('administration', false)
ON CONFLICT (module) DO NOTHING;

GRANT SELECT, INSERT, UPDATE, DELETE ON modules_actifs TO eduai_app;
