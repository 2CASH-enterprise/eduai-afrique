-- Migration 005 : permet à un établissement d'inviter un enseignant déjà
-- inscrit sur la plateforme de façon indépendante (etablissement_id NULL)
-- à le rejoindre. Portée volontairement restreinte à cette V1 : un
-- enseignant déjà rattaché à un autre établissement ne peut pas être
-- invité (le multi-établissement simultané est un chantier séparé,
-- voir TODO.md point 2).

CREATE TABLE IF NOT EXISTS invitations_enseignants (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    etablissement_id    UUID NOT NULL REFERENCES etablissements(id) ON DELETE CASCADE,
    enseignant_id       UUID NOT NULL REFERENCES utilisateurs(id) ON DELETE CASCADE,
    statut              TEXT NOT NULL DEFAULT 'en_attente'
                        CHECK (statut IN ('en_attente', 'acceptee', 'refusee')),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    traitee_at          TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_invitations_enseignant ON invitations_enseignants(enseignant_id);
CREATE INDEX IF NOT EXISTS idx_invitations_etablissement ON invitations_enseignants(etablissement_id);

-- Cohérent avec la correction structurelle de la migration 004 : cette
-- nouvelle table doit être accessible à l'utilisateur applicatif. Comme
-- ALTER DEFAULT PRIVILEGES a déjà été configuré pour le rôle postgres, ce
-- GRANT explicite est redondant en théorie mais gardé par prudence — coûte
-- rien et rend la migration indépendante de l'ordre d'exécution.
GRANT SELECT, INSERT, UPDATE, DELETE ON invitations_enseignants TO eduai_app;
