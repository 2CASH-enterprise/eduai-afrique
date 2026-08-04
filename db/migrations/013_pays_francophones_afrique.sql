-- Migration 013 : ajoute les pays francophones d'Afrique manquants à la
-- liste de couverture, discuté le 04/08. Tous inactifs par défaut, comme
-- toujours (voir migration 012) — l'Admin Plateforme les active
-- explicitement un par un, dès que leur corpus documentaire est jugé
-- suffisant.
--
-- Liste basée sur les pays membres de l'Afrique francophone (français
-- langue officielle ou coofficielle) : 21 pays au total, dont 7 déjà
-- présents (Bénin, Cameroun, Côte d'Ivoire, Gabon, RDC, Sénégal, Togo).

INSERT INTO pays_couverture (pays, actif) VALUES
    ('Burkina Faso', false),
    ('Burundi', false),
    ('Comores', false),
    ('République du Congo', false),
    ('Djibouti', false),
    ('Guinée', false),
    ('Guinée équatoriale', false),
    ('Madagascar', false),
    ('Mali', false),
    ('Niger', false),
    ('Rwanda', false),
    ('Seychelles', false),
    ('Tchad', false),
    ('République centrafricaine', false)
ON CONFLICT (pays) DO NOTHING;
