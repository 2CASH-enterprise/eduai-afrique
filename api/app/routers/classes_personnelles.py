from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from ..db import get_cursor
from ..deps import get_enseignant_connecte
from ..schemas import EnseignantConnecte

router = APIRouter(prefix="/enseignant/classes-personnelles", tags=["classes-personnelles"])


class ClassePersonnelleResume(BaseModel):
    id: str
    nom: str
    matiere_id: str
    matiere: str
    niveau: str
    effectif: int | None


class CreationClassePersonnelle(BaseModel):
    nom: str
    matiere_id: str
    niveau: str
    effectif: int | None = None


@router.post("", response_model=ClassePersonnelleResume, status_code=status.HTTP_201_CREATED)
def creer_classe_personnelle(payload: CreationClassePersonnelle, enseignant: EnseignantConnecte = Depends(get_enseignant_connecte)):
    """Contexte déclaré par l'enseignant lui-même — pas d'élèves réels, pas
    de bulletins. Ouvre l'accès au vrai flux 'Déposer un cours' (avec sa
    file de validation), pas seulement à la Génération libre éphémère."""
    with get_cursor(commit=True) as cur:
        cur.execute("SELECT nom FROM matieres WHERE id = %s", (payload.matiere_id,))
        row = cur.fetchone()
        if row is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Matière introuvable")
        matiere_nom = row[0]

        cur.execute(
            "INSERT INTO classes_personnelles (enseignant_id, nom, matiere_id, niveau, effectif) "
            "VALUES (%s, %s, %s, %s, %s) RETURNING id",
            (enseignant.id, payload.nom, payload.matiere_id, payload.niveau, payload.effectif),
        )
        classe_id = cur.fetchone()[0]

    return ClassePersonnelleResume(id=str(classe_id), nom=payload.nom, matiere_id=payload.matiere_id,
                                     matiere=matiere_nom, niveau=payload.niveau, effectif=payload.effectif)


@router.get("", response_model=list[ClassePersonnelleResume])
def lister_classes_personnelles(enseignant: EnseignantConnecte = Depends(get_enseignant_connecte)):
    with get_cursor() as cur:
        cur.execute(
            """
            SELECT cp.id, cp.nom, cp.matiere_id, m.nom, cp.niveau, cp.effectif
            FROM classes_personnelles cp
            JOIN matieres m ON m.id = cp.matiere_id
            WHERE cp.enseignant_id = %s
            ORDER BY cp.created_at DESC
            """,
            (enseignant.id,),
        )
        lignes = cur.fetchall()
    return [ClassePersonnelleResume(id=str(id_), nom=nom, matiere_id=str(mid), matiere=matiere, niveau=niveau, effectif=eff)
            for id_, nom, mid, matiere, niveau, eff in lignes]


@router.delete("/{classe_id}", status_code=status.HTTP_204_NO_CONTENT)
def supprimer_classe_personnelle(classe_id: str, enseignant: EnseignantConnecte = Depends(get_enseignant_connecte)):
    with get_cursor(commit=True) as cur:
        cur.execute(
            "DELETE FROM classes_personnelles WHERE id = %s AND enseignant_id = %s RETURNING id",
            (classe_id, enseignant.id),
        )
        if cur.fetchone() is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Classe personnelle introuvable")
