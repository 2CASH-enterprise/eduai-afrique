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

## 24. Menu hamburger sur les autres espaces — reporté le 05/08

**Fait le 05/08** : navigation responsive (horizontal → hamburger déroulant
sur mobile/tablette) sur l'espace **Enseignant** uniquement — c'est celui
avec le plus d'éléments dans la barre (9), donc le plus urgent.

**Reste à faire, même traitement** : Admin Plateforme, Direction,
Administration (et Élève/Parent le jour où ils seront activés). Pas
urgent — reporté consciemment, à reprendre plus tard.

---

## 23. Modules actifs sur le portail public — ✅ FAIT le 05/08

**Discuté et cadré le 05/08**, en préparation du lancement en test ouvert
du seul module Enseignant : les cartes des modules pas encore ouverts
(Élève, Direction, Parent, Administration) ne devaient plus apparaître sur
la page d'accueil publique.

**Deux décisions distinctes, pas une seule** :
- **Cartes "en attente d'activation"** (Élève, Direction, Parent,
  Administration) → **Option A retenue** : complètement invisibles, pas
  grisées avec "Bientôt disponible" — plus propre, aucune ambiguïté.
  Géré par un vrai interrupteur, activable un jour sans redéploiement.
- **Admin Plateforme** → traitement différent, volontairement pas dans le
  même système : ce n'est pas un module "pas encore prêt", c'est un outil
  interne à l'équipe, **retiré définitivement** du portail public — plus
  jamais une carte, accessible uniquement par lien direct (`/plateforme`).
  Précision importante : ça ne change rien à la sécurité en soi (l'écran
  de connexion reste protégé par les vrais identifiants) — c'est une
  question de discrétion, pas une mesure de sécurité.

**Construit et déployé** : table `modules_actifs` (migration 015, seul
Enseignant actif au lancement), endpoint public `GET /modules-actifs`
(sans authentification — nécessaire puisque la page d'accueil doit savoir
quoi afficher **avant** toute connexion, ne révèle rien de sensible),
`PATCH /plateforme/modules/{module}` protégé (Admin Plateforme
uniquement), écran "Modules" dédié (bascule actif/bloqué, même principe
que l'écran "Pays"). Page d'accueil (`web/app/page.jsx`) convertie en
composant serveur qui récupère l'état des modules à chaque requête
(revalidation automatique toutes les 60 secondes), avec repli sûr
(Enseignant seul) si l'API est injoignable — jamais une page blanche.

---

## 22. Renforcement du RAG — discuté le 04/08, deux points faits, trois reportés

**Réflexion menée le 04/08** sur cinq leviers pour rendre le RAG plus
puissant. Deux corrigés immédiatement (coût faible, impact réel), trois
reportés consciemment :

1. **Requête de recherche enrichie** — ✅ FAIT. La recherche ne se basait
   que sur "matière + niveau + titre du cours" ; elle utilise désormais
   aussi le contenu réel rédigé par l'enseignant (tronqué à 800
   caractères), un signal bien plus riche pour cibler le bon passage du
   corpus. Concerne `generation_cours.py` ("Déposer un cours" uniquement —
   Génération libre n'a pas d'équivalent "contenu réel", son thème reste
   son meilleur signal disponible).
2. **Seuil de pertinence minimum** — ✅ FAIT. `SEUIL_SIMILARITE_MINIMUM =
   0.3` dans `rag.py` — avant, la recherche renvoyait toujours ses k
   meilleurs résultats même quand rien n'était vraiment pertinent,
   injectant parfois du bruit dans le prompt. Valeur de départ
   raisonnable, à ajuster une fois de vraies données d'usage disponibles.
3. **Découpage naïf des documents** — ✅ FAIT le 05/08. Découpage par
   paragraphes plutôt que par blocs de mots fixes (voir `rag.py`,
   `decouper_en_passages`) — ne coupe plus un chapitre ou une idée en
   plein milieu. **Reste à faire** : réindexer les 88 documents déjà
   déposés (74 Côte d'Ivoire, 14 Sénégal) avec ce nouveau découpage — pas
   urgent techniquement (l'import en masse permet de relancer facilement
   les mêmes lots), mais à faire pour qu'ils bénéficient de l'amélioration.
4. **Pondération des sources** (programme officiel vs contenu
   généré-validé) — reporté, risque de dérive lente jugé faible tant que
   le corpus reste petit et surveillé de près.
5. **Mesure de la qualité du RAG** — reporté. Aucun moyen aujourd'hui de
   savoir objectivement si le RAG aide réellement les générations.
   Construire un système de mesure sans données réelles d'usage serait
   prématuré — à revoir une fois de vrais enseignants actifs sur la
   plateforme.

---

## 21. Chat contextuel enseignant — envisagé puis abandonné le 04/08

**Idée discutée** : un champ de chat dans le module Enseignant, permettant
de dialoguer avec l'IA ancrée dans le contexte précis (programme, pays,
chapitre/exercice enseigné), en s'appuyant sur le RAG déjà en place. Trois
points restaient à trancher (chat général vs contextuel à un cours,
sauvegarde ou non de l'historique, et surtout la question du coût — un
chat s'utilise bien plus intensément qu'une génération ponctuelle,
tension avec la gratuité volontaire de Génération libre).

