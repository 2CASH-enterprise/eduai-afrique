import json
from fastapi import APIRouter, Depends, HTTPException, status

from .. import rag
from .. import generation_cours
from ..db import get_cursor
from ..deps import get_enseignant_connecte
from ..schemas import DepotCours, CoursResume, CoursDetail, ModificationRessource, EnseignantConnecte

router = APIRouter(prefix="/enseignant/cours", tags=["cours"])

TYPES_RESSOURCE = ["fiche_pedagogique", "resume", "exercices", "qcm", "devoir", "controle"]

LABELS_RESSOURCE = {
    "fiche_pedagogique": "Fiche pédagogique",
    "resume": "Résumé",
    "exercices": "Exercices",
    "qcm": "QCM",
    "devoir": "Devoir",
    "controle": "Contrôle",
}



def _verifier_cours_du_enseignant(cur, cours_id: str, enseignant_id: str):
    cur.execute(
        """
        SELECT c.id, c.titre, c.contenu_texte, c.created_at, m.nom, cl.nom
        FROM cours c
        JOIN matieres m ON m.id = c.matiere_id
        JOIN classes cl ON cl.id = c.classe_id
        WHERE c.id = %s AND c.enseignant_id = %s
        """,
        (cours_id, enseignant_id),
    )
    row = cur.fetchone()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                             detail="Cours introuvable dans votre banque personnelle")
    return row


@router.post("", response_model=CoursDetail, status_code=status.HTTP_201_CREATED)
def deposer_cours(
    payload: DepotCours,
    enseignant: EnseignantConnecte = Depends(get_enseignant_connecte),
):
    with get_cursor(commit=True) as cur:
        # Vérifie que l'enseignant est bien affecté à cette classe/matière
        cur.execute(
            "SELECT 1 FROM affectations_enseignants WHERE enseignant_id = %s AND classe_id = %s AND matiere_id = %s",
            (enseignant.id, payload.classe_id, payload.matiere_id),
        )
        if cur.fetchone() is None:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                 detail="Vous n'êtes pas affecté à cette classe pour cette matière")

        cur.execute(
            """
            INSERT INTO cours (enseignant_id, classe_id, matiere_id, titre, contenu_texte, fichier_url, date_seance)
            VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id, titre, contenu_texte, created_at
            """,
            (enseignant.id, payload.classe_id, payload.matiere_id, payload.titre,
             payload.contenu_texte, payload.fichier_url, payload.date_seance),
        )
        cours_id, titre, contenu_texte, created_at = cur.fetchone()

        cur.execute("SELECT nom FROM matieres WHERE id = %s", (payload.matiere_id,))
        matiere_nom = cur.fetchone()[0]
        cur.execute(
            "SELECT c.niveau_id, n.nom, c.etablissement_id FROM classes c "
            "JOIN niveaux n ON n.id = c.niveau_id WHERE c.id = %s",
            (payload.classe_id,),
        )
        niveau_id, niveau_nom, etablissement_id = cur.fetchone()

        ressources = []
        for type_ressource in TYPES_RESSOURCE:
            contenu = generation_cours.generer_ressource(
                type_ressource, titre, contenu_texte, matiere_nom, niveau_nom,
                str(niveau_id), payload.matiere_id, str(etablissement_id), enseignant.id,
            )
            cur.execute(
                """
                INSERT INTO ressources_generees (cours_id, type_ressource, contenu, statut)
                VALUES (%s, %s, %s, 'en_attente') RETURNING id, type_ressource, contenu, statut
                """,
                (cours_id, type_ressource, json.dumps(contenu)),
            )
            r_id, r_type, r_contenu, r_statut = cur.fetchone()
            ressources.append({"id": str(r_id), "type_ressource": r_type, "label": LABELS_RESSOURCE[r_type],
                                "contenu": r_contenu, "statut": r_statut})

        cur.execute("SELECT nom FROM classes WHERE id = %s", (payload.classe_id,))
        classe_nom = cur.fetchone()[0]

    return CoursDetail(id=str(cours_id), titre=titre, matiere=matiere_nom, classe=classe_nom,
                        contenu_texte=contenu_texte, created_at=created_at, ressources=ressources)


