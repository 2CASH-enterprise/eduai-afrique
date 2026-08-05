"""Contrôle de quelles cartes apparaissent sur le portail public (TODO.md,
discuté le 05/08), en préparation du lancement en test ouvert du seul
module Enseignant. Admin Plateforme n'est volontairement pas dans ce
système : retiré définitivement du portail public, pas "en attente
d'activation" comme les autres — voir migration 015.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from ..db import get_cursor
from ..deps import get_admin_plateforme_connecte
from ..schemas import AdminPlateformeConnecte

router = APIRouter(tags=["modules"])

MODULES_VALIDES = {"eleve", "enseignant", "direction", "parent", "administration"}


class ModuleActif(BaseModel):
    module: str
    actif: bool


class ModificationModuleActif(BaseModel):
    actif: bool


@router.get("/modules-actifs", response_model=list[ModuleActif])
def lister_modules_actifs():
    """PUBLIC, sans authentification — c'est justement ce qui décide quelles
    cartes afficher sur le portail avant toute connexion. Ne révèle rien de
    sensible (juste quel module est actif ou non), comme la page d'accueil
    elle-même est déjà publique."""
    with get_cursor() as cur:
        cur.execute("SELECT module, actif FROM modules_actifs ORDER BY module")
        lignes = cur.fetchall()
    return [ModuleActif(module=m, actif=a) for m, a in lignes]


@router.patch("/plateforme/modules/{module}", response_model=ModuleActif)
def modifier_module_actif(module: str, payload: ModificationModuleActif,
                            admin: AdminPlateformeConnecte = Depends(get_admin_plateforme_connecte)):
    if module not in MODULES_VALIDES:
        raise HTTPException(status_code=422, detail="Module inconnu")
    with get_cursor(commit=True) as cur:
        cur.execute(
            "UPDATE modules_actifs SET actif = %s, updated_at = now() WHERE module = %s RETURNING module, actif",
            (payload.actif, module),
        )
        row = cur.fetchone()
        if row is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Module introuvable")
    return ModuleActif(module=row[0], actif=row[1])
