from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from .. import rag
from .. import credits
from ..db import get_cursor
from ..deps import get_enseignant_connecte
from ..generation_libre import generer_exercice_a_la_demande
from ..schemas import (DemandeGenerationLibre, ExerciceGenereLibre, ModificationExerciceGenereLibre,
                        EnseignantConnecte, MatiereResume)
from ..text_utils import aplatir_en_texte

router = APIRouter(prefix="/enseignant", tags=["generation-libre"])

QUANTITE_MIN, QUANTITE_MAX = 1, 5


class MouvementCredit(BaseModel):
    delta: int
    motif: str
    created_at: str


class SoldeCredits(BaseModel):
    solde: int
    en_periode_gratuite: bool
    historique: list[MouvementCredit]


@router.get("/credits", response_model=SoldeCredits)
def consulter_mes_credits(enseignant: EnseignantConnecte = Depends(get_enseignant_connecte)):
    """Jauge strictement personnelle — jamais visible par l'établissement
    (voir la discussion produit du 01/08)."""
    with get_cursor() as cur:
        gratuite = credits.en_periode_gratuite(cur, enseignant.id)
        solde_actuel = credits.solde(cur, enseignant.id)
        cur.execute(
            "SELECT delta, motif, created_at FROM credits_enseignant WHERE enseignant_id = %s "
            "ORDER BY created_at DESC LIMIT 20",
            (enseignant.id,),
        )
        historique = [MouvementCredit(delta=d, motif=m, created_at=c.isoformat()) for d, m, c in cur.fetchall()]
    return SoldeCredits(solde=solde_actuel, en_periode_gratuite=gratuite, historique=historique)


