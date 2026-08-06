"""Génération des ressources de cours (fiche pédagogique, résumé, QCM,
devoir, contrôle, exercices) — remplace l'ancien gabarit statique par un
vrai appel Mistral, enrichi par le corpus documentaire (programme officiel,
notes de cours de l'enseignant, contenu déjà validé sur la plateforme) via
rag.rechercher_passages_pertinents.

Chaque type de ressource a sa propre structure JSON (voir SCHEMAS_PAR_TYPE),
pour un affichage dédié côté interface plutôt qu'un simple bloc de texte —
mais si l'IA ne respecte pas le schéma attendu (ça arrive), on retombe sur
un texte aplati plutôt que de stocker une structure que le frontend ne
saurait pas afficher (incident du 02/08 : React plantait sur un objet
imbriqué inattendu).

Toujours produit avec statut='en_attente' côté appelant (cours.py) — un
contenu généré par IA n'est jamais publié sans relecture humaine, même
enrichi par de vrais documents de référence.
"""
import os
import json
import re

from mistralai.client import Mistral

from . import rag
from .db import get_cursor
from .text_utils import aplatir_en_texte

MODELE = "mistral-small-latest"

INSTRUCTIONS_PAR_TYPE = {
    "fiche_pedagogique": "une fiche pédagogique : objectifs d'apprentissage, compétences visées, "
                          "déroulé pédagogique suggéré (introduction, développement, synthèse).",
    "resume": "un résumé clair en une page : définitions clés, règle(s) principale(s), un exemple travaillé.",
    "exercices": "10 exercices d'application, du plus facile au plus difficile, avec corrigés détaillés.",
    "qcm": "un questionnaire à choix multiples de 8 questions, avec les bonnes réponses indiquées.",
    "devoir": "un devoir maison : 5 exercices d'application + 1 problème contextualisé, avec corrigés.",
    "controle": "un contrôle en classe d'une heure : 3 exercices d'application + 1 exercice de synthèse, avec corrigés.",
}

# Exemple de JSON attendu par type, montré tel quel à l'IA dans le prompt —
# plus fiable qu'une description en prose pour obtenir une structure stable.
SCHEMAS_PAR_TYPE = {
    "fiche_pedagogique": {
        "objectifs": ["Objectif 1", "Objectif 2"],
        "competences_visees": ["Compétence 1", "Compétence 2"],
        "deroulement": [
            {"etape": "Introduction", "duree": "10 min", "description": "..."},
            {"etape": "Développement", "duree": "30 min", "description": "..."},
            {"etape": "Synthèse", "duree": "10 min", "description": "..."},
        ],
    },
    "resume": {
        "definitions_cles": [{"terme": "...", "definition": "..."}],
        "regles_principales": ["Règle 1", "Règle 2"],
        "exemple_travaille": {"enonce": "...", "resolution": "..."},
    },
    "exercices": {
        "exercices": [{"numero": 1, "difficulte": "facile", "enonce": "...", "corrige": "..."}],
    },
    "qcm": {
        "questions": [{"numero": 1, "question": "...", "choix": ["...", "...", "...", "..."],
                        "bonne_reponse": 0, "explication": "..."}],
    },
    "devoir": {
        "exercices": [{"numero": 1, "enonce": "...", "corrige": "..."}],
        "probleme": {"enonce": "...", "corrige": "..."},
    },
    "controle": {
        "duree": "1 heure",
        "exercices": [{"numero": 1, "points": 5, "enonce": "...", "corrige": "..."}],
        "exercice_synthese": {"points": 5, "enonce": "...", "corrige": "..."},
    },
}

# Clés minimales à retrouver pour considérer que l'IA a bien respecté le
# schéma — conservé pour référence/documentation, la validation réelle est
# désormais dans _structure_valide (plus stricte : vérifie aussi la FORME
# des valeurs, pas juste leur présence — voir incident du 03/08 où
# "exercices" existait mais n'était pas une vraie liste d'objets).
CLES_REQUISES_PAR_TYPE = {
    "fiche_pedagogique": ["objectifs", "deroulement"],
    "resume": ["definitions_cles", "regles_principales"],
    "exercices": ["exercices"],
    "qcm": ["questions"],
    "devoir": ["exercices", "probleme"],
    "controle": ["exercices", "exercice_synthese"],
}


