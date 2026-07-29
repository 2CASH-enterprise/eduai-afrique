from fastapi import APIRouter, Depends, HTTPException, status

from ..db import get_cursor
from ..deps import get_eleve_connecte
from ..schemas import (ExerciceDisponible, CorrigeExercice, DeclarationTentative,
                        TentativeEnregistree, ResultatMatiere, DevoirAVenir,
                        NotificationEleve, EleveConnecte)

router = APIRouter(prefix="/eleve", tags=["eleve"])


@router.get("/exercices", response_model=list[ExerciceDisponible])
def lister_exercices_disponibles(
    eleve: EleveConnecte = Depends(get_eleve_connecte),
    matiere: str | None = None,
    theme: str | None = None,
    limite: int = 50,
):
    """Exercices validés (statut='valide') pour le niveau de l'élève. Le
    corrigé n'est jamais renvoyé ici — voir /exercices/{id}/reveler."""
    with get_cursor() as cur:
        cur.execute(
            """
            SELECT e.id, e.theme, e.sous_theme, e.difficulte, e.enonce, e.contexte, e.tags
            FROM exercices e
            JOIN matieres m ON m.id = e.matiere_id
            WHERE e.niveau_id = %s AND e.statut = 'valide' AND e.deleted_at IS NULL
              AND (%s::text IS NULL OR m.nom = %s)
              AND (%s::text IS NULL OR e.theme = %s)
            ORDER BY e.theme, e.created_at
            LIMIT %s
            """,
            (eleve.niveau_id, matiere, matiere, theme, theme, limite),
        )
        lignes = cur.fetchall()

    return [
        ExerciceDisponible(id=str(id_), theme=theme, sous_theme=sous_theme, difficulte=difficulte,
                            enonce=enonce, contexte=contexte, tags=tags or [])
        for id_, theme, sous_theme, difficulte, enonce, contexte, tags in lignes
    ]


def _charger_exercice_valide_du_niveau(cur, exercice_id: str, niveau_id: str):
    cur.execute(
        """
        SELECT id, corrige, etapes FROM exercices
        WHERE id = %s AND niveau_id = %s AND statut = 'valide' AND deleted_at IS NULL
        """,
        (exercice_id, niveau_id),
    )
    row = cur.fetchone()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                             detail="Exercice introuvable, non publié, ou hors de votre niveau")
    return row


@router.post("/exercices/{exercice_id}/reveler", response_model=CorrigeExercice)
def reveler_corrige(
    exercice_id: str,
    eleve: EleveConnecte = Depends(get_eleve_connecte),
):
    with get_cursor() as cur:
        _, corrige, etapes = _charger_exercice_valide_du_niveau(cur, exercice_id, eleve.niveau_id)
    return CorrigeExercice(corrige=corrige, etapes=etapes or [])


@router.post("/exercices/{exercice_id}/tentative", response_model=TentativeEnregistree)
def declarer_tentative(
    exercice_id: str,
    tentative: DeclarationTentative,
    eleve: EleveConnecte = Depends(get_eleve_connecte),
):
    """Enregistre une tentative auto-déclarée (l'élève indique s'il a réussi
    après avoir consulté le corrigé). Les statistiques de l'exercice sont
    recalculées par agrégation sur tentatives_exercices plutôt que par
    incrément JSONB en place — plus simple et sans risque de dérive sous
    accès concurrents (deux élèves qui valident en même temps)."""
    with get_cursor(commit=True) as cur:
        _charger_exercice_valide_du_niveau(cur, exercice_id, eleve.niveau_id)

        cur.execute(
            """
            INSERT INTO tentatives_exercices (exercice_id, eleve_id, reussi, temps_passe_secondes, reponse_donnee)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id, exercice_id, reussi, created_at
            """,
            (exercice_id, eleve.id, tentative.reussi, tentative.temps_passe_secondes, tentative.reponse_donnee),
        )
        nouvelle_tentative = cur.fetchone()

        cur.execute(
            """
            SELECT COUNT(*), AVG(CASE WHEN reussi THEN 1.0 ELSE 0.0 END), AVG(temps_passe_secondes)
            FROM tentatives_exercices WHERE exercice_id = %s
            """,
            (exercice_id,),
        )
        nombre, taux_reussite, temps_moyen = cur.fetchone()

        cur.execute(
            """
            UPDATE exercices SET statistiques = jsonb_build_object(
                'nombre_tentatives', %s,
                'taux_reussite', %s,
                'temps_moyen_secondes', %s
            ) WHERE id = %s
            """,
            (nombre, round(float(taux_reussite or 0), 3),
             round(float(temps_moyen), 0) if temps_moyen is not None else None, exercice_id),
        )

    return TentativeEnregistree(id=str(nouvelle_tentative[0]), exercice_id=str(nouvelle_tentative[1]),
                                 reussi=nouvelle_tentative[2], created_at=nouvelle_tentative[3])


@router.get("/mes-resultats", response_model=list[ResultatMatiere])
def mes_resultats(eleve: EleveConnecte = Depends(get_eleve_connecte)):
    with get_cursor() as cur:
        cur.execute(
            """
            SELECT m.nom, v.trimestre, v.moyenne_sur_20, v.nombre_notes
            FROM vue_moyennes_eleve v
            JOIN matieres m ON m.id = v.matiere_id
            WHERE v.eleve_id = %s
            ORDER BY v.trimestre, m.nom
            """,
            (eleve.id,),
        )
        lignes = cur.fetchall()

    return [ResultatMatiere(matiere=m, trimestre=t, moyenne_sur_20=float(moy), nombre_notes=n)
            for m, t, moy, n in lignes]


@router.get("/mon-planning", response_model=list[DevoirAVenir])
def mon_planning(eleve: EleveConnecte = Depends(get_eleve_connecte)):
    with get_cursor() as cur:
        cur.execute(
            """
            SELECT d.id, d.titre, m.nom, d.description, d.date_limite
            FROM devoirs d
            JOIN matieres m ON m.id = d.matiere_id
            WHERE d.classe_id = %s AND d.date_limite >= now()
            ORDER BY d.date_limite ASC
            """,
            (eleve.classe_id,),
        )
        lignes = cur.fetchall()

    return [DevoirAVenir(id=str(id_), titre=titre, matiere=matiere, description=description,
                          date_limite=date_limite)
            for id_, titre, matiere, description, date_limite in lignes]


@router.get("/notifications", response_model=list[NotificationEleve])
def mes_notifications(eleve: EleveConnecte = Depends(get_eleve_connecte)):
    with get_cursor() as cur:
        cur.execute(
            """
            SELECT id, titre, message, type_notification, lue, created_at
            FROM notifications
            WHERE utilisateur_id = %s
            ORDER BY lue ASC, created_at DESC
            """,
            (eleve.id,),
        )
        lignes = cur.fetchall()

    return [NotificationEleve(id=str(id_), titre=titre, message=message, type_notification=type_,
                               lue=lue, created_at=created_at)
            for id_, titre, message, type_, lue, created_at in lignes]


@router.patch("/notifications/{notification_id}/lu")
def marquer_notification_lue(
    notification_id: str,
    eleve: EleveConnecte = Depends(get_eleve_connecte),
):
    with get_cursor(commit=True) as cur:
        cur.execute(
            "UPDATE notifications SET lue = true WHERE id = %s AND utilisateur_id = %s RETURNING id",
            (notification_id, eleve.id),
        )
        if cur.fetchone() is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification introuvable")
    return {"statut": "ok"}
