-- Migration 006 : un enseignant peut désormais dispenser des cours dans
-- plusieurs établissements (TODO.md point 2), sans que ça remette en cause
-- son établissement principal.
--
-- On étend la table d'invitations existante plutôt que d'en créer une
-- nouvelle : une invitation "classique" (classe_id/matiere_id NULL) reste
-- une invitation à REJOINDRE un établissement (comportement du point 1,
-- inchangé) ; une invitation qui porte une classe_id/matiere_id est une
-- invitation à ENSEIGNER cette classe précise — l'acceptation crée
-- l'affectation sans toucher à l'établissement principal de l'enseignant,
-- et sans limite de nombre (contrairement à "rejoindre", qui reste unique).

ALTER TABLE invitations_enseignants ADD COLUMN IF NOT EXISTS classe_id UUID REFERENCES classes(id) ON DELETE CASCADE;
ALTER TABLE invitations_enseignants ADD COLUMN IF NOT EXISTS matiere_id UUID REFERENCES matieres(id) ON DELETE CASCADE;

-- Garde-fou : une invitation à une classe précise doit porter les DEUX
-- champs (classe ET matière), jamais un seul — sinon l'affectation créée à
-- l'acceptation serait incomplète.
ALTER TABLE invitations_enseignants DROP CONSTRAINT IF EXISTS invitations_enseignants_classe_matiere_coherentes;
ALTER TABLE invitations_enseignants ADD CONSTRAINT invitations_enseignants_classe_matiere_coherentes
    CHECK ((classe_id IS NULL) = (matiere_id IS NULL));