def _rechercher_contexte_libre(matiere_nom: str, niveau: str, theme: str, matiere_id: str,
                                 etablissement_id: str | None, enseignant_id: str, pays: str | None) -> list[str]:
    """Best-effort, comme partout ailleurs où le RAG enrichit une
    génération : jamais bloquant, jamais visible de l'utilisateur en cas
    d'échec — juste moins de contexte pour cette génération précise. Pas de
    niveau_id disponible ici (niveaux n'est pas une table globale, voir
    TODO.md point 3) : le filtre se fait sur la matière et le pays."""
    try:
        client = rag.obtenir_client_mistral()
        if client is None:
            return []
        embedding = rag.generer_embeddings(client, [f"{matiere_nom} {niveau} {theme}"])[0]
        with get_cursor() as cur:
            return rag.rechercher_passages_pertinents(
                cur, embedding, niveau_id=None, matiere_id=matiere_id,
                etablissement_id=etablissement_id, utilisateur_id_demandeur=enseignant_id, pays=pays, k=4,
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


def _generer_un_exercice_normalise(matiere_nom: str, niveau: str, theme: str, passages: list[str], indice: int) -> dict:
    """Appelle l'IA puis aplatit défensivement chaque champ vers son type
    attendu — rien ne garantit qu'elle renvoie exactement des chaînes
    simples (incidents des 02/08 et 03/08)."""
    theme_varie = theme if indice == 0 else f"{theme} (variante {indice + 1}, différente des précédentes)"
    donnees = generer_exercice_a_la_demande(matiere=matiere_nom, niveau=niveau, theme=theme_varie, passages_contexte=passages)

    def _str(valeur):
        return aplatir_en_texte(valeur) if valeur is not None and not isinstance(valeur, str) else valeur

    etapes_brutes = donnees.get("etapes", []) or []
    if not isinstance(etapes_brutes, list):
        etapes_brutes = [etapes_brutes]
    etapes = [aplatir_en_texte(e) if not isinstance(e, str) else e for e in etapes_brutes]

    tags_bruts = donnees.get("tags", []) or []
    if not isinstance(tags_bruts, list):
        tags_bruts = [tags_bruts]
    tags = [aplatir_en_texte(t) if not isinstance(t, str) else t for t in tags_bruts]

    return {
        "sous_theme": _str(donnees.get("sous_theme")),
        "enonce": _str(donnees.get("enonce", "")) or "",
        "corrige": _str(donnees.get("corrige", "")) or "",
        "etapes": etapes,
        "contexte": _str(donnees.get("contexte")),
        "tags": tags,
    }


@router.post("/generation-libre", response_model=list[ExerciceGenereLibre], status_code=status.HTTP_201_CREATED)
def generer_en_mode_libre(payload: DemandeGenerationLibre, enseignant: EnseignantConnecte = Depends(get_enseignant_connecte)):
    """Redéfini le 03/08 : génère une SÉRIE d'exercices corrigés (1 à 5,
    au choix de l'enseignant) sur un niveau/matière/thème choisis librement
    — aucune classe ni établissement requis (voir TODO.md point 1). Chaque
    exercice est désormais PERSISTÉ avec un statut à valider — comme les
    ressources de "Déposer un cours" — et sa validation réinjecte le
    corpus documentaire. Toujours gratuite, sans condition, à la
    différence de "Déposer un cours" (décision du 03/08)."""
    if not (QUANTITE_MIN <= payload.quantite <= QUANTITE_MAX):
        raise HTTPException(status_code=422, detail=f"quantite doit être entre {QUANTITE_MIN} et {QUANTITE_MAX}")

    with get_cursor() as cur:
        cur.execute("SELECT nom FROM matieres WHERE id = %s", (payload.matiere_id,))
        row_matiere = cur.fetchone()
    if row_matiere is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Matière introuvable")
    matiere_nom = row_matiere[0]

    passages = _rechercher_contexte_libre(matiere_nom, payload.niveau, payload.theme,
                                            payload.matiere_id, enseignant.etablissement_id, enseignant.id, enseignant.pays)

    resultats = []
    with get_cursor(commit=True) as cur:
        for i in range(payload.quantite):
            donnees = _generer_un_exercice_normalise(matiere_nom, payload.niveau, payload.theme, passages, i)
            cur.execute(
                """
                INSERT INTO exercices_generation_libre
                    (enseignant_id, matiere_id, niveau, theme, pays, sous_theme, enonce, corrige, etapes, contexte, tags, statut)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'en_attente')
                RETURNING id, created_at
                """,
                (enseignant.id, payload.matiere_id, payload.niveau, payload.theme, enseignant.pays,
                 donnees["sous_theme"], donnees["enonce"], donnees["corrige"], donnees["etapes"],
                 donnees["contexte"], donnees["tags"]),
            )
            ex_id, created_at = cur.fetchone()
            resultats.append(ExerciceGenereLibre(
                id=str(ex_id), theme=payload.theme, sous_theme=donnees["sous_theme"],
                niveau=payload.niveau, matiere=matiere_nom, enonce=donnees["enonce"], corrige=donnees["corrige"],
                etapes=donnees["etapes"], contexte=donnees["contexte"], tags=donnees["tags"],
                statut="en_attente", created_at=created_at,
            ))

    return resultats


@router.get("/generation-libre", response_model=list[ExerciceGenereLibre])
def lister_generations_libres(enseignant: EnseignantConnecte = Depends(get_enseignant_connecte)):
    """Historique complet de l'enseignant — en_attente, validés et
    rejetés, du plus récent au plus ancien."""
    with get_cursor() as cur:
        cur.execute(
            """
            SELECT e.id, e.theme, e.sous_theme, e.niveau, m.nom, e.enonce, e.corrige,
                   e.etapes, e.contexte, e.tags, e.statut, e.created_at
            FROM exercices_generation_libre e
            JOIN matieres m ON m.id = e.matiere_id
            WHERE e.enseignant_id = %s
            ORDER BY e.created_at DESC
            """,
            (enseignant.id,),
        )
        lignes = cur.fetchall()
    return [
        ExerciceGenereLibre(id=str(id_), theme=theme, sous_theme=sous_theme, niveau=niveau, matiere=matiere,
                              enonce=enonce, corrige=corrige, etapes=etapes or [], contexte=contexte, tags=tags or [],
                              statut=statut, created_at=created_at)
        for id_, theme, sous_theme, niveau, matiere, enonce, corrige, etapes, contexte, tags, statut, created_at in lignes
    ]


@router.patch("/generation-libre/{exercice_id}", status_code=status.HTTP_204_NO_CONTENT)
def valider_ou_rejeter(exercice_id: str, payload: ModificationExerciceGenereLibre,
                        enseignant: EnseignantConnecte = Depends(get_enseignant_connecte)):
    """Valider réinjecte silencieusement le corpus documentaire (Type 3,
    voir rag.reinjecter_contenu_valide) — l'exercice, lui, reste visible
    dans l'historique de l'enseignant quel que soit le choix."""
    if payload.statut not in ("valide", "rejete"):
        raise HTTPException(status_code=422, detail="Statut invalide — attendu 'valide' ou 'rejete'")

    with get_cursor(commit=True) as cur:
        cur.execute(
            "SELECT theme, niveau, matiere_id, pays, enonce, corrige, etapes, statut "
            "FROM exercices_generation_libre WHERE id = %s AND enseignant_id = %s",
            (exercice_id, enseignant.id),
        )
        row = cur.fetchone()
        if row is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exercice introuvable")
        theme, niveau, matiere_id, pays, enonce, corrige, etapes, statut_avant = row

        cur.execute("UPDATE exercices_generation_libre SET statut = %s WHERE id = %s", (payload.statut, exercice_id))

    if payload.statut == "valide" and statut_avant != "valide":
        texte = "\n".join(filter(None, [enonce, corrige, "\n".join(etapes or [])]))
        rag.reinjecter_contenu_valide(titre=theme, texte=texte, niveau_id=None, matiere_id=matiere_id, pays=pays)
