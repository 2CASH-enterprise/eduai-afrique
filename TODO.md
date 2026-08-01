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

## 2. Un enseignant peut dispenser des cours dans plusieurs établissements — ✅ FAIT le 01/08

**Besoin exprimé** : un enseignant n'est pas forcément lié à une seule école.
Dans "Mes classes", il faut alors afficher clairement le nom de
l'établissement à côté de chaque classe, pour que l'enseignant s'y retrouve.

**Construit et déployé** : la table `invitations_enseignants` porte
désormais optionnellement une `classe_id`/`matiere_id`. Sans elles, c'est
l'invitation "classique" à rejoindre un établissement (point 1, exclusive).
Avec elles, c'est une invitation à enseigner cette classe précise —
l'acceptation crée directement l'affectation, **sans jamais toucher
l'établissement principal**, et sans limite de nombre. C'est ce qui permet
concrètement le multi-établissement : un enseignant peut accepter autant
d'invitations "classe précise" que nécessaire, dans autant d'établissements
différents, tout en gardant un seul établissement principal.

`GET /enseignant/mes-classes` affiche maintenant `etablissement_nom` pour
chaque classe. Interfaces mises à jour des deux côtés (bascule "Rejoindre
l'établissement" / "Enseigner une classe précise" côté Administration,
libellé distinct côté Enseignant selon le type d'invitation reçue).

**Bénéfice inattendu** : ce même mécanisme comble aussi une partie du point
3 (aucun moyen d'ajouter une affectation à un enseignant déjà existant) —
un établissement peut désormais affecter un enseignant à une nouvelle
classe/matière chez lui aussi, pas seulement ailleurs, via ce même flux
d'invitation.

---

## 3. Structure classes/niveaux incomplète — ✅ FAIT le 01/08 (bloquait Collège Vogt)

**Constat, diagnostiqué le 31/07** : `cycles` et `niveaux` sont des tables
**propres à chaque établissement** (pas globales, contrairement à
`matieres`). Le Collège Vogt (établissement réel, pas un compte de test) n'a
actuellement qu'un seul cycle ("Premier Cycle") et un seul niveau ("6ème")
en base — d'où le symptôme observé : impossible de créer une classe sur un
autre niveau, ce niveau unique apparaît partout où un choix de classe est
attendu.

**Construit et déployé** : nouveau module `structure_scolaire.py` — un
établissement peut désormais créer lui-même ses années scolaires, cycles,
niveaux et classes via l'interface (`/administration` → onglet
"Structure"), sans plus jamais dépendre de nous en SQL manuel. Chaîne
complète testée de bout en bout sur un établissement entièrement neuf
(année scolaire → cycle → niveau → classe).

**Pour débloquer concrètement Collège Vogt** : se connecter avec un compte
administratif de cet établissement, aller dans Structure, et ajouter les
niveaux manquants (5ème, 4ème, 3ème...) puis leurs classes.

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