def _est_liste_non_vide_de_dicts(valeur) -> bool:
    return isinstance(valeur, list) and len(valeur) > 0 and all(isinstance(item, dict) for item in valeur)


def _structure_valide(type_ressource: str, donnees) -> bool:
    """Vérifie la FORME réelle attendue, pas seulement la présence des
    clés — une IA peut renvoyer "exercices": {...} (un objet) au lieu de
    "exercices": [...] (une liste), ce qui passerait un simple contrôle de
    présence mais casserait l'affichage dédié (incident du 03/08)."""
    if not isinstance(donnees, dict):
        return False
    if type_ressource == "fiche_pedagogique":
        return (isinstance(donnees.get("objectifs"), list) and len(donnees["objectifs"]) > 0
                and _est_liste_non_vide_de_dicts(donnees.get("deroulement")))
    if type_ressource == "resume":
        return (_est_liste_non_vide_de_dicts(donnees.get("definitions_cles"))
                and isinstance(donnees.get("regles_principales"), list) and len(donnees["regles_principales"]) > 0)
    if type_ressource == "exercices":
        return _est_liste_non_vide_de_dicts(donnees.get("exercices"))
    if type_ressource == "qcm":
        return _est_liste_non_vide_de_dicts(donnees.get("questions"))
    if type_ressource == "devoir":
        return bool(_est_liste_non_vide_de_dicts(donnees.get("exercices")) and isinstance(donnees.get("probleme"), dict) and donnees["probleme"])
    if type_ressource == "controle":
        return bool(_est_liste_non_vide_de_dicts(donnees.get("exercices"))
                and isinstance(donnees.get("exercice_synthese"), dict) and donnees["exercice_synthese"])
    return False



def _rechercher_contexte(matiere_nom: str, niveau_nom: str, titre_cours: str, contenu_texte: str | None,
                          niveau_id: str | None, matiere_id: str | None,
                          etablissement_id: str | None, enseignant_id: str, pays: str | None) -> list[str]:
    """Best-effort : une panne d'indexation ou d'embedding ne doit jamais
    empêcher la génération elle-même — juste la priver de contexte enrichi.

    Réflexion du 04/08 : la requête se limitait avant à "matière niveau
    titre" — quelques mots, souvent trop pauvres pour bien cibler le
    corpus. Le contenu réellement enseigné (rédigé par l'enseignant dans
    "Contenu du cours") est un bien meilleur signal — on l'inclut
    désormais dans la requête elle-même, pas seulement dans le prompt final."""
    try:
        client = rag.obtenir_client_mistral()
        if client is None:
            return []
        texte_requete = f"{matiere_nom} {niveau_nom} {titre_cours}"
        if contenu_texte:
            texte_requete += " " + contenu_texte[:800]  # tronqué : signal suffisant, évite une requête trop longue
        embedding = rag.generer_embeddings(client, [texte_requete])[0]
        with get_cursor() as cur:
            return rag.rechercher_passages_pertinents(
                cur, embedding, niveau_id=niveau_id, matiere_id=matiere_id,
                etablissement_id=etablissement_id, utilisateur_id_demandeur=enseignant_id, pays=pays, k=4,
            )
    except Exception:
        return []


LABELS_DIFFICULTE = {
    "facile": "plutôt facile, accessible, avec des étapes bien guidées",
    "moyen": "de difficulté moyenne, standard pour ce niveau",
    "difficile": "exigeant, pour des élèves à l'aise avec la matière",
}


def _conformer_au_gabarit(valeur, gabarit):
    """Force `valeur` à respecter la FORME du gabarit (l'exemple de schéma
    envoyé dans le prompt), en aplatissant en texte toute divergence — quel
    que soit l'endroit précis où elle survient. `_structure_valide` ne
    vérifie que la structure de surface (les bonnes clés présentes, pas
    vides) ; ça ne suffit pas si l'IA respecte les clés de premier niveau
    mais renvoie un objet imbriqué là où une simple chaîne était attendue
    en profondeur (incident du 06/08 : {"phrase_1": ..., "phrase_5": ...}
    au lieu d'une phrase, dans un champ texte quelconque)."""
    if isinstance(gabarit, str):
        return valeur if isinstance(valeur, str) else aplatir_en_texte(valeur)
    if isinstance(gabarit, (int, float, bool)) or gabarit is None:
        return valeur
    if isinstance(gabarit, list):
        if not isinstance(valeur, list):
            return [aplatir_en_texte(valeur)] if valeur else []
        modele_item = gabarit[0] if gabarit else None
        return [_conformer_au_gabarit(item, modele_item) if modele_item is not None else item for item in valeur]
    if isinstance(gabarit, dict):
        if not isinstance(valeur, dict):
            return {}
        return {cle: _conformer_au_gabarit(valeur[cle], sous_gabarit)
                for cle, sous_gabarit in gabarit.items() if cle in valeur}
    return valeur


