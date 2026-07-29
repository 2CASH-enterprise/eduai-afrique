from fastapi import APIRouter, Depends

from ..db import get_cursor
from ..deps import get_direction_connecte
from ..schemas import (TableauDeBord, ValidationsEnAttenteParMatiere, ActiviteEnseignant,
                        MoyenneClasse, PaiementEnRetard, DirectionConnecte)

router = APIRouter(prefix="/direction", tags=["direction"])


def _perimetre_etablissement(cur, etablissement_id: str) -> set[tuple[str, str]]:
    """Ensemble des (niveau_id, matiere_id) réellement enseignés dans cet
    établissement, d'après les affectations de TOUS ses enseignants —
    équivalent de _perimetre_enseignant mais agrégé au niveau école. Sert à
    ne compter, dans les exercices en attente (bibliothèque commune, donc
    sans etablissement_id), que ceux qui concernent réellement cette école.
    """
    cur.execute(
        """
        SELECT DISTINCT c.niveau_id, ae.matiere_id
        FROM affectations_enseignants ae
        JOIN classes c ON c.id = ae.classe_id
        JOIN utilisateurs u ON u.id = ae.enseignant_id
        WHERE u.etablissement_id = %s
        """,
        (etablissement_id,),
    )
    return {(str(n), str(m)) for n, m in cur.fetchall()}


@router.get("/tableau-de-bord", response_model=TableauDeBord)
def tableau_de_bord(direction: DirectionConnecte = Depends(get_direction_connecte)):
    etab = direction.etablissement_id
    with get_cursor() as cur:
        cur.execute(
            "SELECT COUNT(*) FROM eleves el JOIN classes c ON c.id = el.classe_id WHERE c.etablissement_id = %s",
            (etab,),
        )
        effectif_eleves = cur.fetchone()[0]

        cur.execute(
            "SELECT COUNT(*) FROM utilisateurs WHERE etablissement_id = %s AND role = 'enseignant' "
            "AND actif = true AND deleted_at IS NULL",
            (etab,),
        )
        effectif_enseignants = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM classes WHERE etablissement_id = %s", (etab,))
        nombre_classes = cur.fetchone()[0]

        cur.execute(
            """
            SELECT AVG(CASE WHEN t.reussi THEN 1.0 ELSE 0.0 END) * 100
            FROM tentatives_exercices t
            JOIN eleves el ON el.utilisateur_id = t.eleve_id
            JOIN classes c ON c.id = el.classe_id
            WHERE c.etablissement_id = %s
            """,
            (etab,),
        )
        taux_reussite = cur.fetchone()[0]

        cur.execute(
            """
            SELECT AVG(n.valeur / n.bareme * 20)
            FROM notes n
            JOIN eleves el ON el.utilisateur_id = n.eleve_id
            JOIN classes c ON c.id = el.classe_id
            WHERE c.etablissement_id = %s
            """,
            (etab,),
        )
        moyenne_generale = cur.fetchone()[0]

        cur.execute(
            """
            SELECT COALESCE(SUM(p.montant_du), 0), COALESCE(SUM(p.montant_paye), 0)
            FROM paiements p
            JOIN eleves el ON el.utilisateur_id = p.eleve_id
            JOIN classes c ON c.id = el.classe_id
            WHERE c.etablissement_id = %s
            """,
            (etab,),
        )
        montant_du, montant_paye = cur.fetchone()

        perimetre = _perimetre_etablissement(cur, etab)
        exercices_en_attente = 0
        if perimetre:
            niveaux_ids, matieres_ids = zip(*perimetre)
            cur.execute(
                """
                SELECT COUNT(*) FROM exercices
                WHERE statut = 'en_validation' AND deleted_at IS NULL
                  AND niveau_id = ANY(%s::uuid[]) AND matiere_id = ANY(%s::uuid[])
                """,
                (list(niveaux_ids), list(matieres_ids)),
            )
            exercices_en_attente = cur.fetchone()[0]

    return TableauDeBord(
        effectif_eleves=effectif_eleves,
        effectif_enseignants=effectif_enseignants,
        nombre_classes=nombre_classes,
        taux_reussite_tentatives_pct=round(float(taux_reussite), 1) if taux_reussite is not None else None,
        moyenne_generale_etablissement=round(float(moyenne_generale), 2) if moyenne_generale is not None else None,
        montant_du_total=float(montant_du),
        montant_paye_total=float(montant_paye),
        exercices_en_attente_validation=exercices_en_attente,
    )


