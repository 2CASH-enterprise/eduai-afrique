# ÉduAI Afrique

Plateforme pédagogique intelligente pour l'Afrique francophone — bibliothèque
d'exercices générée automatiquement (templates déterministes + LLM), relue
par des enseignants, et exposée via une API multi-rôles (Enseignant, Élève,
Direction, Administration, Parent).

## Structure du projet

```
db/            Schéma PostgreSQL complet (tables, index, vues, triggers)
pipeline/      Génération et validation automatique des exercices
  generator_math.py            13 templates déterministes (6ème → Seconde), validés par SymPy
  generator_physique_chimie.py 9 templates déterministes (5ème → Seconde)
  generator_llm.py             Génération via Mistral AI (Français, SVT, Histoire-Géo)
  validation.py                Validation indépendante (recalcul SymPy, détection de dérive LLM)
  pipeline.py                  Orchestrateur : génération → validation → insertion PostgreSQL
  test_generator_llm.py        Tests du générateur LLM avec un client Mistral simulé
api/           API FastAPI
  app/main.py                  Point d'entrée
  app/routers/                 auth, exercices (enseignant), eleve, direction, administration, parent
  test_workflow*.py            Tests end-to-end par module (contre une vraie base PostgreSQL)
```

## Démarrage local

```bash
# 1. Dépendances
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 2. Base de données (PostgreSQL doit tourner)
createdb eduai_afrique
psql -d eduai_afrique -f db/schema.sql

# 3. Variables d'environnement
cp .env.example .env
# éditer .env avec vos vraies valeurs

# 4. Lancer l'API
cd api && uvicorn app.main:app --reload

# 5. Lancer le pipeline de génération (exemple : maths)
cd pipeline && python3 pipeline.py
```

## Tests

Chaque module de l'API a un script de test end-to-end qui s'exécute contre
une vraie base PostgreSQL (pas de mocks pour la base — les mocks ne sont
utilisés que pour l'API Mistral, qui n'est pas accessible dans tous les
environnements de développement) :

```bash
cd api
python3 test_workflow.py                 # Module Enseignant
python3 test_workflow_eleve.py           # Module Élève
python3 test_workflow_direction.py       # Module Direction (isolation multi-établissement)
python3 test_workflow_administration.py  # Module Administration
python3 test_workflow_parent.py          # Module Parent (isolation inter-familles)
```

## Principes d'architecture

- **Génération à deux vitesses** : Maths/Physique-Chimie via templates Python
  paramétrés (coût nul, calcul garanti juste par re-vérification indépendante
  SymPy/Decimal) ; Français/SVT/Histoire-Géo via Mistral AI, systématiquement
  marqués `validation_ia=false` — aucune validation automatique fiable
  n'existe pour ces matières, la relecture humaine n'est jamais contournée.
- **Authentification générique** : un seul endpoint `/auth/login` pour tous
  les rôles. Le rôle n'est jamais encodé dans le JWT — chaque dépendance
  (`get_enseignant_connecte`, `get_eleve_connecte`, etc.) revérifie
  l'appartenance directement en base à chaque requête.
- **Isolation testée, pas supposée** : périmètre enseignant (matières/niveaux
  réellement affectés), isolation inter-établissements (Direction,
  Administration), isolation inter-familles (Parent) — chacune vérifiée par
  un test qui simule une tentative d'accès non autorisée et confirme le rejet.

## Statut

V1 en développement. Voir le code pour le détail des choix et limites
documentées dans les docstrings (notamment les limites de cardinalité de
certains templates, à surveiller en passant à l'échelle).
