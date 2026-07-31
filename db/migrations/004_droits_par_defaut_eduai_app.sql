-- Migration 004 : corrige un problème structurel de droits, révélé par
-- l'incident du 31/07/2026 (base documentaire RAG inaccessible en
-- production avec "permission denied for table documents_pedagogiques").
--
-- Cause : les migrations sont exécutées via `sudo -u postgres psql`, donc
-- les tables qu'elles créent appartiennent au superutilisateur postgres.
-- L'API se connecte avec un utilisateur applicatif dédié (eduai_app), qui
-- ne reçoit aucun droit automatiquement sur ces nouvelles tables — il faut
-- un GRANT explicite à chaque fois, ce qu'on a oublié pour la migration 002.
--
-- Cette migration corrige l'existant ET configure les droits par défaut
-- pour que ça ne se reproduise plus sur les prochaines migrations.

GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO eduai_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO eduai_app;

-- S'applique uniquement aux objets créés PAR LA SUITE par le rôle qui
-- exécute cette commande (postgres, puisque c'est lui qui lance les
-- migrations) — donc toute nouvelle table créée par une future migration
-- héritera automatiquement de ces droits pour eduai_app, sans qu'on ait à
-- s'en souvenir à chaque fois.
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO eduai_app;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public
    GRANT USAGE, SELECT ON SEQUENCES TO eduai_app;
