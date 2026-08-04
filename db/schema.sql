-- ============================================================================
-- ÉduAI Afrique — Schéma PostgreSQL (V1)
-- ============================================================================
-- Convention :
--   - Toutes les clés primaires en UUID (portable, pas de collision entre
--     établissements, facile à exposer publiquement sans fuite d'information).
--   - Toutes les tables ont created_at / updated_at.
--   - Les champs "métadonnées flexibles" (statistiques, tags) utilisent JSONB
--     plutôt que Firebase séparé — Postgres gère très bien ce cas d'usage.
--   - Suppression logique (soft delete) via colonne deleted_at plutôt que
--     DELETE physique, pour garder l'historique (notes, bulletins, paiements).
-- ============================================================================

CREATE EXTENSION IF NOT EXISTS "pgcrypto";  -- pour gen_random_uuid()

-- Fonction utilitaire : met à jour updated_at automatiquement
CREATE OR REPLACE FUNCTION trigger_set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- 1. ÉTABLISSEMENTS & PARAMÉTRAGE (Module 1)
-- ============================================================================

CREATE TABLE etablissements (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    nom                 TEXT NOT NULL,
    pays                TEXT NOT NULL,               -- 'Cameroun', 'Sénégal', ...
    ville               TEXT,
    devise              TEXT NOT NULL DEFAULT 'FCFA',
    logo_url            TEXT,
    reglement_url       TEXT,                         -- PDF du règlement intérieur
    email_contact       TEXT,
    telephone_contact   TEXT,
    niveau_abonnement   TEXT NOT NULL DEFAULT 'starter'
                        CHECK (niveau_abonnement IN ('starter', 'premium', 'ministere')),
    quota_requetes_ia_mois      INTEGER NOT NULL DEFAULT 1000,
    quota_generation_exercices_mois INTEGER NOT NULL DEFAULT 500,
    actif               BOOLEAN NOT NULL DEFAULT true,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at          TIMESTAMPTZ
);
CREATE TRIGGER set_updated_at BEFORE UPDATE ON etablissements
    FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

CREATE TABLE annees_scolaires (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    etablissement_id    UUID NOT NULL REFERENCES etablissements(id) ON DELETE CASCADE,
    libelle             TEXT NOT NULL,                -- '2026-2027'
    date_debut          DATE NOT NULL,
    date_fin            DATE NOT NULL,
    est_active          BOOLEAN NOT NULL DEFAULT true,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (etablissement_id, libelle)
);

CREATE TABLE cycles (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    etablissement_id    UUID NOT NULL REFERENCES etablissements(id) ON DELETE CASCADE,
    nom                 TEXT NOT NULL,                -- 'Premier Cycle', 'Second Cycle'
    ordre               INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE niveaux (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    cycle_id            UUID NOT NULL REFERENCES cycles(id) ON DELETE CASCADE,
    nom                 TEXT NOT NULL,                -- '6ème', 'Terminale D'
    ordre               INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE classes (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    etablissement_id    UUID NOT NULL REFERENCES etablissements(id) ON DELETE CASCADE,
    niveau_id           UUID NOT NULL REFERENCES niveaux(id) ON DELETE CASCADE,
    annee_scolaire_id   UUID NOT NULL REFERENCES annees_scolaires(id) ON DELETE CASCADE,
    nom                 TEXT NOT NULL,                -- '6ème A'
    filiere             TEXT,                         -- 'Général', 'Terminale D', ...
    effectif_max        INTEGER,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_classes_etablissement ON classes(etablissement_id);
CREATE INDEX idx_classes_annee ON classes(annee_scolaire_id);

CREATE TABLE matieres (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    nom                 TEXT NOT NULL UNIQUE,         -- 'Mathématiques', 'Français', ...
    code                TEXT NOT NULL UNIQUE           -- 'MATH', 'FR', 'PC', 'SVT', 'HG', 'INFO'
);

-- Référentiel pédagogique : quel programme/manuel un établissement suit
-- pour une matière et un niveau donnés.
CREATE TABLE referentiels_pedagogiques (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    etablissement_id    UUID NOT NULL REFERENCES etablissements(id) ON DELETE CASCADE,
    niveau_id           UUID NOT NULL REFERENCES niveaux(id) ON DELETE CASCADE,
    matiere_id          UUID NOT NULL REFERENCES matieres(id) ON DELETE CASCADE,
    programme_officiel  TEXT NOT NULL,                -- 'Programme Cameroun 2026-2027'
    manuel_titre        TEXT,
    manuel_editeur      TEXT,
    manuel_edition      TEXT,
    UNIQUE (etablissement_id, niveau_id, matiere_id)
);

-- Calendrier pédagogique : quel chapitre est prévu quel mois
CREATE TABLE calendrier_pedagogique (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    referentiel_id      UUID NOT NULL REFERENCES referentiels_pedagogiques(id) ON DELETE CASCADE,
    mois                DATE NOT NULL,                -- premier jour du mois concerné
    chapitre_titre      TEXT NOT NULL,
    competences         TEXT[],
    ordre               INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX idx_calendrier_referentiel ON calendrier_pedagogique(referentiel_id);

-- ============================================================================
-- 2. UTILISATEURS (base commune à tous les rôles)
-- ============================================================================

CREATE TABLE utilisateurs (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    etablissement_id    UUID REFERENCES etablissements(id) ON DELETE CASCADE,
    -- NULL possible pour un admin plateforme multi-établissements
    pays                TEXT,
    -- Seulement pertinent pour un enseignant indépendant (etablissement_id
    -- NULL) — pour tout le monde d'autre, le pays vient de l'établissement.
    role                TEXT NOT NULL
                        CHECK (role IN ('admin_plateforme', 'direction', 'administratif',
                                         'enseignant', 'eleve', 'parent')),
    email               TEXT UNIQUE,
    telephone           TEXT,
    mot_de_passe_hash   TEXT NOT NULL,
    nom                 TEXT NOT NULL,
    prenom              TEXT NOT NULL,
    photo_url           TEXT,
    actif               BOOLEAN NOT NULL DEFAULT true,
    derniere_connexion  TIMESTAMPTZ,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at          TIMESTAMPTZ
);
CREATE INDEX idx_utilisateurs_etablissement ON utilisateurs(etablissement_id);
CREATE INDEX idx_utilisateurs_role ON utilisateurs(role);
CREATE TRIGGER set_updated_at BEFORE UPDATE ON utilisateurs
    FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

-- Extension "élève" : infos spécifiques + rattachement à une classe
CREATE TABLE eleves (
    utilisateur_id      UUID PRIMARY KEY REFERENCES utilisateurs(id) ON DELETE CASCADE,
    classe_id           UUID NOT NULL REFERENCES classes(id) ON DELETE CASCADE,
    matricule           TEXT,
    date_naissance      DATE,
    UNIQUE (matricule)
);
CREATE INDEX idx_eleves_classe ON eleves(classe_id);

-- Extension "enseignant"
CREATE TABLE enseignants (
    utilisateur_id      UUID PRIMARY KEY REFERENCES utilisateurs(id) ON DELETE CASCADE,
    specialite          TEXT,
    date_embauche       DATE
);

-- Affectation enseignant → classe → matière (un enseignant peut enseigner
-- plusieurs matières dans plusieurs classes)
CREATE TABLE affectations_enseignants (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    enseignant_id       UUID NOT NULL REFERENCES enseignants(utilisateur_id) ON DELETE CASCADE,
    classe_id           UUID NOT NULL REFERENCES classes(id) ON DELETE CASCADE,
    matiere_id          UUID NOT NULL REFERENCES matieres(id) ON DELETE CASCADE,
    UNIQUE (enseignant_id, classe_id, matiere_id)
);
CREATE INDEX idx_affectations_enseignant ON affectations_enseignants(enseignant_id);
CREATE INDEX idx_affectations_classe ON affectations_enseignants(classe_id);

-- Invitation d'un enseignant à rejoindre un établissement (classe_id ET
-- matiere_id NULL), OU invitation à enseigner une classe précise sans
-- devenir membre principal (les deux renseignés) — voir TODO.md points 1
-- et 2. Portée V1 : un enseignant ne peut avoir qu'un seul établissement
-- principal à la fois, mais un nombre illimité d'affectations "invitées"
-- dans d'autres établissements.
CREATE TABLE invitations_enseignants (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    etablissement_id    UUID NOT NULL REFERENCES etablissements(id) ON DELETE CASCADE,
    enseignant_id       UUID NOT NULL REFERENCES utilisateurs(id) ON DELETE CASCADE,
    classe_id           UUID REFERENCES classes(id) ON DELETE CASCADE,
    matiere_id          UUID REFERENCES matieres(id) ON DELETE CASCADE,
    statut              TEXT NOT NULL DEFAULT 'en_attente'
                        CHECK (statut IN ('en_attente', 'acceptee', 'refusee')),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    traitee_at          TIMESTAMPTZ,
    CONSTRAINT invitations_enseignants_classe_matiere_coherentes
        CHECK ((classe_id IS NULL) = (matiere_id IS NULL))
);
CREATE INDEX idx_invitations_enseignant ON invitations_enseignants(enseignant_id);
CREATE INDEX idx_invitations_etablissement ON invitations_enseignants(etablissement_id);

-- Lien parent ↔ élève (un parent peut avoir plusieurs enfants,
-- un élève peut avoir plusieurs tuteurs légaux)
CREATE TABLE parents_eleves (
    parent_id           UUID NOT NULL REFERENCES utilisateurs(id) ON DELETE CASCADE,
    eleve_id            UUID NOT NULL REFERENCES eleves(utilisateur_id) ON DELETE CASCADE,
    lien                TEXT DEFAULT 'parent',        -- 'parent', 'tuteur', ...
    PRIMARY KEY (parent_id, eleve_id)
);

-- ============================================================================
-- 3. BASE PÉDAGOGIQUE — EXERCICES (Module 0, cœur du système)
-- ============================================================================

CREATE TABLE exercices (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    -- NULL = exercice de la bibliothèque commune ÉduAI Afrique (partagé entre
    -- établissements). Sinon rattaché à un établissement (banque interne).
    etablissement_id    UUID REFERENCES etablissements(id) ON DELETE CASCADE,

    pays                TEXT NOT NULL,
    niveau_id           UUID NOT NULL REFERENCES niveaux(id),
    matiere_id          UUID NOT NULL REFERENCES matieres(id),
    theme               TEXT NOT NULL,
    sous_theme          TEXT,
    type_exercice       TEXT NOT NULL DEFAULT 'application'
                        CHECK (type_exercice IN ('application', 'probleme', 'qcm', 'controle', 'devoir')),
    difficulte          TEXT NOT NULL DEFAULT 'moyen'
                        CHECK (difficulte IN ('facile', 'moyen', 'difficile')),

    enonce              TEXT NOT NULL,
    corrige             TEXT NOT NULL,
    etapes              TEXT[],                       -- étapes de résolution
    contexte            TEXT,                          -- ancrage local ('Cameroun')
    programme           TEXT,                          -- 'Programme Cameroun 2026-2027'

    source              TEXT NOT NULL DEFAULT 'mistral_ai'
                        CHECK (source IN ('mistral_ai', 'python_genere', 'enseignant', 'import')),
    genere_par_utilisateur_id UUID REFERENCES utilisateurs(id),  -- si déposé par un enseignant

    validation_ia       BOOLEAN NOT NULL DEFAULT false,
    validation_humaine   BOOLEAN NOT NULL DEFAULT false,
    valide_par_id       UUID REFERENCES utilisateurs(id),
    date_validation     TIMESTAMPTZ,
    statut              TEXT NOT NULL DEFAULT 'brouillon'
                        CHECK (statut IN ('brouillon', 'en_validation', 'valide', 'rejete', 'archive')),

    tags                TEXT[] DEFAULT '{}',
    liens                JSONB DEFAULT '{}',            -- {programme_officiel, ressources: []}
    statistiques        JSONB NOT NULL DEFAULT
                        '{"nombre_tentatives":0,"taux_reussite":0,"temps_moyen_secondes":0}',

    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at          TIMESTAMPTZ
);
CREATE INDEX idx_exercices_niveau_matiere ON exercices(niveau_id, matiere_id);
CREATE INDEX idx_exercices_etablissement ON exercices(etablissement_id);
CREATE INDEX idx_exercices_statut ON exercices(statut) WHERE deleted_at IS NULL;
CREATE INDEX idx_exercices_tags ON exercices USING GIN (tags);
CREATE INDEX idx_exercices_theme_trgm ON exercices USING GIN (to_tsvector('french', theme || ' ' || coalesce(sous_theme,'')));
CREATE TRIGGER set_updated_at BEFORE UPDATE ON exercices
    FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

-- Historique des tentatives d'un élève sur un exercice
-- (alimente les statistiques agrégées ci-dessus et le suivi de progrès)
CREATE TABLE tentatives_exercices (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    exercice_id         UUID NOT NULL REFERENCES exercices(id) ON DELETE CASCADE,
    eleve_id            UUID NOT NULL REFERENCES eleves(utilisateur_id) ON DELETE CASCADE,
    reussi              BOOLEAN,
    temps_passe_secondes INTEGER,
    reponse_donnee      TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_tentatives_eleve ON tentatives_exercices(eleve_id);
CREATE INDEX idx_tentatives_exercice ON tentatives_exercices(exercice_id);

-- ============================================================================
-- 4. COURS & RESSOURCES GÉNÉRÉES (Module 4 — Enseignant)
-- ============================================================================

-- Classes personnelles : contexte que l'enseignant indépendant déclare
-- lui-même (pas d'élèves réels, pas de bulletins) pour pouvoir utiliser le
-- vrai flux "Déposer un cours" sans dépendre d'un établissement. Niveau en
-- texte libre — aucune table de niveaux globale n'existe (niveaux est
-- propre à chaque établissement, voir cycles).
CREATE TABLE classes_personnelles (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    enseignant_id       UUID NOT NULL REFERENCES utilisateurs(id) ON DELETE CASCADE,
    nom                 TEXT NOT NULL,
    matiere_id          UUID NOT NULL REFERENCES matieres(id),
    niveau              TEXT NOT NULL,
    effectif            INTEGER,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_classes_personnelles_enseignant ON classes_personnelles(enseignant_id);

CREATE TABLE cours (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    enseignant_id       UUID NOT NULL REFERENCES enseignants(utilisateur_id) ON DELETE CASCADE,
    classe_id           UUID REFERENCES classes(id) ON DELETE CASCADE,
    classe_personnelle_id UUID REFERENCES classes_personnelles(id) ON DELETE CASCADE,
    matiere_id          UUID NOT NULL REFERENCES matieres(id),
    titre               TEXT NOT NULL,
    contenu_texte       TEXT,
    fichier_url         TEXT,                          -- PDF / Word / PPT déposé
    date_seance         DATE,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT cours_une_seule_classe CHECK ((classe_id IS NULL) != (classe_personnelle_id IS NULL))
);
CREATE INDEX idx_cours_enseignant ON cours(enseignant_id);
CREATE INDEX idx_cours_classe ON cours(classe_id);
CREATE TRIGGER set_updated_at BEFORE UPDATE ON cours
    FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

-- Ressources générées par l'IA à partir d'un cours (fiche, résumé, QCM, etc.)
CREATE TABLE ressources_generees (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    cours_id            UUID NOT NULL REFERENCES cours(id) ON DELETE CASCADE,
    type_ressource       TEXT NOT NULL
                        CHECK (type_ressource IN ('fiche_pedagogique', 'resume', 'exercices', 'corriges', 'qcm', 'devoir', 'controle')),
    contenu             JSONB NOT NULL,                 -- contenu structuré généré
    statut               TEXT NOT NULL DEFAULT 'en_attente'
                        CHECK (statut IN ('en_attente', 'valide', 'corrige', 'supprime')),
    valide_par_id        UUID REFERENCES utilisateurs(id),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_ressources_cours ON ressources_generees(cours_id);

-- ============================================================================
-- 5. DEVOIRS, NOTES, ABSENCES (Modules 4/5/6)
-- ============================================================================

CREATE TABLE devoirs (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    enseignant_id       UUID NOT NULL REFERENCES enseignants(utilisateur_id) ON DELETE CASCADE,
    classe_id           UUID NOT NULL REFERENCES classes(id) ON DELETE CASCADE,
    matiere_id          UUID NOT NULL REFERENCES matieres(id),
    titre               TEXT NOT NULL,
    description         TEXT,
    exercice_ids        UUID[] DEFAULT '{}',           -- exercices rattachés
    date_limite         TIMESTAMPTZ NOT NULL,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_devoirs_classe ON devoirs(classe_id);

CREATE TABLE devoirs_soumissions (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    devoir_id           UUID NOT NULL REFERENCES devoirs(id) ON DELETE CASCADE,
    eleve_id            UUID NOT NULL REFERENCES eleves(utilisateur_id) ON DELETE CASCADE,
    fichier_url         TEXT,
    contenu_texte       TEXT,
    note                NUMERIC(4,2),
    commentaire         TEXT,
    soumis_le           TIMESTAMPTZ,
    corrige_le          TIMESTAMPTZ,
    UNIQUE (devoir_id, eleve_id)
);

CREATE TABLE notes (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    eleve_id            UUID NOT NULL REFERENCES eleves(utilisateur_id) ON DELETE CASCADE,
    matiere_id          UUID NOT NULL REFERENCES matieres(id),
    enseignant_id       UUID NOT NULL REFERENCES enseignants(utilisateur_id),
    type_evaluation     TEXT NOT NULL DEFAULT 'controle'
                        CHECK (type_evaluation IN ('controle', 'devoir', 'examen', 'participation')),
    valeur              NUMERIC(4,2) NOT NULL,
    bareme               NUMERIC(4,2) NOT NULL DEFAULT 20,
    trimestre           INTEGER NOT NULL CHECK (trimestre IN (1, 2, 3)),
    annee_scolaire_id   UUID NOT NULL REFERENCES annees_scolaires(id),
    commentaire         TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_notes_eleve ON notes(eleve_id);
CREATE INDEX idx_notes_eleve_trimestre ON notes(eleve_id, trimestre, annee_scolaire_id);

CREATE TABLE absences (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    eleve_id            UUID NOT NULL REFERENCES eleves(utilisateur_id) ON DELETE CASCADE,
    date_absence        DATE NOT NULL,
    type_absence        TEXT NOT NULL DEFAULT 'absence'
                        CHECK (type_absence IN ('absence', 'retard')),
    justifie            BOOLEAN NOT NULL DEFAULT false,
    motif               TEXT,
    signale_par_id      UUID REFERENCES utilisateurs(id),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_absences_eleve ON absences(eleve_id);

-- Bulletins (document généré/figé par trimestre)
CREATE TABLE bulletins (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    eleve_id            UUID NOT NULL REFERENCES eleves(utilisateur_id) ON DELETE CASCADE,
    annee_scolaire_id   UUID NOT NULL REFERENCES annees_scolaires(id),
    trimestre           INTEGER NOT NULL CHECK (trimestre IN (1, 2, 3)),
    moyenne_generale    NUMERIC(4,2),
    rang_classe         INTEGER,
    fichier_pdf_url     TEXT,
    genere_le           TIMESTAMPTZ,
    UNIQUE (eleve_id, annee_scolaire_id, trimestre)
);

-- ============================================================================
-- 6. PAIEMENTS (Module 2 — Administration)
-- ============================================================================

CREATE TABLE paiements (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    eleve_id            UUID NOT NULL REFERENCES eleves(utilisateur_id) ON DELETE CASCADE,
    annee_scolaire_id   UUID NOT NULL REFERENCES annees_scolaires(id),
    montant_du          NUMERIC(12,2) NOT NULL,
    montant_paye        NUMERIC(12,2) NOT NULL DEFAULT 0,
    devise              TEXT NOT NULL DEFAULT 'FCFA',
    date_echeance       DATE,
    statut              TEXT NOT NULL DEFAULT 'en_attente'
                        CHECK (statut IN ('en_attente', 'partiel', 'complet', 'en_retard')),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_paiements_eleve ON paiements(eleve_id);
CREATE TRIGGER set_updated_at BEFORE UPDATE ON paiements
    FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

-- ============================================================================
-- 7. NOTIFICATIONS
-- ============================================================================

CREATE TABLE notifications (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    utilisateur_id      UUID NOT NULL REFERENCES utilisateurs(id) ON DELETE CASCADE,
    titre               TEXT NOT NULL,
    message             TEXT NOT NULL,
    type_notification    TEXT NOT NULL DEFAULT 'info'
                        CHECK (type_notification IN ('info', 'note', 'devoir', 'absence', 'paiement', 'alerte')),
    lien_ressource       TEXT,                          -- deep link vers l'objet concerné
    lue                 BOOLEAN NOT NULL DEFAULT false,
    envoyee_par_canal    TEXT[] DEFAULT '{}',            -- ['app', 'sms', 'email']
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_notifications_utilisateur ON notifications(utilisateur_id, lue);

-- ============================================================================
-- 7b. BASE DOCUMENTAIRE (RAG) — alimente la génération IA, jamais partagée
-- ============================================================================
-- Voir migrations/002_base_documentaire.sql pour le commentaire complet sur
-- la politique de contenu (documents publics ou rédigés par l'établissement
-- uniquement — jamais de manuel scolaire commercial scanné).

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE documents_pedagogiques (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    etablissement_id    UUID REFERENCES etablissements(id) ON DELETE CASCADE,
    -- NULL = portée plateforme entière (programme_officiel, genere_valide) ;
    -- une vraie valeur = privé à un établissement (notes_cours uniquement).
    depose_par_id       UUID REFERENCES utilisateurs(id),
    type_document        TEXT NOT NULL DEFAULT 'notes_cours'
                        CHECK (type_document IN ('programme_officiel', 'notes_cours', 'genere_valide')),
    pays                TEXT NOT NULL,                 -- isole le corpus par pays (voir migration 009)
    niveau_id           UUID REFERENCES niveaux(id),
    matiere_id          UUID REFERENCES matieres(id),
    titre               TEXT NOT NULL,
    nombre_pages        INTEGER,
    statut              TEXT NOT NULL DEFAULT 'en_traitement'
                        CHECK (statut IN ('en_traitement', 'indexe', 'erreur')),
    erreur_traitement   TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT documents_pedagogiques_notes_cours_proprietaire CHECK (
        type_document != 'notes_cours'
        OR (etablissement_id IS NOT NULL AND depose_par_id IS NOT NULL)
    )
);
CREATE INDEX idx_documents_etablissement ON documents_pedagogiques(etablissement_id);
CREATE INDEX idx_documents_niveau_matiere ON documents_pedagogiques(niveau_id, matiere_id);
CREATE INDEX idx_documents_pays ON documents_pedagogiques(pays);

-- Partage explicite d'une note de cours avec un ou plusieurs collègues du
-- même établissement — jamais automatique, jamais entre établissements.
CREATE TABLE documents_partages (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id         UUID NOT NULL REFERENCES documents_pedagogiques(id) ON DELETE CASCADE,
    partage_avec_id     UUID NOT NULL REFERENCES utilisateurs(id) ON DELETE CASCADE,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (document_id, partage_avec_id)
);
CREATE INDEX idx_documents_partages_document ON documents_partages(document_id);
CREATE INDEX idx_documents_partages_utilisateur ON documents_partages(partage_avec_id);

CREATE TABLE passages_documents (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id         UUID NOT NULL REFERENCES documents_pedagogiques(id) ON DELETE CASCADE,
    ordre               INTEGER NOT NULL,
    contenu             TEXT NOT NULL,
    embedding           vector(1024)
);
CREATE INDEX idx_passages_document ON passages_documents(document_id);
CREATE INDEX idx_passages_embedding ON passages_documents
    USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- ============================================================================
-- 8. USAGE / QUOTAS IA (pilotage des coûts Mistral par établissement)
-- ============================================================================

CREATE TABLE usage_ia (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    etablissement_id    UUID NOT NULL REFERENCES etablissements(id) ON DELETE CASCADE,
    utilisateur_id      UUID REFERENCES utilisateurs(id),
    type_action          TEXT NOT NULL
                        CHECK (type_action IN ('generation_exercice', 'generation_ressource_cours', 'analyse_direction', 'autre')),
    tokens_utilises      INTEGER,
    cout_estime_usd      NUMERIC(8,4),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_usage_ia_etablissement_date ON usage_ia(etablissement_id, created_at);

-- ============================================================================
-- VUES UTILES
-- ============================================================================

-- Moyenne d'un élève par matière et par trimestre (pour tableau de bord parent/direction)
CREATE VIEW vue_moyennes_eleve AS
SELECT
    eleve_id,
    matiere_id,
    trimestre,
    annee_scolaire_id,
    ROUND(AVG(valeur / bareme * 20), 2) AS moyenne_sur_20,
    COUNT(*) AS nombre_notes
FROM notes
GROUP BY eleve_id, matiere_id, trimestre, annee_scolaire_id;

-- Exercices en attente de validation humaine, par établissement
-- (alimente le tableau de bord "Module Enseignant / Direction")
CREATE VIEW vue_exercices_a_valider AS
SELECT e.id, e.etablissement_id, e.niveau_id, e.matiere_id, e.theme, e.created_at
FROM exercices e
WHERE e.validation_humaine = false
  AND e.statut = 'en_validation'
  AND e.deleted_at IS NULL;

-- ============================================================================
-- Droits pour l'utilisateur applicatif (eduai_app)
-- ============================================================================
-- Sur une installation neuve, ce script est généralement appliqué par le
-- superutilisateur postgres, alors que l'API se connecte avec un utilisateur
-- applicatif dédié (eduai_app, créé séparément). Sans ce réglage, chaque
-- nouvelle table créée par une future migration (elle aussi exécutée par
-- postgres) resterait inaccessible à l'API tant qu'on n'y pense pas
-- explicitement — voir l'incident du 31/07/2026 (migration 004).
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO eduai_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO eduai_app;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO eduai_app;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public
    GRANT USAGE, SELECT ON SEQUENCES TO eduai_app;

-- ============================================================================
-- ============================================================================
-- Génération libre — persistante depuis le 03/08 (voir migration 011)
-- ============================================================================
-- Séparée de `exercices` (bibliothèque commune + pipeline hors-ligne, qui
-- exige un niveau_id réel) : ici niveau reste en texte libre, comme pour
-- classes_personnelles. Toujours gratuite, jamais concernée par les crédits.
CREATE TABLE exercices_generation_libre (
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
CREATE INDEX idx_exgl_enseignant ON exercices_generation_libre(enseignant_id);
CREATE INDEX idx_exgl_statut ON exercices_generation_libre(statut);

-- ============================================================================
-- Couverture par pays — blocage des inscriptions sans corpus (migration 012)
-- ============================================================================
CREATE TABLE pays_couverture (
    pays        TEXT PRIMARY KEY,
    actif       BOOLEAN NOT NULL DEFAULT false,
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
-- 21 pays francophones d'Afrique (voir migrations 012 et 013) — tous
-- inactifs par défaut, activés explicitement un par un par l'Admin
-- Plateforme selon l'avancement du corpus documentaire de chacun.
INSERT INTO pays_couverture (pays, actif) VALUES
    ('Cameroun', false), ('Sénégal', false), ('Côte d''Ivoire', false),
    ('République démocratique du Congo', false), ('Bénin', false), ('Togo', false), ('Gabon', false),
    ('Burkina Faso', false), ('Burundi', false), ('Comores', false), ('République du Congo', false),
    ('Djibouti', false), ('Guinée', false), ('Guinée équatoriale', false), ('Madagascar', false),
    ('Mali', false), ('Niger', false), ('Rwanda', false), ('Seychelles', false), ('Tchad', false),
    ('République centrafricaine', false);

CREATE TABLE liste_attente_inscriptions (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email       TEXT NOT NULL,
    pays        TEXT NOT NULL,
    role        TEXT NOT NULL DEFAULT 'enseignant',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (email, pays)
);

-- Système de crédits enseignant (voir migration 008 pour la logique complète)
-- ============================================================================
CREATE TABLE credits_enseignant (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    enseignant_id       UUID NOT NULL REFERENCES utilisateurs(id) ON DELETE CASCADE,
    delta               INTEGER NOT NULL,
    motif               TEXT NOT NULL
                        CHECK (motif IN ('validation_simple', 'validation_corrigee', 'depot_cours')),
    reference_id        UUID,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_credits_enseignant ON credits_enseignant(enseignant_id);

-- ============================================================================
-- FIN DU SCHÉMA V1
-- ============================================================================
