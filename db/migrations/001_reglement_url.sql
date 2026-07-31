-- Migration 001 : paramétrage établissement (règlement intérieur)
-- Exécuter sur une base déjà en production, en plus de schema.sql (qui a
-- été mis à jour pour les nouvelles installations, mais ne rejoue pas sur
-- une base existante).

ALTER TABLE etablissements ADD COLUMN IF NOT EXISTS reglement_url TEXT;