**Décision : abandonné**, aucune suite prévue.

---

## 20. Stratégie économique clarifiée + geste "Suggérer EduAI à mon établissement"

**Discuté le 04/08**, éclaire enfin pourquoi le module Enseignant a été
construit avec une gratuité aussi généreuse (Génération libre toujours
gratuite, 3 mois totalement libres même pour "Déposer un cours") : ce
n'est pas qu'une décision produit isolée, c'est une **stratégie
d'acquisition délibérée**. Le modèle économique final : seuls les
**établissements** (abonnement, point 12) et les **parents** (upgrade du
compte élève, point 13) paient — les enseignants sont l'entonnoir gratuit
qui fait connaître la plateforme.

**Manque identifié** : aujourd'hui, rien ne permet à un enseignant
satisfait de faire remonter son intérêt pour que son établissement
rejoigne la plateforme — l'onboarding d'un établissement passe uniquement
par l'Admin Plateforme, pas par l'enseignant.

**Décision** : ne rien construire tout de suite. **Revenir sur ce point
une fois la barre des 300 enseignants inscrits atteinte** — un simple
geste "Suggérer EduAI à mon établissement" (pas un onboarding
self-service complet), qui envoie un signal côté équipe.

---

## 19. Manques identifiés sur le module Enseignant — discuté le 04/08

**Bilan fait le 04/08** avant le lancement en test ouvert. Sept points
identifiés, quatre retenus pour cette session — **tous les quatre faits et
déployés** :

1. **Export PDF/Word** — ✅ FAIT (PDF seulement, pas Word). Module
   `pdf_export.py` (reportlab/Platypus, mise en page automatique par
   section selon le type de ressource). Deux endpoints : une ressource
   seule (`GET /enseignant/cours/{id}/ressources/{id}/export-pdf`) ou tout
   le cours d'un coup (`GET /enseignant/cours/{id}/export-pdf`), plus un
   export pour un exercice de Génération libre. Bouton dédié sur chaque
   ressource et sur l'écran de détail du cours.
2. **Suivi des résultats élèves** — reporté, pas retenu cette session.
   La boucle génération → distribution → résultats n'est pas fermée :
   l'enseignant ne voit pas qui a fait quoi ni avec quel taux de réussite.
3. **Assigner un contenu à une classe avec échéance** — ✅ FAIT. Champ
   `cours.date_echeance`, réglable au dépôt ou modifiable après coup
   (`PATCH /enseignant/cours/{id}/echeance`), affiché avec code couleur
   selon la proximité (rouge si dépassée, ambre si ≤ 7 jours) sur "Mes
   cours".
4. **Dupliquer/adapter un cours existant** — ✅ FAIT.
   `POST /enseignant/cours/{id}/dupliquer` copie titre + contenu + les 6
   ressources vers une autre classe (ou la même), sans nouvel appel IA —
   donc **gratuit, aucun débit de crédits**. Chaque ressource copiée
   repart de `en_attente`, l'occasion d'adapter avant de revalider.
5. **Onboarding** — reporté, pas retenu cette session. Aucun tutoriel ni
   guide de prise en main pour un enseignant qui découvre seul la
   plateforme — pertinent vu le contexte de test ouvert sans accompagnement.
6. **Tableau de bord personnel** — reporté, pas retenu cette session.
   Rien ne montre à l'enseignant une synthèse de son activité (cours
   déposés, exercices validés...), pourrait se relier aux crédits.
7. **Niveau de difficulté ciblé à la génération** — ✅ FAIT. Champ
   `difficulte` ('facile'/'moyen'/'difficile') sur `cours` et
   `exercices_generation_libre`, transmis au prompt IA pour les deux
   points d'entrée (Déposer un cours, Génération libre), sélecteur dédié
   dans les deux formulaires.

