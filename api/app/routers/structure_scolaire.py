from fastapi import APIRouter, Depends, HTTPException, status

from ..db import get_cursor
from ..deps import get_administratif_connecte
from ..schemas import (AdministratifConnecte, AnneeScolaireResume, CreationAnneeScolaire,
                        CycleResume, CreationCycle, NiveauResume, CreationNiveau,
                        ClasseResume, CreationClasse)

router = APIRouter(prefix="/administration", tags=["structure-scolaire"])

# Jusqu'ici, années scolaires/cycles/niveaux/classes étaient toujours créés à
# la main en SQL pour chaque nouvel établissement (voir l'incident du 31/07
# — Collège Vogt bloqué avec un seul niveau "6ème"). Ce module donne enfin à
# chaque établissement la main sur sa propre structure, sans dépendre de nous.


# ---------------------------------------------------------------------------
# Années scolaires
# ---------------------------------------------------------------------------

@router.get("/annees-scolaires", response_model=list[AnneeScolaireResume])
def lister_annees_scolaires(admin: AdministratifConnecte = Depends(get_administratif_connecte)):
    with get_cursor() as cur:
        cur.execute(
            "SELECT id, libelle, date_debut, date_fin, est_active FROM annees_scolaires "
            "WHERE etablissement_id = %s ORDER BY date_debut DESC",
            (admin.etablissement_id,),
        )
        lignes = cur.fetchall()
    return [AnneeScolaireResume(id=str(id_), libelle=lib, date_debut=str(dd), date_fin=str(df), est_active=act)
            for id_, lib, dd, df, act in lignes]


@router.post("/annees-scolaires", response_model=AnneeScolaireResume, status_code=status.HTTP_201_CREATED)
def creer_annee_scolaire(payload: CreationAnneeScolaire, admin: AdministratifConnecte = Depends(get_administratif_connecte)):
    """Nouvelle année scolaire, automatiquement activée — désactive les
    autres. Un établissement n'a jamais qu'une seule année active à la fois
    (c'est elle qui sert de référence pour les classes, notes, bulletins)."""
    with get_cursor(commit=True) as cur:
        cur.execute("UPDATE annees_scolaires SET est_active = false WHERE etablissement_id = %s", (admin.etablissement_id,))
        cur.execute(
            """
            INSERT INTO annees_scolaires (etablissement_id, libelle, date_debut, date_fin, est_active)
            VALUES (%s, %s, %s, %s, true)
            RETURNING id, libelle, date_debut, date_fin, est_active
            """,
            (admin.etablissement_id, payload.libelle, payload.date_debut, payload.date_fin),
        )
        id_, lib, dd, df, act = cur.fetchone()
    return AnneeScolaireResume(id=str(id_), libelle=lib, date_debut=str(dd), date_fin=str(df), est_active=act)


# ---------------------------------------------------------------------------
# Cycles (ex : "Premier Cycle", "Second Cycle")
# ---------------------------------------------------------------------------

@router.get("/cycles", response_model=list[CycleResume])
def lister_cycles(admin: AdministratifConnecte = Depends(get_administratif_connecte)):
    with get_cursor() as cur:
        cur.execute("SELECT id, nom, ordre FROM cycles WHERE etablissement_id = %s ORDER BY ordre", (admin.etablissement_id,))
        lignes = cur.fetchall()
    return [CycleResume(id=str(id_), nom=nom, ordre=ordre) for id_, nom, ordre in lignes]


@router.post("/cycles", response_model=CycleResume, status_code=status.HTTP_201_CREATED)
def creer_cycle(payload: CreationCycle, admin: AdministratifConnecte = Depends(get_administratif_connecte)):
    with get_cursor(commit=True) as cur:
        cur.execute(
            "INSERT INTO cycles (etablissement_id, nom, ordre) VALUES (%s, %s, %s) RETURNING id",
            (admin.etablissement_id, payload.nom, payload.ordre),
        )
        cycle_id = cur.fetchone()[0]
    return CycleResume(id=str(cycle_id), nom=payload.nom, ordre=payload.ordre)


# ---------------------------------------------------------------------------
# Niveaux (ex : "6ème", "5ème"...) — rattachés à un cycle de l'établissement
# ---------------------------------------------------------------------------

@router.get("/niveaux", response_model=list[NiveauResume])
def lister_niveaux(admin: AdministratifConnecte = Depends(get_administratif_connecte)):
    with get_cursor() as cur:
        cur.execute(
            """
            SELECT n.id, n.nom, n.ordre, c.id, c.nom
            FROM niveaux n
            JOIN cycles c ON c.id = n.cycle_id
            WHERE c.etablissement_id = %s
            ORDER BY n.ordre
            """,
            (admin.etablissement_id,),
        )
        lignes = cur.fetchall()
    return [NiveauResume(id=str(id_), nom=nom, ordre=ordre, cycle_id=str(cid), cycle_nom=cnom)
            for id_, nom, ordre, cid, cnom in lignes]


@router.post("/niveaux", response_model=NiveauResume, status_code=status.HTTP_201_CREATED)
def creer_niveau(payload: CreationNiveau, admin: AdministratifConnecte = Depends(get_administratif_connecte)):
    with get_cursor(commit=True) as cur:
        cur.execute("SELECT nom FROM cycles WHERE id = %s AND etablissement_id = %s", (payload.cycle_id, admin.etablissement_id))
        row = cur.fetchone()
        if row is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cycle introuvable dans votre établissement")
        cycle_nom = row[0]

        cur.execute(
            "INSERT INTO niveaux (cycle_id, nom, ordre) VALUES (%s, %s, %s) RETURNING id",
            (payload.cycle_id, payload.nom, payload.ordre),
        )
        niveau_id = cur.fetchone()[0]
    return NiveauResume(id=str(niveau_id), nom=payload.nom, ordre=payload.ordre, cycle_id=payload.cycle_id, cycle_nom=cycle_nom)


# ---------------------------------------------------------------------------
# Classes (ex : "6ème A") — rattachées à un niveau, à l'année scolaire active
# ---------------------------------------------------------------------------

@router.post("/classes", response_model=ClasseResume, status_code=status.HTTP_201_CREATED)
def creer_classe(payload: CreationClasse, admin: AdministratifConnecte = Depends(get_administratif_connecte)):
    with get_cursor(commit=True) as cur:
        cur.execute(
            "SELECT n.nom FROM niveaux n JOIN cycles c ON c.id = n.cycle_id "
            "WHERE n.id = %s AND c.etablissement_id = %s",
            (payload.niveau_id, admin.etablissement_id),
        )
        row = cur.fetchone()
        if row is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Niveau introuvable dans votre établissement")
        niveau_nom = row[0]

        cur.execute(
            "SELECT id FROM annees_scolaires WHERE etablissement_id = %s AND est_active = true LIMIT 1",
            (admin.etablissement_id,),
        )
        row_annee = cur.fetchone()
        if row_annee is None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                                 detail="Aucune année scolaire active — créez-en une d'abord")
        annee_id = row_annee[0]

        cur.execute(
            "INSERT INTO classes (etablissement_id, niveau_id, nom, annee_scolaire_id) VALUES (%s, %s, %s, %s) RETURNING id",
            (admin.etablissement_id, payload.niveau_id, payload.nom, annee_id),
        )
        classe_id = cur.fetchone()[0]
    return ClasseResume(id=str(classe_id), nom=payload.nom, niveau=niveau_nom)
