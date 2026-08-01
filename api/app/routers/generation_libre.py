from fastapi import APIRouter, Depends, HTTPException, status

from ..db import get_cursor
from ..deps import get_enseignant_connecte
from ..generation_libre import generer_exercice_a_la_demande
from ..schemas import DemandeGenerationLibre, ExerciceGenereLibre, EnseignantConnecte, MatiereResume

router = APIRouter(prefix="/enseignant", tags=["generation-libre"])


@router.get("/matieres", response_model=list[MatiereResume])
def lister_matieres(enseignant: EnseignantConnecte = Depends(get_enseignant_connecte)):
    """Référentiel global — utile en mode libre où l'enseignant n'a pas
    forcément d'affectation existante à une matière (cas indépendant)."""
    with get_cursor() as cur:
        cur.execute("SELECT id, nom FROM matieres ORDER BY nom")
        lignes = cur.fetchall()
    return [MatiereResume(id=str(id_), nom=nom) for id_, nom in lignes]


@router.post("/generation-libre", response_model=ExerciceGenereLibre)
def generer_en_mode_libre(payload: DemandeGenerationLibre, enseignant: EnseignantConnecte = Depends(get_enseignant_connecte)):
    """Génération à la demande, sur un niveau/matière choisis librement —
    aucune classe ni établissement requis (voir TODO.md point 1). Pensé
    d'abord pour l'enseignant indépendant, mais ouvert à tout enseignant :
    utile aussi pour explorer un thème avant de le proposer à une vraie
    classe. Le résultat n'est PAS persisté ni soumis à validation —
    contrairement au reste de la plateforme, il n'y a ici ni collègue ni
    établissement pour le relire, donc l'IA n'est jamais présentée comme
    fiable sans relecture (voir le champ `avertissement`)."""
    with get_cursor() as cur:
        cur.execute("SELECT nom FROM matieres WHERE id = %s", (payload.matiere_id,))
        row_matiere = cur.fetchone()

    if row_matiere is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Matière introuvable")

    donnees = generer_exercice_a_la_demande(matiere=row_matiere[0], niveau=payload.niveau, theme=payload.theme)

    return ExerciceGenereLibre(
        theme=payload.theme,
        sous_theme=donnees.get("sous_theme"),
        enonce=donnees.get("enonce", ""),
        corrige=donnees.get("corrige", ""),
        etapes=donnees.get("etapes", []),
        contexte=donnees.get("contexte"),
        tags=donnees.get("tags", []),
    )