@router.get("", response_model=list[CoursResume])
def lister_mes_cours(enseignant: EnseignantConnecte = Depends(get_enseignant_connecte)):
    with get_cursor() as cur:
        cur.execute(
            """
            SELECT c.id, c.titre, m.nom, cl.nom, c.created_at,
                   COUNT(*) FILTER (WHERE r.statut = 'valide') AS validees,
                   COUNT(*) AS total
            FROM cours c
            JOIN matieres m ON m.id = c.matiere_id
            JOIN classes cl ON cl.id = c.classe_id
            LEFT JOIN ressources_generees r ON r.cours_id = c.id
            WHERE c.enseignant_id = %s
            GROUP BY c.id, c.titre, m.nom, cl.nom, c.created_at
            ORDER BY c.created_at DESC
            """,
            (enseignant.id,),
        )
        lignes = cur.fetchall()

    return [CoursResume(id=str(id_), titre=titre, matiere=matiere, classe=classe, created_at=created_at,
                         nombre_ressources_validees=validees, nombre_ressources_total=total)
            for id_, titre, matiere, classe, created_at, validees, total in lignes]


@router.get("/{cours_id}", response_model=CoursDetail)
def detail_cours(cours_id: str, enseignant: EnseignantConnecte = Depends(get_enseignant_connecte)):
    with get_cursor() as cur:
        cours_id_v, titre, contenu_texte, created_at, matiere_nom, classe_nom = _verifier_cours_du_enseignant(
            cur, cours_id, enseignant.id)

        cur.execute(
            "SELECT id, type_ressource, contenu, statut FROM ressources_generees WHERE cours_id = %s "
            "AND statut != 'supprime' ORDER BY type_ressource",
            (cours_id,),
        )
        ressources = [{"id": str(r_id), "type_ressource": r_type, "label": LABELS_RESSOURCE[r_type],
                       "contenu": r_contenu, "statut": r_statut}
                      for r_id, r_type, r_contenu, r_statut in cur.fetchall()]

    return CoursDetail(id=str(cours_id_v), titre=titre, matiere=matiere_nom, classe=classe_nom,
                        contenu_texte=contenu_texte, created_at=created_at, ressources=ressources)


@router.patch("/{cours_id}/ressources/{ressource_id}")
def modifier_ressource(
    cours_id: str,
    ressource_id: str,
    payload: ModificationRessource,
    enseignant: EnseignantConnecte = Depends(get_enseignant_connecte),
):
    with get_cursor(commit=True) as cur:
        _verifier_cours_du_enseignant(cur, cours_id, enseignant.id)

        cur.execute(
            "SELECT id FROM ressources_generees WHERE id = %s AND cours_id = %s",
            (ressource_id, cours_id),
        )
        if cur.fetchone() is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ressource introuvable")

        champs = {}
        if payload.contenu is not None:
            champs["contenu"] = json.dumps(payload.contenu)
        if payload.statut is not None:
            if payload.statut not in ("en_attente", "valide", "corrige", "supprime"):
                raise HTTPException(status_code=422, detail="Statut invalide")
            champs["statut"] = payload.statut

        if not champs:
            raise HTTPException(status_code=422, detail="Aucune modification fournie")

        assignations = ", ".join(f"{k} = %s" for k in champs)
        cur.execute(f"UPDATE ressources_generees SET {assignations} WHERE id = %s",
                    (*champs.values(), ressource_id))

        # Type 3 du corpus documentaire : une ressource de cours validée par
        # l'enseignant est une création propre de la plateforme, réinjectée
        # pour enrichir les futures générations — jamais consultable comme
        # document par ailleurs (voir rag.reinjecter_contenu_valide).
        texte, niveau_id, matiere_id, titre_reinjection = None, None, None, None
        if payload.statut == "valide":
            cur.execute(
                """
                SELECT c.matiere_id, cl.niveau_id, c.titre, r.type_ressource, r.contenu
                FROM ressources_generees r
                JOIN cours c ON c.id = r.cours_id
                JOIN classes cl ON cl.id = c.classe_id
                WHERE r.id = %s
                """,
                (ressource_id,),
            )
            matiere_id, niveau_id, titre_cours, type_ressource, contenu_json = cur.fetchone()
            if contenu_json:
                donnees = contenu_json if isinstance(contenu_json, dict) else json.loads(contenu_json)
                texte = donnees.get("texte")
            titre_reinjection = f"{titre_cours} — {LABELS_RESSOURCE.get(type_ressource, type_ressource)}"

    if texte:
        rag.reinjecter_contenu_valide(titre=titre_reinjection, texte=texte,
                                        niveau_id=niveau_id, matiere_id=matiere_id)

    return {"statut": "ok"}
