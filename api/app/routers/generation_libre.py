from fastapi import APIRouter, Depends, HTTPException, status

from .. import rag
from ..db import get_cursor
from ..deps import get_enseignant_connecte
from ..generation_libre import generer_exercice_a_la_demande
from ..schemas import DemandeGenerationLibre, ExerciceGenereLibre, EnseignantConnecte, MatiereResume

router = APIRouter(prefix="/enseignant", tags=["generation-libre"])


def _rechercher_contexte_libre(matiere_nom: str, niveau: str, theme: str, matiere_id: str,
                                 etablissement_id: str | None, enseignant_id: str) -> list[str]:
    """Best-effort, comme partout ailleurs où le RAG enrichit une
    génération : jamais bloquant, jamais visible de l'utilisateur en cas
    d'échec — juste moins de contexte pour cette génération précise. Pas de
    niveau_id disponible ici (niveaux n'est pas une table globale, voir
    TODO.md point 3 et le module generation_libre) : le filtre se fait
    uniquement sur la matière."""
    try:
        client = rag.obtenir_client_mistral()
        if client is None:
            return []
        embedding = rag.generer_embeddings(client, [f"{matiere_nom} {niveau} {theme}"])[0]
        with get_cursor() as cur:
            return rag.rechercher_passages_pertinents(
                cur, embedding, niveau_id=None, matiere_id=matiere_id,
                etablissement_id=etablissement_id, utilisateur_id_demandeur=enseignant_id, k=4,
            )
    except Exception:
        return []


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

    passages = _rechercher_contexte_libre(row_matiere[0], payload.niveau, payload.theme,
                                            payload.matiere_id, enseignant.etablissement_id, enseignant.id)

    donnees = generer_exercice_a_la_demande(matiere=row_matiere[0], niveau=payload.niveau, theme=payload.theme,
                                              passages_contexte=passages)

    return ExerciceGenereLibre(
        theme=payload.theme,
        sous_theme=donnees.get("sous_theme"),
        enonce=donnees.get("enonce", ""),
        corrige=donnees.get("corrige", ""),
        etapes=donnees.get("etapes", []),
        contexte=donnees.get("contexte"),
        tags=donnees.get("tags", []),
    )
