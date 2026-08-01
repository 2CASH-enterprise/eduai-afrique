from fastapi import APIRouter, Depends, HTTPException, status

from ..db import get_cursor
from ..deps import get_enseignant_connecte
from ..schemas import (ClasseEnseignant, EleveResume, NoteDetail, AbsenceDetail,
                        CreationNote, CreationAbsence, EnseignantConnecte)

router = APIRouter(prefix="/enseignant", tags=["classes"])


def _verifier_eleve_dans_perimetre(cur, enseignant_id: str, eleve_id: str, matiere_id: str) -> str:
    """Vérifie que cet élève appartient à une classe où l'enseignant est
    affecté pour la matière donnée. Retourne le classe_id si c'est valide,
    lève 404 sinon (même logique de non-divulgation que les autres modules).
    """
    cur.execute(
        """
        SELECT el.classe_id
        FROM eleves el
        JOIN affectations_enseignants ae ON ae.classe_id = el.classe_id AND ae.matiere_id = %s
        WHERE el.utilisateur_id = %s AND ae.enseignant_id = %s
        """,
        (matiere_id, eleve_id, enseignant_id),
    )
    row = cur.fetchone()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                             detail="Élève introuvable dans votre périmètre pour cette matière")
    return str(row[0])


@router.get("/mes-classes", response_model=list[ClasseEnseignant])
def mes_classes(enseignant: EnseignantConnecte = Depends(get_enseignant_connecte)):
    with get_cursor() as cur:
        cur.execute(
            """
            SELECT c.id, ae.matiere_id, c.nom, n.id, n.nom, m.nom, e.nom,
                   COUNT(DISTINCT el.utilisateur_id) AS effectif
            FROM affectations_enseignants ae
            JOIN classes c ON c.id = ae.classe_id
            JOIN niveaux n ON n.id = c.niveau_id
            JOIN matieres m ON m.id = ae.matiere_id
            JOIN etablissements e ON e.id = c.etablissement_id
            LEFT JOIN eleves el ON el.classe_id = c.id
            WHERE ae.enseignant_id = %s
            GROUP BY c.id, ae.matiere_id, c.nom, n.id, n.nom, m.nom, e.nom, n.ordre
            ORDER BY n.ordre, c.nom
            """,
            (enseignant.id,),
        )
        lignes = cur.fetchall()

        resultats = []
        for classe_id, matiere_id, nom, niveau_id, niveau, matiere, etablissement_nom, effectif in lignes:
            cur.execute(
                """
                SELECT AVG(no.valeur / no.bareme * 20)
                FROM notes no
                JOIN eleves el ON el.utilisateur_id = no.eleve_id
                WHERE el.classe_id = %s AND no.matiere_id = %s
                """,
                (classe_id, matiere_id),
            )
            moyenne = cur.fetchone()[0]
            resultats.append(ClasseEnseignant(
                classe_id=str(classe_id), matiere_id=str(matiere_id), nom=nom,
                niveau_id=str(niveau_id), niveau=niveau,
                matiere=matiere, etablissement_nom=etablissement_nom, effectif=effectif,
                moyenne_classe=round(float(moyenne), 2) if moyenne is not None else None,
            ))

    return resultats


@router.get("/classes/{classe_id}/eleves", response_model=list[EleveResume])
def eleves_de_la_classe(
    classe_id: str,
    matiere_id: str,
    enseignant: EnseignantConnecte = Depends(get_enseignant_connecte),
):
    with get_cursor() as cur:
        cur.execute(
            "SELECT 1 FROM affectations_enseignants WHERE enseignant_id = %s AND classe_id = %s AND matiere_id = %s",
            (enseignant.id, classe_id, matiere_id),
        )
        if cur.fetchone() is None:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                 detail="Vous n'êtes pas affecté à cette classe pour cette matière")

        cur.execute(
            """
            SELECT u.id, u.nom, u.prenom, el.matricule
            FROM eleves el
            JOIN utilisateurs u ON u.id = el.utilisateur_id
            WHERE el.classe_id = %s
            ORDER BY u.nom, u.prenom
            """,
            (classe_id,),
        )
        eleves = cur.fetchall()

        resultats = []
        for eleve_id, nom, prenom, matricule in eleves:
            cur.execute(
                "SELECT AVG(valeur / bareme * 20) FROM notes WHERE eleve_id = %s AND matiere_id = %s",
                (eleve_id, matiere_id),
            )
            moyenne = cur.fetchone()[0]
            cur.execute(
                "SELECT COUNT(*) FROM absences WHERE eleve_id = %s AND type_absence = 'absence'",
                (eleve_id,),
            )
            nb_absences = cur.fetchone()[0]
            resultats.append(EleveResume(
                eleve_id=str(eleve_id), nom=nom, prenom=prenom, matricule=matricule,
                moyenne=round(float(moyenne), 2) if moyenne is not None else None,
                nombre_absences=nb_absences,
            ))

    return resultats


