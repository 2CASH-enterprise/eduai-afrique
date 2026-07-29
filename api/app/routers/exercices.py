from fastapi import APIRouter, Depends, HTTPException, status

from ..db import get_cursor
from ..deps import get_enseignant_connecte
from ..schemas import (ExerciceEnAttente, ModificationExercice, RejetExercice,
                        ExerciceValide, EnseignantConnecte)

router = APIRouter(prefix="/enseignant/exercices", tags=["exercices"])


def _perimetre_enseignant(cur, enseignant_id: str) -> set[tuple[str, str]]:
    """Renvoie l'ensemble des (niveau_id, matiere_id) que cet enseignant est
    habilité à relire, d'après ses affectations réelles (table
    affectations_enseignants → classes → niveau). Un enseignant ne doit
    valider que le contenu des matières/niveaux qu'il enseigne réellement —
    pas la bibliothèque entière de l'établissement.
    """
    cur.execute(
        """
        SELECT DISTINCT c.niveau_id, ae.matiere_id
        FROM affectations_enseignants ae
        JOIN classes c ON c.id = ae.classe_id
        WHERE ae.enseignant_id = %s
        """,
        (enseignant_id,),
    )
    return {(str(niveau_id), str(matiere_id)) for niveau_id, matiere_id in cur.fetchall()}


def _verifier_perimetre(cur, enseignant_id: str, niveau_id: str, matiere_id: str) -> None:
    if (str(niveau_id), str(matiere_id)) not in _perimetre_enseignant(cur, enseignant_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cet exercice ne relève pas d'une matière/niveau que vous enseignez",
        )


def _charger_exercice_ou_404(cur, exercice_id: str):
    cur.execute(
        """
        SELECT e.id, e.niveau_id, e.matiere_id, n.nom AS niveau_nom, m.nom AS matiere_nom,
               e.theme, e.sous_theme, e.difficulte, e.enonce, e.corrige, e.etapes,
               e.contexte, e.tags, e.source, e.validation_ia, e.statut, e.created_at
        FROM exercices e
        JOIN niveaux n ON n.id = e.niveau_id
        JOIN matieres m ON m.id = e.matiere_id
        WHERE e.id = %s AND e.deleted_at IS NULL
        """,
        (exercice_id,),
    )
    row = cur.fetchone()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exercice introuvable")
    return row


@router.get("/a-valider", response_model=list[ExerciceEnAttente])
def lister_exercices_a_valider(
    enseignant: EnseignantConnecte = Depends(get_enseignant_connecte),
    limite: int = 20,
):
    """Liste les exercices en attente, restreinte au périmètre réel de
    l'enseignant (matières/niveaux qu'il enseigne effectivement)."""
    with get_cursor() as cur:
        perimetre = _perimetre_enseignant(cur, enseignant.id)
        if not perimetre:
            return []

        niveaux_ids, matieres_ids = zip(*perimetre) if perimetre else ([], [])
        # On filtre en Python plutôt qu'avec un IN sur des tuples (portabilité
        # psycopg2) : on récupère large sur les niveaux/matières concernés,
        # puis on ne garde que les couples exacts du périmètre.
        cur.execute(
            """
            SELECT e.id, e.theme, e.sous_theme, n.nom, m.nom, e.difficulte,
                   e.enonce, e.corrige, e.etapes, e.contexte, e.tags, e.source,
                   e.validation_ia, e.created_at, e.niveau_id, e.matiere_id
            FROM exercices e
            JOIN niveaux n ON n.id = e.niveau_id
            JOIN matieres m ON m.id = e.matiere_id
            WHERE e.statut = 'en_validation' AND e.deleted_at IS NULL
              AND e.niveau_id = ANY(%s::uuid[]) AND e.matiere_id = ANY(%s::uuid[])
            ORDER BY e.created_at ASC
            LIMIT %s
            """,
            (list(niveaux_ids), list(matieres_ids), limite),
        )
        lignes = cur.fetchall()

    resultats = []
    for row in lignes:
        (id_, theme, sous_theme, niveau_nom, matiere_nom, difficulte, enonce, corrige,
         etapes, contexte, tags, source, validation_ia, created_at, niveau_id, matiere_id) = row
        if (str(niveau_id), str(matiere_id)) not in perimetre:
            continue  # double-vérification : le ANY() ci-dessus est une union, pas le produit exact
        resultats.append(ExerciceEnAttente(
            id=str(id_), theme=theme, sous_theme=sous_theme, niveau=niveau_nom,
            matiere=matiere_nom, difficulte=difficulte, enonce=enonce, corrige=corrige,
            etapes=etapes or [], contexte=contexte, tags=tags or [], source=source,
            validation_ia=validation_ia, created_at=created_at,
        ))
    return resultats


