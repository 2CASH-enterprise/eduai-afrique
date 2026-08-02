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

## 4. Version hors-ligne — ✅ FAIT (V1) le 01/08, inactive en production tant qu'HTTPS n'est pas en place

**Périmètre retenu, discuté le 01/08** : V1 volontairement limitée à la
**consultation** hors-ligne (ce qui a déjà été chargé pendant qu'il y avait
du réseau reste consultable sans réseau), pour élève et enseignant à
parts égales. Pas de synchronisation d'actions hors-ligne (répondre à un
exercice sans réseau, etc.) — chantier plus complexe, délibérément reporté.
Tout ce qui touche l'IA ou plusieurs personnes reste par nature impossible
sans réseau (génération, validation).

**Construit et déployé** : service worker (`web/public/sw.js`, stratégie
réseau d'abord puis repli sur le cache pour toute requête `GET`, jamais
pour les écritures), manifeste PWA (`web/public/manifest.json` + icônes),
bandeau "Hors-ligne" affiché automatiquement (`ServiceWorkerRegistration.jsx`,
basé sur les événements `online`/`offline` du navigateur).

**⚠️ Limite technique importante, à ne pas oublier** : les service workers
exigent HTTPS (sauf en localhost) — tant que l'application tourne en HTTP
simple sur l'IP du VPS, **ce service worker ne s'activera jamais en
production**, même si le code est bien déployé. Il faut un nom de domaine +
certificat HTTPS devant l'application pour que le hors-ligne fonctionne
réellement. Confirmé fonctionnel en local (`localhost`) pendant cette
session — juste en attente d'HTTPS pour la production.

---

## 5. Confusion sur le libellé "Contenu du cours" — répondu, pas une tâche

Le champ "Contenu du cours" (formulaire de dépôt de cours, espace
Enseignant) sert à coller/saisir le contenu réel de la leçon enseignée —
c'est sur cette base que l'IA génère ensuite des ressources adaptées
(plutôt que sur le thème seul). Pas d'action nécessaire, sauf si le libellé
mérite d'être rendu plus explicite dans l'interface (ex : ajouter un texte
d'aide sous le champ).

---

## 6. Les identifiants d'un module "ouvrent" partiellement les autres modules — ✅ FAIT le 01/08

**Constat** : `/auth/login` est volontairement générique (ne vérifie que
email/mot de passe, jamais le rôle — chaque endpoint revérifie le rôle côté
serveur ensuite). Résultat côté UX : des identifiants Administration
"passent" l'écran de connexion du module Enseignant (token valide émis),
mais aucune donnée réelle n'est exposée (bloqué au niveau de chaque endpoint
spécifique). Pas de faille de sécurité de fond, mais une mauvaise
expérience : l'utilisateur se retrouve sur un écran vide/cassé au lieu d'un
message clair.

**Construit et déployé** : `ErreurApi` porte désormais le code HTTP de la
réponse (`e.status`) dans les 6 espaces. Si le tout premier appel
authentifié échoue en 401, le token n'est jamais posé (ou aussitôt retiré) —
l'utilisateur reste sur l'écran de connexion avec le message "Ce compte n'a
pas accès à cet espace", plutôt que de voir un tableau de bord vide ou
cassé. Selon l'architecture de chaque espace : vérification directe dans
`connecter()` (Enseignant, Administration, Direction, Plateforme) ou
interception dans le `catch` du premier chargement (Élève, Parent).

---

## 7. Brancher réellement la recherche RAG sur la génération de cours/exercices — ✅ FAIT le 01/08

**Découverte en cours de route** : la génération de "ressources de cours"
(fiches, résumés, QCM...) n'appelait **aucune IA** — texte gabarit codé en
dur, avec une note explicite dans le code disant "à remplacer par un vrai
appel LLM". Brancher le RAG a donc d'abord nécessité de construire ce vrai
appel manquant.

