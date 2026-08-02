-- Migration 010 : complète le référentiel matières avec les disciplines
-- identifiées sur le catalogue DPFC (Côte d'Ivoire) mais absentes jusqu'ici
-- de la plateforme — nécessaire avant de pouvoir déposer leurs programmes
-- officiels (l'import échouerait sinon avec "Matière inconnue").
--
-- TICE non ajoutée séparément : couverte par "Informatique", déjà présente.

INSERT INTO matieres (nom, code) VALUES
    ('Anglais', 'ANG'),
    ('Allemand', 'ALL'),
    ('Espagnol', 'ESP'),
    ('Arts Plastiques', 'AP'),
    ('Education Musicale', 'MUS'),
    ('EPS', 'EPS'),
    ('EDHC', 'EDHC'),
    ('Philosophie', 'PHILO')
ON CONFLICT (nom) DO NOTHING;
