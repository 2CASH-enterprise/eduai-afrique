# TODO — ÉduAI Afrique

Tâches identifiées le 31/07/2026, à traiter dans une prochaine session. Chaque
entrée capture le besoin exprimé, ce qu'on a compris de la discussion, et les
implications techniques identifiées — pour ne pas avoir à tout ré-expliquer
la prochaine fois.

---

## 1. Connexion indépendante pour un enseignant (sans établissement inscrit)

**Besoin exprimé** : un enseignant dont l'établissement n'est pas encore
inscrit sur la plateforme doit pouvoir quand même s'inscrire et utiliser la
plateforme de façon autonome (préparer ses cours, bénéficier de l'IA...),
sans être rattaché à aucune école. Plus tard, quand son établissement
s'inscrit à son tour, celui-ci doit pouvoir **l'inviter à le rejoindre** —
sans repartir de zéro.

**Implications techniques identifiées (à valider avant de coder)** :
- Le compte enseignant doit pouvoir exister avec `etablissement_id = NULL`
  (actuellement, `get_enseignant_connecte` et les endpoints enseignant
  supposent tous un établissement — à revérifier précisément).
- Il faut un vrai **flux d'auto-inscription** pour les enseignants, qui
  n'existe pas du tout aujourd'hui (tous les comptes sont créés par un
  administratif ou en SQL direct).
- Il faut un **flux d'invitation** : un établissement invite (par email) un
  enseignant déjà existant sur la plateforme à le rejoindre, l'enseignant
  accepte, son compte se rattache à l'école.
- Se combine avec le point 2 ci-dessous : si un enseignant peut aussi
  travailler dans plusieurs écoles à la fois, `etablissement_id` unique sur
  `utilisateurs` ne suffit peut-être plus — voir la question d'architecture
  commune aux deux points.

---

## 2. Un enseignant peut dispenser des cours dans plusieurs établissements

**Besoin exprimé** : un enseignant n'est pas forcément lié à une seule école.
Dans "Mes classes", il faut alors afficher clairement le nom de
l'établissement à côté de chaque classe, pour que l'enseignant s'y retrouve.

**Implications techniques identifiées** :
- Question d'architecture centrale, à trancher avant de coder quoi que ce
  soit : est-ce qu'on garde `utilisateurs.etablissement_id` (un seul, comme
  aujourd'hui) et qu'on gère le multi-établissement uniquement via
  `affectations_enseignants` (qui pourrait porter sa propre notion
  d'établissement par affectation) ? Ou est-ce qu'on a réellement besoin
  d'une relation plusieurs-à-plusieurs entre enseignants et établissements ?
- Si un enseignant travaille dans plusieurs écoles, ses identifiants de
  connexion restent les mêmes partout (compte unique) — bien vérifier que
  ça reste cohérent avec l'isolation stricte des données entre
  établissements déjà en place ailleurs sur la plateforme.
- Écran "Mes classes" (`/enseignant/mes-classes`) à mettre à jour pour
  afficher le nom de l'établissement par classe, une fois l'architecture
  ci-dessus décidée.

---

## 3. Structure classes/niveaux incomplète — bloque un vrai client (Collège Vogt)

**Constat, diagnostiqué le 31/07** : `cycles` et `niveaux` sont des tables
**propres à chaque établissement** (pas globales, contrairement à
`matieres`). Le Collège Vogt (établissement réel, pas un compte de test) n'a
actuellement qu'un seul cycle ("Premier Cycle") et un seul niveau ("6ème")
en base — d'où le symptôme observé : impossible de créer une classe sur un
autre niveau, ce niveau unique apparaît partout où un choix de classe est
attendu.

**Cause racine** : il n'existe **aucun endpoint ni écran** pour qu'un
établissement crée lui-même ses cycles/niveaux/classes. Jusqu'ici, toujours
fait à la main en SQL par nous (pour "École Test" puis "Collège Vogt").

**Décision prise le 31/07** : ne pas corriger dans l'urgence — ajouté à
cette liste, à traiter dans une prochaine session. Le déblocage immédiat de
Collège Vogt (ajout manuel en SQL des niveaux/classes manquants) reste
possible à la demande en attendant.

**À construire** : écran + endpoints (`POST /administration/cycles`,
`/administration/niveaux`, et l'écran de création de classe qui manque déjà
aussi) pour qu'un établissement structure lui-même son organisation
scolaire, sans dépendre de nous.

---

## 4. "Version en ligne" de l'application

**Besoin exprimé** : pas encore clarifié précisément — la question a été
posée mais pas encore répondue. L'app tourne déjà en ligne sur le VPS
(`89.116.111.3`), donc il s'agit probablement de l'une de ces pistes,
à confirmer à la prochaine session :
- un vrai nom de domaine + HTTPS (au lieu de l'IP:port actuelle) ;
- une version mobile / installable (PWA) ;
- autre chose.

---

## 5. Confusion sur le libellé "Contenu du cours" — répondu, pas une tâche

Le champ "Contenu du cours" (formulaire de dépôt de cours, espace
Enseignant) sert à coller/saisir le contenu réel de la leçon enseignée —
c'est sur cette base que l'IA génère ensuite des ressources adaptées
(plutôt que sur le thème seul). Pas d'action nécessaire, sauf si le libellé
mérite d'être rendu plus explicite dans l'interface (ex : ajouter un texte
d'aide sous le champ).

---

## 6. Les identifiants d'un module ouvrent (partiellement) les autres modules

**Constat** : `/auth/login` est volontairement générique (ne vérifie que
email/mot de passe, jamais le rôle — chaque endpoint revérifie le rôle côté
serveur ensuite). Résultat côté UX : des identifiants Administration
"passent" l'écran de connexion du module Enseignant (token valide émis),
mais aucune donnée réelle n'est exposée (bloqué au niveau de chaque endpoint
spécifique). Pas de faille de sécurité de fond, mais une mauvaise
expérience : l'utilisateur se retrouve sur un écran vide/cassé au lieu d'un
message clair.

**Correctif identifié** : après connexion, chaque espace frontend doit
vérifier immédiatement (via un appel léger, ex. le premier chargement de
données du module) que le compte correspond bien au bon rôle, et afficher
"Ce compte n'a pas accès à cet espace" plutôt que de laisser entrer sur un
écran cassé.

---

## Fait pendant la session du 31/07 (pour référence)

- Corpus documentaire RAG réorganisé (portée plateforme / privé / réinjection).
- Incident de production résolu (droits PostgreSQL pour `eduai_app`).
- Module Admin Plateforme complet construit et déployé (établissements,
  documents partagés, bibliothèque commune d'exercices).
