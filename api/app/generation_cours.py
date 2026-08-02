"""Génération des ressources de cours (fiche pédagogique, résumé, QCM,
devoir, contrôle, exercices) — remplace l'ancien gabarit statique par un
vrai appel Mistral, enrichi par le corpus documentaire (programme officiel,
notes de cours de l'enseignant, contenu déjà validé sur la plateforme) via
rag.rechercher_passages_pertinents.

Toujours produit avec statut='en_attente' côté appelant (cours.py) — un
contenu généré par IA n'est jamais publié sans relecture humaine, même
enrichi par de vrais documents de référence (voir generator_llm.py pour la
même philosophie côté exercices).
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

SYSTEM_PROMPT = """Tu es un expert en pédagogie pour le Cameroun, qui aide un enseignant à préparer sa classe. \
Réponds UNIQUEMENT avec un objet JSON valide, sans texte avant ou après, sans balises markdown. \
Le JSON doit avoir exactement une clé : "texte" (le contenu demandé, en texte structuré, prêt à être relu \
puis utilisé par l'enseignant)."""


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
            messages=[{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.6,
        )
        brut = reponse.choices[0].message.content
        donnees = json.loads(re.sub(r"^```json\s*|\s*```$", "", brut.strip()))
        return {"texte": donnees.get("texte", "")}
    except Exception as e:
        return {"texte": f"[Erreur de génération : {e}] {titre_cours}"}
