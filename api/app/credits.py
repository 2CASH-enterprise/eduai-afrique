"""Système de crédits enseignant — cadré le 01/08 :

- Gagner : valider une ressource sans la modifier (+1), ou après correction
  (+2) — dès le premier jour du compte, pour habituer l'enseignant.
- Dépenser : uniquement "Déposer un cours" (−2), et uniquement à partir du
  4e mois suivant la création du compte. Avant ça, gratuit et illimité,
  mais les crédits s'accumulent déjà en arrière-plan.
- Génération libre : toujours gratuite, à vie, sans condition — jamais
  concernée par ce module.
- Pas de suivi ni de visibilité côté établissement — jauge strictement
  personnelle à l'enseignant.

Pas un router — importé par cours.py (gain à la validation, dépense au
dépôt de cours) et par un futur endpoint de consultation du solde.
"""
from datetime import timedelta

from fastapi import HTTPException, status

from .db import get_cursor

COUT_DEPOT_COURS = 2
DUREE_PERIODE_GRATUITE_JOURS = 90  # ~3 mois


def solde(cur, enseignant_id: str) -> int:
    cur.execute("SELECT COALESCE(SUM(delta), 0) FROM credits_enseignant WHERE enseignant_id = %s", (enseignant_id,))
    return cur.fetchone()[0]


def _ajouter(cur, enseignant_id: str, delta: int, motif: str, reference_id: str | None = None) -> None:
    cur.execute(
        "INSERT INTO credits_enseignant (enseignant_id, delta, motif, reference_id) VALUES (%s, %s, %s, %s)",
        (enseignant_id, delta, motif, reference_id),
    )


def en_periode_gratuite(cur, enseignant_id: str) -> bool:
    from datetime import datetime, timezone
    cur.execute("SELECT created_at FROM utilisateurs WHERE id = %s", (enseignant_id,))
    created_at = cur.fetchone()[0]
    if created_at is None:
        return True  # ne devrait jamais arriver (NOT NULL en base), prudence par défaut
    return (created_at + timedelta(days=DUREE_PERIODE_GRATUITE_JOURS)) > datetime.now(timezone.utc)


def recompenser_validation(cur, enseignant_id: str, ressource_id: str, statut_avant: str) -> None:
    """Appelée par cours.py juste avant qu'une ressource passe à 'valide'.
    +2 si elle avait été corrigée au préalable (statut 'corrige' — preuve
    d'une vraie relecture), +1 si validée telle quelle."""
    if statut_avant == "corrige":
        _ajouter(cur, enseignant_id, 2, "validation_corrigee", ressource_id)
    else:
        _ajouter(cur, enseignant_id, 1, "validation_simple", ressource_id)


def verifier_et_debiter_depot_cours(cur, enseignant_id: str) -> None:
    """Appelée par cours.py avant de créer un nouveau cours (donc avant
    d'appeler l'IA — pas de sens à débiter, ni même à générer, si
    l'enseignant n'a pas les crédits nécessaires). Ne fait rien pendant la
    période gratuite ; lève une erreur claire si le solde est insuffisant
    après celle-ci."""
    if en_periode_gratuite(cur, enseignant_id):
        return
    solde_actuel = solde(cur, enseignant_id)
    if solde_actuel < COUT_DEPOT_COURS:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=(
                f"Crédits insuffisants ({solde_actuel}/{COUT_DEPOT_COURS} requis) pour déposer un cours. "
                "Validez des ressources pour en gagner — la Génération libre, elle, reste toujours gratuite."
            ),
        )
    _ajouter(cur, enseignant_id, -COUT_DEPOT_COURS, "depot_cours", None)