**Construit et déployé** :
- Nouveau module `generation_cours.py` — remplace le gabarit statique par
  un vrai appel Mistral pour les 6 types de ressources (fiche pédagogique,
  résumé, exercices, QCM, devoir, contrôle), enrichi par
  `rag.rechercher_passages_pertinents` (programme officiel + notes de
  l'enseignant + contenu déjà validé, filtré par niveau/matière/établissement)
  et par le contenu réellement enseigné (`contenu_texte` du cours déposé).
  Statut `en_attente` inchangé — relecture humaine toujours obligatoire.
- `enseignant/generation-libre` enrichi de la même façon (best-effort,
  filtré seulement par matière puisqu'aucun `niveau_id` n'existe pour un
  enseignant indépendant).
- Testé de bout en bout : confirmé que 6 vrais appels LLM ont désormais
  lieu au dépôt d'un cours (au lieu de zéro), et que le contexte RAG est
  bien injecté dans le prompt quand des documents pertinents existent.

**Reste à part, non traité** : le pipeline d'exercices hors-ligne
(`pipeline/generator_llm.py`, `generator_math.py`) — toujours un script
batch exécuté manuellement, jamais déclenché par l'API. Brancher le RAG
dessus serait un chantier séparé.

---

## 8. CI/CD — déploiement automatique à chaque push

**Plan clarifié le 01/08, pas encore construit** : GitHub Actions, avec un
geste de validation manuelle avant tout déploiement en production (décision
volontaire — pas d'auto-déploiement complet sans validation, projet avec
de vrais utilisateurs).

**Flux retenu** :
1. Automatique à chaque push sur `main` : vérifier que le frontend build
   sans erreur, et que le code de l'API s'importe proprement (sans base de
   données réelle pour cette V1 — un test complet avec la base demanderait
   une configuration plus lourde, à envisager plus tard si besoin).
2. Si ça casse → tout s'arrête, rien ne touche le serveur.
3. Si ça passe → un bouton "Déployer" apparaît sur GitHub (environnement
   `production` avec validateur requis), à cliquer manuellement.
4. Une fois cliqué → automatique : connexion SSH au serveur, récupération
   du code, migration si besoin, rebuild, redémarrage des services.

**Configuration initiale nécessaire avant de pouvoir construire ça**
(remise à plus tard, décision du 01/08) :
- Générer une clé SSH dédiée (pas la clé personnelle) pour que GitHub
  Actions puisse se connecter au serveur.
- L'ajouter comme secret dans les paramètres du dépôt GitHub.
- Créer un environnement GitHub nommé `production`, avec validateur requis
  — c'est ce qui crée le bouton de validation manuelle.

---

## 11. Système de crédits enseignant — ✅ FAIT le 01/08

**Discuté et cadré le 01/08**, en réponse à une demande de modèle
économique : transformer la relecture humaine des ressources IA (déjà
indispensable pour la qualité de la plateforme) en mécanisme d'engagement.

**Modèle retenu** :
- Gagner : valider une ressource sans la modifier (+1 crédit), ou après
  correction (+2 crédits) — dès le premier jour du compte, pour habituer
  l'enseignant. La distinction simple/corrigée décourage le clic
  automatique sans vraie relecture.
- Dépenser : uniquement "Déposer un cours" (−2 crédits), et uniquement à
  partir du 4e mois suivant la création du compte — avant ça, gratuit et
  illimité, mais les crédits s'accumulent déjà en arrière-plan.
- Génération libre : toujours gratuite, à vie, sans aucune condition.
- Aucun suivi ni visibilité côté établissement — jauge strictement
  personnelle à l'enseignant.

**Préalable nécessaire, traité avant les crédits** : ajout des classes
personnelles pour l'enseignant indépendant (voir point 1, mis à jour) —
sans ça, un enseignant indépendant n'aurait rien de réel à valider pour
gagner des crédits.

**Construit et déployé** : table `credits_enseignant` (registre/ledger,
traçable), module `credits.py`, vérification + débit avant tout dépôt de
cours (donc avant l'appel IA — pas de génération gaspillée si crédits
insuffisants), gain automatique à la validation dans `cours.py`, endpoint
`GET /enseignant/credits` et écran "Mes crédits" (solde + historique).

---

## 12. Vrai système d'abonnement établissement (pas encore fonctionnel)

**Contexte, précisé le 01/08** : le modèle économique complet a trois
niveaux — établissement (abonnement classique, donne accès à ses
enseignants/parents/élèves), enseignant (crédits, point 11, fait),
et élève (upgrade payant par le parent, point 13, à faire). Ce point
couvre le premier niveau.

**Constat** : `etablissements.niveau_abonnement` existe déjà en base
(renseigné à la création d'un établissement via l'Admin Plateforme), mais
c'est **une simple étiquette aujourd'hui** — rien dans le code ne
vérifie sa valeur ni n'applique de restriction en fonction d'elle. Un
établissement en formule "starter" a exactement les mêmes droits qu'un
établissement en formule supérieure.

**À définir avant de coder** : quelles formules existent réellement (ex :
starter/standard/premium ?), ce que chacune inclut ou limite concrètement
(nombre d'élèves ? nombre d'enseignants ? accès à certains modules comme
Documents ou Bibliothèque commune ?), et comment un établissement change
de formule (upgrade/downgrade — qui déclenche ça, l'Admin Plateforme ?).

---

## 14. Segmentation du corpus documentaire par pays — ✅ FAIT le 02/08

**Découvert en préparant le dépôt des programmes officiels de Côte
d'Ivoire, Sénégal, RDC, Bénin, Togo et Gabon** : `documents_pedagogiques`
n'avait aucun champ `pays`, contrairement à `exercices` qui en avait déjà
un. Concrètement, sans correction, un programme officiel camerounais
aurait pu influencer une génération demandée au Sénégal, et inversement —
aucune segmentation n'existait, seuls le niveau et la matière filtraient
la recherche RAG.

**Construit et déployé** :
- `documents_pedagogiques.pays` (obligatoire) et `utilisateurs.pays`
  (optionnel, pour les enseignants indépendants uniquement — les autres
  l'obtiennent via leur établissement).
- `rag.rechercher_passages_pertinents` et `reinjecter_contenu_valide`
  filtrent/enregistrent désormais le pays.
- Le pays est résolu automatiquement pour chaque enseignant à la connexion
  (établissement en priorité, sinon le sien propre) et transmis
  correctement à chaque point de génération (Déposer un cours — y compris
  le cas multi-établissement où la classe peut appartenir à un pays
  différent de l'établissement principal —, Génération libre).
- Un admin d'établissement ne voit plus, dans son onglet Documents, que
  les programmes officiels de son propre pays.
- Formulaires mis à jour : inscription enseignant indépendant (sélecteur
  de pays), dépôt de programme officiel côté Admin Plateforme (pays
  obligatoire, affiché dans la liste).

---

## 13. Upgrade du compte élève par le parent (n'existe pas encore)

**Besoin exprimé le 01/08** : un parent doit pouvoir payer pour débloquer
plus de services sur le compte de son enfant, au-delà de ce que la formule
classique de l'établissement offre par défaut.

**État actuel** : n'existe pas du tout — ni dans le schéma, ni dans le
code, ni dans les discussions précédentes. Tout un chantier à cadrer :
quels services précis un élève "de base" a aujourd'hui (exercices,
planning, résultats — voir `/eleve/...`) versus ce qu'un upgrade
débloquerait concrètement (génération d'exercices supplémentaires ? accès
à du contenu plus avancé ? autre chose ?). Question de paiement à trancher
aussi : paiement ponctuel, abonnement récurrent, et par quel moyen (le
module `paiements` existe déjà côté établissement, à voir s'il est
réutilisable ou s'il faut un circuit séparé pour les parents).

---

## 9. Déposer les vrais programmes officiels MINESEC

Une fois récupérés par l'utilisateur (le site du MINESEC bloque l'accès
automatisé), à déposer via le module Admin Plateforme
(`POST /plateforme/documents`). Pas un chantier technique — juste une
tâche opérationnelle en attente du matériel source.

---

## 10. Nom de domaine + HTTPS — nouveau, identifié comme prérequis du point 4

**Découvert le 01/08** en construisant le hors-ligne : les service workers
(la brique technique du hors-ligne) exigent HTTPS pour s'activer, sauf en
localhost. Tant que l'application tourne en HTTP simple sur l'IP du VPS
(`http://89.116.111.3`), le hors-ligne construit au point 4 restera
inactif en production, même si le code est bien déployé.

**À faire** : acheter/configurer un nom de domaine, mettre en place un
certificat HTTPS (ex : Let's Encrypt via Certbot) devant l'application —
probablement avec un reverse proxy (nginx) devant l'API et le frontend,
puisqu'ils tournent actuellement sur des ports distincts en HTTP direct.

---

## Fait pendant la session du 31/07 (pour référence)

- Corpus documentaire RAG réorganisé (portée plateforme / privé / réinjection).
- Incident de production résolu (droits PostgreSQL pour `eduai_app`).
- Module Admin Plateforme complet construit et déployé (établissements,
  documents partagés, bibliothèque commune d'exercices).
