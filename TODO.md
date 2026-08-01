# TODO — ÉduAI Afrique

Tâches identifiées le 31/07/2026, à traiter dans une prochaine session. Chaque
entrée capture le besoin exprimé, ce qu'on a compris de la discussion, et les
implications techniques identifiées — pour ne pas avoir à tout ré-expliquer
la prochaine fois.

---

## 1. Connexion indépendante pour un enseignant (sans établissement inscrit) — ✅ FAIT le 01/08

**Besoin exprimé** : un enseignant dont l'établissement n'est pas encore
inscrit sur la plateforme doit pouvoir quand même s'inscrire et utiliser la
plateforme de façon autonome (préparer ses cours, bénéficier de l'IA...),
sans être rattaché à aucune école. Plus tard, quand son établissement
s'inscrit à son tour, celui-ci doit pouvoir **l'inviter à le rejoindre** —
sans repartir de zéro.

**Construit et déployé** :
- `POST /auth/inscription-enseignant` — auto-inscription, connexion
  automatique, `etablissement_id = NULL`.
- `POST /enseignant/generation-libre` — génération d'exercice à la demande
  sur niveau (texte libre) + matière + thème choisis, sans classe ni
  établissement requis. Contenu jamais persisté, toujours accompagné d'un
  avertissement explicite (non relu par un humain).
- Flux d'invitation complet : `POST /administration/invitations` (un
  établissement invite un enseignant indépendant existant par email) +
  `GET/POST /enseignant/invitations` (consulter, accepter, refuser).
- Interfaces des deux côtés (bascule connexion/inscription côté Enseignant,
  écran Invitations des deux côtés, écran Génération libre).

**Limite assumée pour cette V1** : un enseignant déjà rattaché à un
établissement ne peut pas être invité par un autre — le multi-établissement
simultané reste le point 2 ci-dessous, pas encore traité.

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

## 4. Version hors-ligne de l'application (correction du 31/07 : ce n'est PAS "en ligne")

**Besoin exprimé, précisé** : pas une question de nom de domaine ou de
HTTPS — le vrai besoin est une **version qui fonctionne sans connexion
internet**, parce que les utilisateurs se trouvent parfois dans des zones
sans accès réseau. Un vrai chantier de fond, pas un réglage rapide.

**Implications techniques à explorer (pas encore creusées)** :
- Passage en PWA (progressive web app) avec service worker, pour permettre
  le chargement de l'app elle-même sans réseau.
- Stratégie de cache/stockage local (exercices déjà chargés, cours
  consultés...) pour un usage minimal hors-ligne.
- Question centrale à trancher : quelles actions doivent rester possibles
  hors-ligne (consulter un exercice déjà chargé, répondre à un exercice ?)
  et lesquelles nécessitent forcément une connexion (génération IA,
  connexion initiale, synchronisation des notes) ?
- Stratégie de synchronisation au retour de la connexion (ex : réponses
  données hors-ligne, à synchroniser ensuite).
- Discussion produit à avoir avant de coder quoi que ce soit : le périmètre
  hors-ligne réaliste pour une V1 (probablement partiel, pas l'app entière).

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

## 7. Brancher réellement la recherche RAG sur la génération de cours/exercices

`rag.rechercher_passages_pertinents` existe et est testée (voir la session
du corpus documentaire), mais n'est encore appelée nulle part dans le code
de génération réel (pipeline Maths/PC par templates, génération LLM
Mistral pour Français/SVT/HG). Tant que ce branchement n'est pas fait, tout
le travail du corpus documentaire (programmes officiels, notes de cours,
réinjection du contenu validé) n'a aucun effet concret sur ce que l'IA
génère.

---

## 8. CI/CD — déploiement automatique à chaque push

Mentionné plusieurs fois au fil des sessions comme prochaine étape
logique, jamais commencé. Objectif : GitHub Actions (ou équivalent) pour
automatiser ce qui est fait à la main aujourd'hui à chaque déploiement
(scp, extraction, migration, redémarrage des services).

---

## 9. Déposer les vrais programmes officiels MINESEC

Une fois récupérés par l'utilisateur (le site du MINESEC bloque l'accès
automatisé), à déposer via le module Admin Plateforme
(`POST /plateforme/documents`). Pas un chantier technique — juste une
tâche opérationnelle en attente du matériel source.

---

## Fait pendant la session du 31/07 (pour référence)

- Corpus documentaire RAG réorganisé (portée plateforme / privé / réinjection).
- Incident de production résolu (droits PostgreSQL pour `eduai_app`).
- Module Admin Plateforme complet construit et déployé (établissements,
  documents partagés, bibliothèque commune d'exercices).