**Deux bugs de régression trouvés et corrigés au passage** (ni prévus ni
demandés, découverts en travaillant sur ces points) :
- La réinjection du corpus documentaire (Type 3) ne fonctionnait plus
  pour les ressources structurées depuis l'introduction de la présentation
  dédiée par type (02-03/08) — `donnees.get("texte")` ne trouvait presque
  jamais rien. Corrigé en aplatissant systématiquement le contenu avant
  réinjection (`text_utils.aplatir_en_texte`), quelle que soit sa forme.
- Les en-têtes HTTP de téléchargement PDF plantaient sur les noms de
  fichiers accentués ("Résumé.pdf") — l'UTF-8 brut n'est pas valide dans
  un en-tête HTTP classique. Corrigé avec l'encodage RFC 5987
  (`filename*=UTF-8''...`), repli ASCII pour les navigateurs plus anciens.

---

## 18. Rwanda — recherche de programmes officiels, bloquée par la langue

**Recherche faite le 04/08** : l'organisme responsable est identifié (REB
— Rwanda Education Board, `reb.gov.rw`), et de vrais documents officiels
existent et sont accessibles :
- Mathematics Syllabus secondaire (S1-S3) : https://www.cur.ac.rw/mis/main/library/documents/book_file/digital-63f5d7ce431026.25518009.pdf
- Competence-Based Curriculum, vue d'ensemble : https://www.cur.ac.rw/mis/main/library/documents/book_file/digital-63f49bc5eeafa8.81233706.pdf
- Mathematics Syllabus primaire (P4-P6) : https://elearning.reb.rw/pluginfile.php/177314/mod_folder/content/0/P4-P6%20Mathematics%20Syllabus.pdf?forcedownload=1

**Blocage identifié, décision prise le 04/08** : depuis la réforme
linguistique de 2008-2010, le curriculum rwandais est **entièrement en
anglais**, malgré l'appartenance du pays à la Francophonie — incompatible
avec une plateforme entièrement française (interface, prompts IA,
génération). Décision : **le Rwanda reste bloqué** dans `pays_couverture`
jusqu'à ce qu'une vraie source en français soit trouvée (traduction
officielle, ou programme d'un cursus francophone local s'il en existe un).
Ne pas déposer les documents anglais tels quels.

---

## 17. Couverture par pays à l'inscription — ✅ FAIT le 04/08

**Discuté et cadré le 04/08**, en préparation du lancement en test ouvert
du module Enseignants pour la rentrée : un enseignant indépendant qui
tente de s'inscrire depuis un pays sans corpus documentaire suffisant
n'obtient plus de vrai compte — juste un message clair, et son email est
conservé pour recontact ultérieur.

**Modèle retenu** : statut explicite par pays, décidé par l'Admin
Plateforme (pas déduit automatiquement du nombre de documents déposés) —
un pays reste bloqué tant qu'il n'est pas jugé prêt, même s'il contient
déjà quelques documents. **Seule la Côte d'Ivoire est active au
lancement** (74 documents, large couverture) — le Sénégal (14 documents)
reste volontairement bloqué pour l'instant, comme tous les autres pays.