@router.patch("/{exercice_id}", response_model=ExerciceEnAttente)
def modifier_exercice(
    exercice_id: str,
    modifications: ModificationExercice,
    enseignant: EnseignantConnecte = Depends(get_enseignant_connecte),
):
    """Permet à l'enseignant de corriger le contenu avant de le valider —
    une coquille dans l'énoncé ne doit pas forcer un rejet complet."""
    with get_cursor(commit=True) as cur:
        row = _charger_exercice_ou_404(cur, exercice_id)
        _verifier_perimetre(cur, enseignant.id, row[1], row[2])

        champs_possibles = {"enonce": modifications.enonce, "corrige": modifications.corrige,
                             "etapes": modifications.etapes, "difficulte": modifications.difficulte}
        a_modifier = {k: v for k, v in champs_possibles.items() if v is not None}
        if not a_modifier:
            raise HTTPException(status_code=422, detail="Aucune modification fournie")

        assignations = ", ".join(f"{champ} = %s" for champ in a_modifier)
        cur.execute(
            f"UPDATE exercices SET {assignations} WHERE id = %s",
            (*a_modifier.values(), exercice_id),
        )
        row = _charger_exercice_ou_404(cur, exercice_id)

    return ExerciceEnAttente(
        id=str(row[0]), theme=row[5], sous_theme=row[6], niveau=row[3], matiere=row[4],
        difficulte=row[7], enonce=row[8], corrige=row[9], etapes=row[10] or [],
        contexte=row[11], tags=row[12] or [], source=row[13], validation_ia=row[14],
        created_at=row[16],
    )


@router.post("/{exercice_id}/valider", response_model=ExerciceValide)
def valider_exercice(
    exercice_id: str,
    enseignant: EnseignantConnecte = Depends(get_enseignant_connecte),
):
    with get_cursor(commit=True) as cur:
        row = _charger_exercice_ou_404(cur, exercice_id)
        _verifier_perimetre(cur, enseignant.id, row[1], row[2])
        if row[15] != "en_validation":
            raise HTTPException(status_code=409,
                                 detail=f"Cet exercice est déjà au statut '{row[15]}', "
                                        f"il n'est plus en attente de relecture")

        cur.execute(
            """
            UPDATE exercices
            SET validation_humaine = true, statut = 'valide',
                valide_par_id = %s, date_validation = now()
            WHERE id = %s
            RETURNING id, statut, valide_par_id, date_validation
            """,
            (enseignant.id, exercice_id),
        )
        resultat = cur.fetchone()

    return ExerciceValide(id=str(resultat[0]), statut=resultat[1],
                           valide_par_id=str(resultat[2]), date_validation=resultat[3])


@router.post("/{exercice_id}/rejeter", response_model=ExerciceValide)
def rejeter_exercice(
    exercice_id: str,
    rejet: RejetExercice,
    enseignant: EnseignantConnecte = Depends(get_enseignant_connecte),
):
    """Le motif est obligatoire (validé par le schéma Pydantic, min 5
    caractères) — un exercice généré automatiquement qui échoue en relecture
    humaine est un signal pour ajuster le template ou le prompt, pas juste
    une suppression silencieuse."""
    with get_cursor(commit=True) as cur:
        row = _charger_exercice_ou_404(cur, exercice_id)
        _verifier_perimetre(cur, enseignant.id, row[1], row[2])
        if row[15] != "en_validation":
            raise HTTPException(status_code=409,
                                 detail=f"Cet exercice est déjà au statut '{row[15]}'")

        # Le motif est stocké dans le champ JSONB `liens`, réutilisé plutôt
        # que d'ajouter une colonne dédiée pour un besoin encore peu volumineux.
        cur.execute(
            """
            UPDATE exercices
            SET statut = 'rejete', valide_par_id = %s, date_validation = now(),
                liens = liens || jsonb_build_object('motif_rejet', %s::text)
            WHERE id = %s
            RETURNING id, statut, valide_par_id, date_validation
            """,
            (enseignant.id, rejet.motif, exercice_id),
        )
        resultat = cur.fetchone()

    return ExerciceValide(id=str(resultat[0]), statut=resultat[1],
                           valide_par_id=str(resultat[2]), date_validation=resultat[3])