@router.get("/validations-en-attente", response_model=list[ValidationsEnAttenteParMatiere])
def validations_en_attente(direction: DirectionConnecte = Depends(get_direction_connecte)):
    """Vue d'ensemble des exercices en attente de relecture, restreinte aux
    matières/niveaux réellement enseignés dans cet établissement — même
    logique de périmètre que côté enseignant, mais agrégée par école."""
    with get_cursor() as cur:
        perimetre = _perimetre_etablissement(cur, direction.etablissement_id)
        if not perimetre:
            return []

        niveaux_ids, matieres_ids = zip(*perimetre)
        cur.execute(
            """
            SELECT m.nom, n.nom, COUNT(*), MIN(e.created_at)
            FROM exercices e
            JOIN matieres m ON m.id = e.matiere_id
            JOIN niveaux n ON n.id = e.niveau_id
            WHERE e.statut = 'en_validation' AND e.deleted_at IS NULL
              AND e.niveau_id = ANY(%s::uuid[]) AND e.matiere_id = ANY(%s::uuid[])
            GROUP BY m.nom, n.nom
            ORDER BY COUNT(*) DESC
            """,
            (list(niveaux_ids), list(matieres_ids)),
        )
        lignes = cur.fetchall()

    resultats = []
    for matiere, niveau, nombre, plus_ancien in lignes:
        # Double vérification : le ANY() ci-dessus est une union, pas le produit
        # cartésien exact — on ne garde que les couples réellement dans le périmètre.
        resultats.append(ValidationsEnAttenteParMatiere(
            matiere=matiere, niveau=niveau, nombre_en_attente=nombre, plus_ancien=plus_ancien))
    return resultats


@router.get("/enseignants/activite", response_model=list[ActiviteEnseignant])
def activite_enseignants(direction: DirectionConnecte = Depends(get_direction_connecte)):
    with get_cursor() as cur:
        cur.execute(
            """
            SELECT u.nom || ' ' || u.prenom, u.email,
                   COUNT(DISTINCT ae.classe_id),
                   COUNT(DISTINCT CASE WHEN ex.statut = 'valide' THEN ex.id END),
                   COUNT(DISTINCT CASE WHEN ex.statut = 'rejete' THEN ex.id END)
            FROM utilisateurs u
            JOIN enseignants en ON en.utilisateur_id = u.id
            LEFT JOIN affectations_enseignants ae ON ae.enseignant_id = u.id
            LEFT JOIN exercices ex ON ex.valide_par_id = u.id
            WHERE u.etablissement_id = %s AND u.actif = true AND u.deleted_at IS NULL
            GROUP BY u.id, u.nom, u.prenom, u.email
            ORDER BY u.nom
            """,
            (direction.etablissement_id,),
        )
        lignes = cur.fetchall()

    return [ActiviteEnseignant(enseignant=nom, email=email, nombre_classes_affectees=nb_classes,
                                 nombre_exercices_valides=nb_valides, nombre_exercices_rejetes=nb_rejetes)
            for nom, email, nb_classes, nb_valides, nb_rejetes in lignes]


@router.get("/classes/moyennes", response_model=list[MoyenneClasse])
def moyennes_par_classe(direction: DirectionConnecte = Depends(get_direction_connecte)):
    with get_cursor() as cur:
        cur.execute(
            """
            SELECT c.nom, m.nom, AVG(n.valeur / n.bareme * 20), COUNT(n.id)
            FROM notes n
            JOIN eleves el ON el.utilisateur_id = n.eleve_id
            JOIN classes c ON c.id = el.classe_id
            JOIN matieres m ON m.id = n.matiere_id
            WHERE c.etablissement_id = %s
            GROUP BY c.nom, m.nom
            ORDER BY c.nom, m.nom
            """,
            (direction.etablissement_id,),
        )
        lignes = cur.fetchall()

    return [MoyenneClasse(classe=classe, matiere=matiere, moyenne_sur_20=round(float(moy), 2),
                            effectif_note=n)
            for classe, matiere, moy, n in lignes]


@router.get("/paiements/retards", response_model=list[PaiementEnRetard])
def paiements_en_retard(direction: DirectionConnecte = Depends(get_direction_connecte)):
    with get_cursor() as cur:
        cur.execute(
            """
            SELECT u.nom, u.prenom, c.nom, p.montant_du, p.montant_paye, p.date_echeance
            FROM paiements p
            JOIN eleves el ON el.utilisateur_id = p.eleve_id
            JOIN utilisateurs u ON u.id = el.utilisateur_id
            JOIN classes c ON c.id = el.classe_id
            WHERE c.etablissement_id = %s
              AND p.montant_paye < p.montant_du
              AND (p.date_echeance IS NULL OR p.date_echeance < CURRENT_DATE)
            ORDER BY p.date_echeance ASC NULLS LAST
            """,
            (direction.etablissement_id,),
        )
        lignes = cur.fetchall()

    return [PaiementEnRetard(eleve_nom=nom, eleve_prenom=prenom, classe=classe,
                               montant_du=float(du), montant_paye=float(paye),
                               montant_restant=float(du) - float(paye), date_echeance=echeance)
            for nom, prenom, classe, du, paye, echeance in lignes]