**Construit et déployé** : tables `pays_couverture` et
`liste_attente_inscriptions` (migration 012), `POST
/auth/inscription-enseignant` vérifie la couverture avant de créer un
compte (retourne 202 + message si le pays est bloqué, ajoute l'email en
liste d'attente sans doublon), endpoints Admin Plateforme `GET/PATCH
/plateforme/pays` et `GET /plateforme/liste-attente`, écran "Pays" dédié
(bascule actif/bloqué par pays + liste d'attente consultable), écran
d'inscription enseignant adapté pour afficher clairement le message de
liste d'attente au lieu de connecter automatiquement.

---

## 16. Historique des validations d'exercices rendu persistant — ✅ FAIT le 03/08

**Découvert en lisant une note laissée dans le code** ("Un vrai historique
persistant nécessiterait un endpoint dédié côté API") : l'onglet
"Historique" de l'espace Enseignant n'accumulait les décisions de
validation/rejet (bibliothèque commune) qu'en mémoire navigateur, le
temps de la session — tout redevenait vide après un rechargement de page
ou une reconnexion, alors que les exercices restaient bien à jour en base.

**Construit** : `GET /enseignant/exercices/mon-historique`, qui relit
`exercices` filtré par `valide_par_id` (réutilisé pour valider ET rejeter,
malgré son nom) et `statut IN ('valide','rejete')`, avec le motif de rejet
extrait du champ `liens`. Le frontend charge désormais cet historique
depuis l'API à l'ouverture de l'onglet, au lieu de se fier à l'état local.

---

## 15. Génération libre redéfinie en poste d'exercices persistants — ✅ FAIT le 03/08

**Discuté et cadré le 03/08** : l'ancienne Génération libre (un exercice à
la fois, jamais sauvegardé, jamais validable, sans effet sur le corpus)
ne correspondait plus au besoin réel — un enseignant qui enseigne
plusieurs classes (Terminale et 5ème par exemple) doit pouvoir produire de
vrais exercices réutilisables, pas juste explorer un thème ponctuellement.

**Nouveau fonctionnement** :
- L'enseignant choisit niveau (texte libre), matière, thème, et une
  **quantité au choix (1 à 5)**.
- Génère une **série** d'exercices corrigés d'un coup, chacun persisté
  avec un statut `en_attente`.
- Chaque exercice se **valide ou se rejette** individuellement — comme les
  ressources de "Déposer un cours".
- Une fois validé, l'exercice **reste dans le système** (historique
  consultable) et **réinjecte silencieusement le corpus documentaire**
  (Type 3), rattaché au bon pays.
- **Reste gratuite, sans condition** — contrairement à "Déposer un cours",
  jamais concernée par le système de crédits (décision explicite du 03/08).

**Construit et déployé** : nouvelle table `exercices_generation_libre`
(distincte de `exercices`, qui sert la bibliothèque commune et exige un
vrai `niveau_id` — même logique que `classes_personnelles` vs `classes`),
endpoints `POST` (génère la série), `GET` (historique), `PATCH` (valide/
rejette), écran refondu avec sélecteur de quantité, cartes "à relire" et
historique.

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

## 10. Nom de domaine + HTTPS — bloqué sur l'achat du domaine (05/08)

**Découvert le 01/08** en construisant le hors-ligne : les service workers
(la brique technique du hors-ligne) exigent HTTPS pour s'activer, sauf en
localhost. Tant que l'application tourne en HTTP simple sur l'IP du VPS
(`http://89.116.111.3`), le hors-ligne construit au point 4 restera
inactif en production, même si le code est bien déployé.

**Redevenu urgent le 05/08** : c'est aussi un vrai préalable à toute
migration du frontend vers Vercel — Vercel donne du HTTPS automatique au
frontend, mais un navigateur bloque purement et simplement un appel HTTPS
→ HTTP ("contenu mixte") : sans HTTPS sur l'API, migrer le frontend
casserait complètement les appels API.

**Statut au 05/08** : discuté, plan clair, mais **bloqué sur l'achat du
nom de domaine** (paiement pas encore possible côté utilisateur — à
reprendre "plus tard"). Rien à débloquer techniquement tant que ce
préalable n'est pas réglé — un certificat Let's Encrypt exige un vrai nom
de domaine, impossible d'en obtenir un pour une IP nue.

**Marche à suivre, prête pour quand le domaine sera acheté** :
1. Acheter un nom de domaine (n'importe quel registraire — Namecheap,
   OVH, Gandi... ~10-15 $/an pour un `.com`)
2. Pointer un enregistrement DNS de type **A** vers `89.116.111.3`
   (racine du domaine, ou sous-domaine type `app.`)
3. Prévoir une séparation en deux adresses : une pour le frontend (ex :
   `votredomaine.com`), une pour l'API (ex : `api.votredomaine.com`)
4. Une fois pointé : mettre en place nginx en façade + certificat Let's
   Encrypt (Certbot) pour les deux adresses
5. Mettre à jour le code pour utiliser les nouvelles adresses HTTPS au
   lieu de l'IP en dur (`http://89.116.111.3:8000` apparaît à plusieurs
   endroits dans le frontend — `API_BASE_URL` dans chaque fichier
   `espace-*.jsx`, et dans `web/app/page.jsx`), et ajuster CORS côté API
6. Alors seulement : migration éventuelle du frontend vers Vercel

---

## Fait pendant la session du 31/07 (pour référence)

- Corpus documentaire RAG réorganisé (portée plateforme / privé / réinjection).
- Incident de production résolu (droits PostgreSQL pour `eduai_app`).
- Module Admin Plateforme complet construit et déployé (établissements,
  documents partagés, bibliothèque commune d'exercices).
