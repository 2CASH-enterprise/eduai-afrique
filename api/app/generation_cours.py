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
# schéma — sert de filet de validation avant d'accepter la structure.
CLES_REQUISES_PAR_TYPE = {
    "fiche_pedagogique": ["objectifs", "deroulement"],
    "resume": ["definitions_cles", "regles_principales"],
    "exercices": ["exercices"],
    "qcm": ["questions"],
    "devoir": ["exercices", "probleme"],
    "controle": ["exercices", "exercice_synthese"],
}


def _aplatir_en_texte(valeur, niveau: int = 0) -> str:
    """Convertit n'importe quelle valeur JSON en texte lisible — utilisé
    uniquement en repli, quand la structure attendue n'est pas respectée."""
    prefixe = "  " * niveau
    if isinstance(valeur, str):
        return valeur
    if isinstance(valeur, (int, float, bool)) or valeur is None:
        return str(valeur)
    if isinstance(valeur, list):
        return "\n".join(f"{prefixe}- {_aplatir_en_texte(v, niveau + 1)}" for v in valeur)
    if isinstance(valeur, dict):
        lignes = []
        for cle, sous_valeur in valeur.items():
            libelle = str(cle).replace("_", " ").capitalize()
            sous_texte = _aplatir_en_texte(sous_valeur, niveau + 1)
            if "\n" in sous_texte:
                lignes.append(f"{prefixe}{libelle} :\n{sous_texte}")
            else:
                lignes.append(f"{prefixe}{libelle} : {sous_texte}")
        return "\n".join(lignes)
    return str(valeur)


def _structure_valide(type_ressource: str, donnees: dict) -> bool:
    if not isinstance(donnees, dict):
        return False
    return all(cle in donnees and donnees[cle] not in (None, [], {}) for cle in CLES_REQUISES_PAR_TYPE[type_ressource])


def _rechercher_contexte(matiere_nom: str, niveau_nom: str, titre_cours: str,
                          niveau_id: str | None, matiere_id: str | None,
                          etablissement_id: str | None, enseignant_id: str, pays: str | None) -> list[str]:
    """Best-effort : une panne d'indexation ou d'embedding ne doit jamais
    empêcher la génération elle-même — juste la priver de contexte enrichi."""
    try:
        client = rag.obtenir_client_mistral()
        if client is None:
            return []
        embedding = rag.generer_embeddings(client, [f"{matiere_nom} {niveau_nom} {titre_cours}"])[0]
        with get_cursor() as cur:
            return rag.rechercher_passages_pertinents(
                cur, embedding, niveau_id=niveau_id, matiere_id=matiere_id,
                etablissement_id=etablissement_id, utilisateur_id_demandeur=enseignant_id, pays=pays, k=4,
            )
    except Exception:
        return []


def generer_ressource(type_ressource: str, titre_cours: str, contenu_texte: str | None,
                       matiere_nom: str, niveau_nom: str,
                       niveau_id: str | None, matiere_id: str | None,
                       etablissement_id: str | None, enseignant_id: str, pays: str | None = None) -> dict:
    passages = _rechercher_contexte(matiere_nom, niveau_nom, titre_cours,
                                      niveau_id, matiere_id, etablissement_id, enseignant_id, pays)

    schema_exemple = json.dumps(SCHEMAS_PAR_TYPE[type_ressource], ensure_ascii=False, indent=2)
    system_prompt = (
        "Tu es un expert en pédagogie pour le Cameroun, qui aide un enseignant à préparer sa classe. "
        "Réponds UNIQUEMENT avec un objet JSON valide, sans texte avant ou après, sans balises markdown. "
        f"Respecte EXACTEMENT cette structure (mêmes clés, mêmes types — remplace juste le contenu "
        f"d'exemple par du vrai contenu pédagogique) :\n{schema_exemple}"
    )

    prompt = (
        f"Prépare {INSTRUCTIONS_PAR_TYPE[type_ressource]}\n\n"
        f"Matière : {matiere_nom}. Niveau : {niveau_nom}. Titre du cours : « {titre_cours} ».\n"
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
            return donnees

        # L'IA n'a pas respecté le schéma attendu (ça arrive, même avec un
        # exemple explicite) — on aplatit tout ce qu'elle a renvoyé plutôt
        # que de stocker une structure que le frontend ne saurait pas
        # afficher, ou de perdre le contenu généré.
        return {"texte": _aplatir_en_texte(donnees)}
    except Exception as e:
        return {"texte": f"[Erreur de génération : {e}] {titre_cours}"}
