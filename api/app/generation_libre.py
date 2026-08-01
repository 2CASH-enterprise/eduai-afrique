"""Génération d'exercice à la demande, pour le mode libre (enseignant sans
classe réelle — indépendant ou simple pratique personnelle).

Adapté de pipeline/generator_llm.py plutôt qu'importé directement : le
pipeline est un outil de génération par lot exécuté hors-ligne (pas par le
process API en production), alors que ce module est appelé en direct,
en synchrone, à chaque requête. Les deux partagent la même logique de
prompt mais vivent dans des contextes d'exécution différents.
"""
import os
import json
import re

from fastapi import HTTPException, status
from mistralai.client import Mistral

MODELE = "mistral-small-latest"

SYSTEM_PROMPT = """Tu es un expert en pédagogie pour le Cameroun. Tu génères des \
exercices scolaires conformes aux programmes officiels camerounais. \
Réponds UNIQUEMENT avec un objet JSON valide, sans texte avant ou après, \
sans balises markdown. Le JSON doit avoir exactement ces clés : \
sous_theme, enonce, corrige, etapes (liste), contexte, tags (liste de 2-4 mots-clés)."""


def _construire_prompt(matiere: str, niveau: str, theme: str) -> str:
    return f"""Génère UN exercice de {matiere} pour la classe de {niveau}, \
sur le thème "{theme}".

Contraintes :
1. Conforme au programme officiel camerounais.
2. Énoncé clair, corrigé détaillé avec étapes de raisonnement.
3. Utilise si possible un contexte local (agriculture, marché, vie \
quotidienne au Cameroun) — sans le forcer si le thème ne s'y prête pas."""


def generer_exercice_a_la_demande(matiere: str, niveau: str, theme: str) -> dict:
    """Appelle Mistral directement et retourne le JSON parsé. Lève une
    HTTPException explicite en cas d'échec — contrairement au pipeline par
    lot, ici il y a un utilisateur en attente d'une réponse immédiate, donc
    pas de sens à avaler l'erreur silencieusement."""
    api_key = os.environ.get("MISTRAL_API_KEY")
    if not api_key:
        raise HTTPException(status_code=503, detail="MISTRAL_API_KEY absente sur le serveur")

    client = Mistral(api_key=api_key)
    try:
        reponse = client.chat.complete(
            model=MODELE,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": _construire_prompt(matiere, niveau, theme)},
            ],
            response_format={"type": "json_object"},
            temperature=0.7,
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Erreur lors de l'appel à l'IA : {e}")

    brut = reponse.choices[0].message.content
    try:
        donnees = json.loads(re.sub(r"^```json\s*|\s*```$", "", brut.strip()))
    except json.JSONDecodeError:
        raise HTTPException(status_code=502, detail="Réponse de l'IA illisible — réessayez")

    return donnees
