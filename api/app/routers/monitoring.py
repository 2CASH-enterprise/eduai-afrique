"""Monitoring des bugs (discuté et cadré le 06/08, suite à l'incident
React #31 découvert le jour même) — trois sources unifiées côté Admin
Plateforme : échecs de génération IA, documents mal indexés, et plantages
navigateur (remontés automatiquement par l'Error Boundary React, voir
web/components/ErrorBoundary.jsx).
"""
from fastapi import APIRouter, Depends

from .. import erreurs
from ..db import get_cursor
from ..deps import get_admin_plateforme_connecte
from ..schemas import AdminPlateformeConnecte, RapportPlantage, ErreurSysteme

router = APIRouter(tags=["monitoring"])


@router.post("/erreurs/plantage-navigateur", status_code=204)
def signaler_plantage(payload: RapportPlantage):
    """PUBLIC, sans authentification — un plantage peut survenir avant
    même qu'un utilisateur soit connecté (ex : écran de connexion lui-même).
    Best-effort par nature (erreurs.enregistrer_erreur avale ses propres
    échecs) : ne doit jamais renvoyer d'erreur au navigateur qui vient déjà
    de planter une fois."""
    erreurs.enregistrer_erreur("plantage_navigateur", payload.message, {
        "stack": payload.stack, "url": payload.url, "user_agent": payload.user_agent,
    })


@router.get("/plateforme/erreurs", response_model=list[ErreurSysteme])
def lister_erreurs(admin: AdminPlateformeConnecte = Depends(get_admin_plateforme_connecte)):
    """Vue unifiée : erreurs_systeme (génération IA, plantages navigateur)
    + documents_pedagogiques en erreur d'indexation (déjà stockés là,
    juste rassemblés ici plutôt que dans un écran séparé)."""
    with get_cursor() as cur:
        cur.execute(
            "SELECT id, type_erreur, message, contexte, created_at FROM erreurs_systeme ORDER BY created_at DESC LIMIT 200"
        )
        lignes = [ErreurSysteme(id=str(i), type_erreur=t, message=m, contexte=c, created_at=dt)
                  for i, t, m, c, dt in cur.fetchall()]

        cur.execute(
            "SELECT id, titre, pays, erreur_traitement, created_at FROM documents_pedagogiques "
            "WHERE statut = 'erreur' ORDER BY created_at DESC LIMIT 200"
        )
        for i, titre, pays, erreur_traitement, dt in cur.fetchall():
            lignes.append(ErreurSysteme(
                id=str(i), type_erreur="indexation_document",
                message=erreur_traitement or "Erreur d'indexation sans détail",
                contexte={"titre": titre, "pays": pays}, created_at=dt,
            ))

    lignes.sort(key=lambda e: e.created_at, reverse=True)
    return lignes