def generer_ressource(type_ressource: str, titre_cours: str, contenu_texte: str | None,
                       matiere_nom: str, niveau_nom: str,
                       niveau_id: str | None, matiere_id: str | None,
                       etablissement_id: str | None, enseignant_id: str, pays: str | None = None,
                       difficulte: str = "moyen") -> dict:
    passages = _rechercher_contexte(matiere_nom, niveau_nom, titre_cours, contenu_texte,
                                      niveau_id, matiere_id, etablissement_id, enseignant_id, pays)

    schema_exemple = json.dumps(SCHEMAS_PAR_TYPE[type_ressource], ensure_ascii=False, indent=2)
    pays_texte = pays or "le pays de l'enseignant"
    system_prompt = (
        f"Tu es un expert en pédagogie pour {pays_texte}, qui aide un enseignant à préparer sa classe. "
        "Rédige TOUJOURS en français — y compris pour les cours de langue étrangère (anglais, allemand, "
        "espagnol...), où seuls les mots ou phrases dans la langue étudiée doivent apparaître dans cette "
        "langue, jamais les consignes ni les explications. "
        "Réponds UNIQUEMENT avec un objet JSON valide, sans texte avant ou après, sans balises markdown. "
        f"Respecte EXACTEMENT cette structure (mêmes clés, mêmes types — remplace juste le contenu "
        f"d'exemple par du vrai contenu pédagogique) :\n{schema_exemple}"
    )

    prompt = (
        f"Prépare {INSTRUCTIONS_PAR_TYPE[type_ressource]}\n\n"
        f"Matière : {matiere_nom}. Niveau : {niveau_nom}. Titre du cours : « {titre_cours} ».\n"
        f"Niveau de difficulté souhaité : {LABELS_DIFFICULTE.get(difficulte, LABELS_DIFFICULTE['moyen'])}.\n"
    )
    if contenu_texte:
        prompt += f"\nContenu réellement enseigné en classe (à utiliser en priorité) :\n{contenu_texte}\n"
    if passages:
        prompt += (
            "\nExtraits de référence disponibles (programme officiel et/ou notes de cours) — "
            "à utiliser s'ils sont pertinents, sans t'y limiter :\n" + "\n---\n".join(passages) + "\n"
        )

    api_key = os.environ.get("MISTRAL_API_KEY")
    if not api_key:
        # Dégradation gracieuse plutôt qu'un 500 : mieux vaut un contenu
        # minimal que bloquer tout le dépôt de cours si la clé manque.
        return {"texte": f"[Génération indisponible — MISTRAL_API_KEY absente] {titre_cours}"}

    client = Mistral(api_key=api_key)
    try:
        reponse = client.chat.complete(
            model=MODELE,
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.6,
        )
        brut = reponse.choices[0].message.content
        donnees = json.loads(re.sub(r"^```json\s*|\s*```$", "", brut.strip()))

        if _structure_valide(type_ressource, donnees):
            return _conformer_au_gabarit(donnees, SCHEMAS_PAR_TYPE[type_ressource])

        # L'IA n'a pas respecté le schéma attendu (ça arrive, même avec un
        # exemple explicite) — on aplatit tout ce qu'elle a renvoyé plutôt
        # que de stocker une structure que le frontend ne saurait pas
        # afficher, ou de perdre le contenu généré.
        return {"texte": aplatir_en_texte(donnees)}
    except Exception as e:
        from . import erreurs
        erreurs.enregistrer_erreur("generation_ia", str(e), {
            "endpoint": "deposer_cours", "type_ressource": type_ressource,
            "titre_cours": titre_cours, "enseignant_id": enseignant_id,
        })
        return {"texte": f"[Erreur de génération : {e}] {titre_cours}"}