@router.get("/eleves/{eleve_id}/notes", response_model=list[NoteDetail])
def notes_eleve(
    eleve_id: str,
    matiere_id: str,
    enseignant: EnseignantConnecte = Depends(get_enseignant_connecte),
):
    with get_cursor() as cur:
        _verifier_eleve_dans_perimetre(cur, enseignant.id, eleve_id, matiere_id)
        cur.execute(
            """
            SELECT id, valeur, bareme, type_evaluation, trimestre, created_at
            FROM notes WHERE eleve_id = %s AND matiere_id = %s
            ORDER BY created_at DESC
            """,
            (eleve_id, matiere_id),
        )
        lignes = cur.fetchall()

    return [NoteDetail(id=str(id_), valeur=float(v), bareme=float(b), type_evaluation=t,
                        trimestre=tr, created_at=c)
            for id_, v, b, t, tr, c in lignes]


@router.post("/eleves/{eleve_id}/notes", response_model=NoteDetail, status_code=status.HTTP_201_CREATED)
def ajouter_note(
    eleve_id: str,
    payload: CreationNote,
    enseignant: EnseignantConnecte = Depends(get_enseignant_connecte),
):
    with get_cursor(commit=True) as cur:
        _verifier_eleve_dans_perimetre(cur, enseignant.id, eleve_id, payload.matiere_id)

        # Déduit l'année scolaire active plutôt que de la demander au frontend —
        # le client n'a aucun moyen simple de la connaître, et il n'y en a
        # normalement qu'une seule active par établissement à un instant donné.
        cur.execute(
            "SELECT id FROM annees_scolaires WHERE etablissement_id = %s AND est_active = true LIMIT 1",
            (enseignant.etablissement_id,),
        )
        annee = cur.fetchone()
        if annee is None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                                 detail="Aucune année scolaire active pour cet établissement")
        annee_scolaire_id = annee[0]

        cur.execute(
            """
            INSERT INTO notes (eleve_id, matiere_id, enseignant_id, valeur, bareme, type_evaluation,
                                trimestre, annee_scolaire_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id, valeur, bareme, type_evaluation, trimestre, created_at
            """,
            (eleve_id, payload.matiere_id, enseignant.id, payload.valeur, payload.bareme,
             payload.type_evaluation, payload.trimestre, annee_scolaire_id),
        )
        id_, v, b, t, tr, c = cur.fetchone()

    return NoteDetail(id=str(id_), valeur=float(v), bareme=float(b), type_evaluation=t, trimestre=tr, created_at=c)


@router.get("/eleves/{eleve_id}/absences", response_model=list[AbsenceDetail])
def absences_eleve(
    eleve_id: str,
    matiere_id: str,
    enseignant: EnseignantConnecte = Depends(get_enseignant_connecte),
):
    with get_cursor() as cur:
        _verifier_eleve_dans_perimetre(cur, enseignant.id, eleve_id, matiere_id)
        cur.execute(
            "SELECT id, date_absence, type_absence, justifie, motif FROM absences "
            "WHERE eleve_id = %s ORDER BY date_absence DESC",
            (eleve_id,),
        )
        lignes = cur.fetchall()

    return [AbsenceDetail(id=str(id_), date_absence=str(d), type_absence=t, justifie=j, motif=m)
            for id_, d, t, j, m in lignes]


@router.post("/eleves/{eleve_id}/absences", response_model=AbsenceDetail, status_code=status.HTTP_201_CREATED)
def ajouter_absence(
    eleve_id: str,
    matiere_id: str,
    payload: CreationAbsence,
    enseignant: EnseignantConnecte = Depends(get_enseignant_connecte),
):
    with get_cursor(commit=True) as cur:
        _verifier_eleve_dans_perimetre(cur, enseignant.id, eleve_id, matiere_id)
        cur.execute(
            """
            INSERT INTO absences (eleve_id, date_absence, type_absence, justifie, motif, signale_par_id)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id, date_absence, type_absence, justifie, motif
            """,
            (eleve_id, payload.date_absence, payload.type_absence, payload.justifie,
             payload.motif, enseignant.id),
        )
        id_, d, t, j, m = cur.fetchone()

    return AbsenceDetail(id=str(id_), date_absence=str(d), type_absence=t, justifie=j, motif=m)
