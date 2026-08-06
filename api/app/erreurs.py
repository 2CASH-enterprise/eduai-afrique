"""Journalisation des erreurs système (TODO.md, monitoring — cadré le
06/08 suite à l'incident React #31). Pas un router — importé par les
points de génération IA (generation_cours.py, generation_libre.py) et par
l'endpoint public de remontée des plantages navigateur.

Toujours best-effort : journaliser une erreur ne doit jamais en provoquer
une nouvelle qui ferait planter l'appelant à sa place.
"""
import json

from .db import get_cursor


def enregistrer_erreur(type_erreur: str, message: str, contexte: dict | None = None) -> None:
    try:
        with get_cursor(commit=True) as cur:
            cur.execute(
                "INSERT INTO erreurs_systeme (type_erreur, message, contexte) VALUES (%s, %s, %s)",
                (type_erreur, str(message)[:2000], json.dumps(contexte) if contexte else None),
            )
    except Exception:
        pass
