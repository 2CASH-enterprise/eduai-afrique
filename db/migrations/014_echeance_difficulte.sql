-- Migration 014 : trois des quatre points retenus le 04/08 pour compléter
-- le module Enseignant avant le lancement.
--
-- - date_echeance : point 3 (assigner un contenu avec une échéance)
-- - difficulte : point 7 (niveau de difficulté ciblé à la génération),
--   sur les deux points d'entrée IA (Déposer un cours, Génération libre)
--
-- Le point 4 (dupliquer un cours) et le point 1 (export PDF) ne
-- nécessitent aucun changement de schéma — juste de nouveaux endpoints.

ALTER TABLE cours ADD COLUMN IF NOT EXISTS date_echeance DATE;
ALTER TABLE cours ADD COLUMN IF NOT EXISTS difficulte TEXT NOT NULL DEFAULT 'moyen'
    CHECK (difficulte IN ('facile', 'moyen', 'difficile'));

ALTER TABLE exercices_generation_libre ADD COLUMN IF NOT EXISTS difficulte TEXT NOT NULL DEFAULT 'moyen'
    CHECK (difficulte IN ('facile', 'moyen', 'difficile'));
