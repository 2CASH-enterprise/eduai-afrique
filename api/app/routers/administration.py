import csv
import io
import secrets

import openpyxl
import psycopg2
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from ..db import get_cursor
from ..deps import get_administratif_connecte
from ..security import hacher_mot_de_passe
from ..schemas import (CreationEleve, CreationEnseignant, CreationParent, CompteCree, UtilisateurResume,
                        GenerationBulletins, BulletinGenere, DiffusionNotification,
                        DiffusionResultat, EncaissementPaiement, PaiementMisAJour,
                        ClasseResume, MatiereResume, PaiementAdmin,
                        RapportImport, ResultatLigneImport,
                        AdministratifConnecte)

router = APIRouter(prefix="/administration", tags=["administration"])


def _generer_mot_de_passe_provisoire() -> str:
    # 10 caractères alphanumériques lisibles — assez d'entropie pour un mot de
    # passe provisoire que l'utilisateur devra changer à sa première connexion
    # (règle à faire respecter côté frontend/produit, pas encore dans cette API).
    return secrets.token_urlsafe(8)


def _verifier_classe_dans_etablissement(cur, classe_id: str, etablissement_id: str) -> None:
    cur.execute("SELECT 1 FROM classes WHERE id = %s AND etablissement_id = %s", (classe_id, etablissement_id))
    if cur.fetchone() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                             detail="Classe introuvable dans votre établissement")


def _lire_fichier_tabulaire(upload_file: UploadFile) -> list[dict]:
    """Lit un CSV ou un Excel (.xlsx) et renvoie une liste de dicts, une par
    ligne, avec des clés normalisées (minuscules, espaces retirés) — pour
    que les en-têtes 'Email', 'email', ' Email ' soient tous acceptés.
    """
    contenu = upload_file.file.read()
    nom_fichier = (upload_file.filename or "").lower()

    if nom_fichier.endswith(".xlsx"):
        classeur = openpyxl.load_workbook(io.BytesIO(contenu), read_only=True, data_only=True)
        feuille = classeur.active
        lignes = list(feuille.iter_rows(values_only=True))
        if not lignes:
            return []
        entetes = [str(h).strip().lower() if h is not None else "" for h in lignes[0]]
        resultats = []
        for ligne in lignes[1:]:
            if all(v is None for v in ligne):
                continue  # ligne vide, courant en fin de fichier Excel
            resultats.append({entetes[i]: (str(ligne[i]).strip() if ligne[i] is not None else "")
                               for i in range(len(entetes))})
        return resultats

    # CSV par défaut — utf-8-sig gère le BOM ajouté par Excel à l'export CSV
    texte = contenu.decode("utf-8-sig")
    lecteur = csv.DictReader(io.StringIO(texte))
    return [{(k or "").strip().lower(): (v or "").strip() for k, v in ligne.items()} for ligne in lecteur]


def _resoudre_classe_par_nom(cur, etablissement_id: str, nom_classe: str) -> str:
    cur.execute("SELECT id FROM classes WHERE etablissement_id = %s AND nom = %s", (etablissement_id, nom_classe))
    row = cur.fetchone()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Classe « {nom_classe} » introuvable")
    return row[0]


def _resoudre_matiere_par_nom(cur, nom_matiere: str) -> str:
    cur.execute("SELECT id FROM matieres WHERE nom = %s", (nom_matiere,))
    row = cur.fetchone()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Matière « {nom_matiere} » introuvable")
    return row[0]


def _parser_affectations(cur, etablissement_id: str, texte: str) -> list[tuple[str, str]]:
    """Format attendu dans la colonne 'affectations' : 'Classe:Matière' pour
    chaque affectation, séparées par ';'. Ex : '6ème A:Mathématiques;6ème B:Mathématiques'.
    Colonne vide ou absente = aucune affectation (à ajouter plus tard)."""
    if not texte:
        return []
    resultat = []
    for paire in (p.strip() for p in texte.split(";") if p.strip()):
        if ":" not in paire:
            raise HTTPException(status_code=422,
                                 detail=f"Format d'affectation invalide : « {paire} » (attendu Classe:Matière)")
        nom_classe, nom_matiere = (x.strip() for x in paire.split(":", 1))
        resultat.append((_resoudre_classe_par_nom(cur, etablissement_id, nom_classe),
                          _resoudre_matiere_par_nom(cur, nom_matiere)))
    return resultat


def _creer_compte_eleve_core(cur, etablissement_id: str, email: str, nom: str, prenom: str,
                               classe_id: str, matricule: str | None) -> tuple[str, str]:
    """Cœur de la création d'un compte élève, réutilisé par l'endpoint
    unitaire et par l'import en masse — pour ne jamais avoir deux versions
    de cette logique qui pourraient diverger silencieusement."""
    mot_de_passe = _generer_mot_de_passe_provisoire()
    cur.execute(
        """
        INSERT INTO utilisateurs (etablissement_id, role, email, mot_de_passe_hash, nom, prenom)
        VALUES (%s, 'eleve', %s, %s, %s, %s) RETURNING id
        """,
        (etablissement_id, email, hacher_mot_de_passe(mot_de_passe), nom, prenom),
    )
    utilisateur_id = cur.fetchone()[0]
    cur.execute(
        "INSERT INTO eleves (utilisateur_id, classe_id, matricule) VALUES (%s, %s, %s)",
        (utilisateur_id, classe_id, matricule or None),
    )
    return str(utilisateur_id), mot_de_passe


def _creer_compte_enseignant_core(cur, etablissement_id: str, email: str, nom: str, prenom: str,
                                    specialite: str | None, affectations: list[tuple[str, str]]) -> tuple[str, str]:
    mot_de_passe = _generer_mot_de_passe_provisoire()
    cur.execute(
        """
        INSERT INTO utilisateurs (etablissement_id, role, email, mot_de_passe_hash, nom, prenom)
        VALUES (%s, 'enseignant', %s, %s, %s, %s) RETURNING id
        """,
        (etablissement_id, email, hacher_mot_de_passe(mot_de_passe), nom, prenom),
    )
    utilisateur_id = cur.fetchone()[0]
    cur.execute("INSERT INTO enseignants (utilisateur_id, specialite) VALUES (%s, %s)",
                (utilisateur_id, specialite or None))
    for classe_id, matiere_id in affectations:
        cur.execute(
            "INSERT INTO affectations_enseignants (enseignant_id, classe_id, matiere_id) "
            "VALUES (%s, %s, %s) ON CONFLICT DO NOTHING",
            (utilisateur_id, classe_id, matiere_id),
        )
    return str(utilisateur_id), mot_de_passe


@router.post("/eleves", response_model=CompteCree, status_code=status.HTTP_201_CREATED)
def creer_eleve(
    payload: CreationEleve,
    admin: AdministratifConnecte = Depends(get_administratif_connecte),
):
    with get_cursor(commit=True) as cur:
        _verifier_classe_dans_etablissement(cur, payload.classe_id, admin.etablissement_id)
        try:
            utilisateur_id, mot_de_passe = _creer_compte_eleve_core(
                cur, admin.etablissement_id, payload.email, payload.nom, payload.prenom,
                payload.classe_id, payload.matricule)
        except psycopg2.errors.UniqueViolation:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                                 detail="Un compte existe déjà avec cet email ou ce matricule")

    return CompteCree(id=utilisateur_id, email=payload.email, mot_de_passe_provisoire=mot_de_passe)


@router.post("/enseignants", response_model=CompteCree, status_code=status.HTTP_201_CREATED)
def creer_enseignant(
    payload: CreationEnseignant,
    admin: AdministratifConnecte = Depends(get_administratif_connecte),
):
    with get_cursor(commit=True) as cur:
        for affectation in payload.affectations:
            _verifier_classe_dans_etablissement(cur, affectation["classe_id"], admin.etablissement_id)

        try:
            utilisateur_id, mot_de_passe = _creer_compte_enseignant_core(
                cur, admin.etablissement_id, payload.email, payload.nom, payload.prenom, payload.specialite,
                [(a["classe_id"], a["matiere_id"]) for a in payload.affectations])
        except psycopg2.errors.UniqueViolation:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                                 detail="Un compte existe déjà avec cet email")

    return CompteCree(id=utilisateur_id, email=payload.email, mot_de_passe_provisoire=mot_de_passe)


@router.post("/parents", response_model=CompteCree, status_code=status.HTTP_201_CREATED)
def creer_parent(
    payload: CreationParent,
    admin: AdministratifConnecte = Depends(get_administratif_connecte),
):
    """Crée un compte parent et le lie à un ou plusieurs élèves existants.
    Chaque élève doit appartenir au même établissement que l'admin — sinon
    un admin pourrait lier un parent à un enfant d'une autre école."""
    with get_cursor(commit=True) as cur:
        for eleve_id in payload.eleve_ids:
            cur.execute(
                """
                SELECT 1 FROM eleves el
                JOIN classes c ON c.id = el.classe_id
                WHERE el.utilisateur_id = %s AND c.etablissement_id = %s
                """,
                (eleve_id, admin.etablissement_id),
            )
            if cur.fetchone() is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                     detail=f"Élève {eleve_id} introuvable dans votre établissement")

        mot_de_passe = _generer_mot_de_passe_provisoire()
        try:
            cur.execute(
                """
                INSERT INTO utilisateurs (etablissement_id, role, email, mot_de_passe_hash, nom, prenom)
                VALUES (%s, 'parent', %s, %s, %s, %s) RETURNING id
                """,
                (admin.etablissement_id, payload.email, hacher_mot_de_passe(mot_de_passe),
                 payload.nom, payload.prenom),
            )
            utilisateur_id = cur.fetchone()[0]
        except psycopg2.errors.UniqueViolation:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                                 detail="Un compte existe déjà avec cet email")

        for eleve_id in payload.eleve_ids:
            cur.execute(
                "INSERT INTO parents_eleves (parent_id, eleve_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                (utilisateur_id, eleve_id),
            )

    return CompteCree(id=str(utilisateur_id), email=payload.email, mot_de_passe_provisoire=mot_de_passe)


@router.get("/utilisateurs", response_model=list[UtilisateurResume])
def lister_utilisateurs(
    admin: AdministratifConnecte = Depends(get_administratif_connecte),
    role: str | None = None,
    classe_id: str | None = None,
):
    with get_cursor() as cur:
        cur.execute(
            """
            SELECT u.id, u.nom, u.prenom, u.email, u.role, u.actif, c.nom
            FROM utilisateurs u
            LEFT JOIN eleves el ON el.utilisateur_id = u.id
            LEFT JOIN classes c ON c.id = el.classe_id
            WHERE u.etablissement_id = %s AND u.deleted_at IS NULL
              AND (%s::text IS NULL OR u.role = %s)
              AND (%s::uuid IS NULL OR el.classe_id = %s::uuid)
            ORDER BY u.nom, u.prenom
            """,
            (admin.etablissement_id, role, role, classe_id, classe_id),
        )
        lignes = cur.fetchall()

    return [UtilisateurResume(id=str(id_), nom=nom, prenom=prenom, email=email, role=role_,
                                actif=actif, classe=classe)
            for id_, nom, prenom, email, role_, actif, classe in lignes]


@router.patch("/utilisateurs/{utilisateur_id}/desactiver")
def desactiver_utilisateur(
    utilisateur_id: str,
    admin: AdministratifConnecte = Depends(get_administratif_connecte),
):
    """Désactivation (actif=false), jamais de suppression physique — on garde
    l'historique (notes, paiements, tentatives...) qui référence cet utilisateur."""
    with get_cursor(commit=True) as cur:
        cur.execute(
            "UPDATE utilisateurs SET actif = false WHERE id = %s AND etablissement_id = %s RETURNING id",
            (utilisateur_id, admin.etablissement_id),
        )
        if cur.fetchone() is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                 detail="Utilisateur introuvable dans votre établissement")
    return {"statut": "desactive"}


@router.post("/bulletins/generer", response_model=list[BulletinGenere])
def generer_bulletins(
    payload: GenerationBulletins,
    admin: AdministratifConnecte = Depends(get_administratif_connecte),
):
    """Calcule la moyenne générale (moyenne des moyennes par matière) et le
    rang de chaque élève de la classe pour le trimestre donné, puis
    upsert dans `bulletins`. Un élève sans aucune note reçoit moyenne=NULL,
    rang=NULL plutôt que d'être exclu silencieusement de la liste."""
    with get_cursor(commit=True) as cur:
        _verifier_classe_dans_etablissement(cur, payload.classe_id, admin.etablissement_id)

        cur.execute(
            "SELECT id FROM annees_scolaires WHERE etablissement_id = %s AND est_active = true LIMIT 1",
            (admin.etablissement_id,),
        )
        annee = cur.fetchone()
        if annee is None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                                 detail="Aucune année scolaire active pour cet établissement")
        annee_scolaire_id = annee[0]

        cur.execute(
            """
            SELECT el.utilisateur_id, u.nom || ' ' || u.prenom,
                   AVG(v.moyenne_sur_20)
            FROM eleves el
            JOIN utilisateurs u ON u.id = el.utilisateur_id
            LEFT JOIN vue_moyennes_eleve v ON v.eleve_id = el.utilisateur_id
                AND v.trimestre = %s AND v.annee_scolaire_id = %s
            WHERE el.classe_id = %s
            GROUP BY el.utilisateur_id, u.nom, u.prenom
            """,
            (payload.trimestre, annee_scolaire_id, payload.classe_id),
        )
        eleves = cur.fetchall()  # (eleve_id, nom_complet, moyenne_generale ou None)

        # Classement : seuls les élèves avec une moyenne sont rangés, par ordre décroissant
        avec_moyenne = sorted([e for e in eleves if e[2] is not None], key=lambda e: -e[2])
        rangs = {eleve_id: i + 1 for i, (eleve_id, _, _) in enumerate(avec_moyenne)}

        resultats = []
        for eleve_id, nom_complet, moyenne in eleves:
            rang = rangs.get(eleve_id)
            cur.execute(
                """
                INSERT INTO bulletins (eleve_id, annee_scolaire_id, trimestre, moyenne_generale, rang_classe, genere_le)
                VALUES (%s, %s, %s, %s, %s, now())
                ON CONFLICT (eleve_id, annee_scolaire_id, trimestre)
                DO UPDATE SET moyenne_generale = EXCLUDED.moyenne_generale,
                              rang_classe = EXCLUDED.rang_classe, genere_le = now()
                """,
                (eleve_id, annee_scolaire_id, payload.trimestre,
                 round(float(moyenne), 2) if moyenne is not None else None, rang),
            )
            resultats.append(BulletinGenere(
                eleve_id=str(eleve_id), eleve_nom=nom_complet,
                moyenne_generale=round(float(moyenne), 2) if moyenne is not None else None,
                rang_classe=rang,
            ))

    return sorted(resultats, key=lambda b: (b.rang_classe is None, b.rang_classe or 0))


@router.post("/notifications/diffuser", response_model=DiffusionResultat)
def diffuser_notification(
    payload: DiffusionNotification,
    admin: AdministratifConnecte = Depends(get_administratif_connecte),
):
    if not payload.classe_id and not payload.utilisateur_id:
        raise HTTPException(status_code=422, detail="Fournir classe_id ou utilisateur_id")

    with get_cursor(commit=True) as cur:
        destinataires: set[str] = set()

        if payload.utilisateur_id:
            cur.execute(
                "SELECT id FROM utilisateurs WHERE id = %s AND etablissement_id = %s",
                (payload.utilisateur_id, admin.etablissement_id),
            )
            row = cur.fetchone()
            if row is None:
                raise HTTPException(status_code=404, detail="Utilisateur introuvable dans votre établissement")
            destinataires.add(str(row[0]))

        if payload.classe_id:
            _verifier_classe_dans_etablissement(cur, payload.classe_id, admin.etablissement_id)
            cur.execute("SELECT utilisateur_id FROM eleves WHERE classe_id = %s", (payload.classe_id,))
            ids_eleves = [row[0] for row in cur.fetchall()]
            destinataires.update(str(i) for i in ids_eleves)

            if payload.inclure_parents and ids_eleves:
                cur.execute(
                    "SELECT DISTINCT parent_id FROM parents_eleves WHERE eleve_id = ANY(%s::uuid[])",
                    (ids_eleves,),
                )
                destinataires.update(str(row[0]) for row in cur.fetchall())

        for destinataire_id in destinataires:
            cur.execute(
                """
                INSERT INTO notifications (utilisateur_id, titre, message, type_notification)
                VALUES (%s, %s, %s, %s)
                """,
                (destinataire_id, payload.titre, payload.message, payload.type_notification),
            )

    return DiffusionResultat(nombre_notifications_envoyees=len(destinataires))


@router.post("/paiements/{paiement_id}/encaisser", response_model=PaiementMisAJour)
def encaisser_paiement(
    paiement_id: str,
    payload: EncaissementPaiement,
    admin: AdministratifConnecte = Depends(get_administratif_connecte),
):
    with get_cursor(commit=True) as cur:
        cur.execute(
            """
            SELECT p.montant_du, p.montant_paye
            FROM paiements p
            JOIN eleves el ON el.utilisateur_id = p.eleve_id
            JOIN classes c ON c.id = el.classe_id
            WHERE p.id = %s AND c.etablissement_id = %s
            """,
            (paiement_id, admin.etablissement_id),
        )
        row = cur.fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Paiement introuvable dans votre établissement")

        montant_du, montant_paye_actuel = row
        nouveau_montant_paye = float(montant_paye_actuel) + payload.montant
        if nouveau_montant_paye >= float(montant_du):
            statut = "complet"
        elif nouveau_montant_paye > 0:
            statut = "partiel"
        else:
            statut = "en_attente"

        cur.execute(
            "UPDATE paiements SET montant_paye = %s, statut = %s WHERE id = %s "
            "RETURNING id, montant_du, montant_paye, statut",
            (nouveau_montant_paye, statut, paiement_id),
        )
        resultat = cur.fetchone()

    return PaiementMisAJour(id=str(resultat[0]), montant_du=float(resultat[1]),
                              montant_paye=float(resultat[2]), statut=resultat[3])


@router.get("/classes", response_model=list[ClasseResume])
def lister_classes(admin: AdministratifConnecte = Depends(get_administratif_connecte)):
    with get_cursor() as cur:
        cur.execute(
            """
            SELECT c.id, c.nom, n.nom
            FROM classes c JOIN niveaux n ON n.id = c.niveau_id
            WHERE c.etablissement_id = %s
            ORDER BY n.ordre, c.nom
            """,
            (admin.etablissement_id,),
        )
        lignes = cur.fetchall()
    return [ClasseResume(id=str(id_), nom=nom, niveau=niveau) for id_, nom, niveau in lignes]


@router.get("/matieres", response_model=list[MatiereResume])
def lister_matieres(admin: AdministratifConnecte = Depends(get_administratif_connecte)):
    # Référentiel global (pas d'etablissement_id sur `matieres`) — commun à tous.
    with get_cursor() as cur:
        cur.execute("SELECT id, nom FROM matieres ORDER BY nom")
        lignes = cur.fetchall()
    return [MatiereResume(id=str(id_), nom=nom) for id_, nom in lignes]


@router.get("/paiements", response_model=list[PaiementAdmin])
def lister_paiements(
    admin: AdministratifConnecte = Depends(get_administratif_connecte),
    statut: str | None = None,
):
    with get_cursor() as cur:
        cur.execute(
            """
            SELECT p.id, u.nom, u.prenom, c.nom, p.montant_du, p.montant_paye, p.statut, p.date_echeance
            FROM paiements p
            JOIN eleves el ON el.utilisateur_id = p.eleve_id
            JOIN utilisateurs u ON u.id = el.utilisateur_id
            JOIN classes c ON c.id = el.classe_id
            WHERE c.etablissement_id = %s
              AND (%s::text IS NULL OR p.statut = %s)
            ORDER BY p.date_echeance ASC NULLS LAST
            """,
            (admin.etablissement_id, statut, statut),
        )
        lignes = cur.fetchall()
    return [PaiementAdmin(id=str(id_), eleve_nom=nom, eleve_prenom=prenom, classe=classe,
                            montant_du=float(du), montant_paye=float(paye), statut=st,
                            date_echeance=str(echeance) if echeance else None)
            for id_, nom, prenom, classe, du, paye, st, echeance in lignes]


@router.post("/eleves/import", response_model=RapportImport)
async def importer_eleves(
    fichier: UploadFile = File(...),
    admin: AdministratifConnecte = Depends(get_administratif_connecte),
):
    """Import en masse depuis un CSV ou Excel. Colonnes attendues :
    email, nom, prenom, classe, matricule (matricule optionnel).
    Une transaction PAR LIGNE — une ligne en erreur (email en doublon, classe
    introuvable...) n'empêche jamais les autres lignes d'être traitées.
    """
    lignes = _lire_fichier_tabulaire(fichier)
    resultats: list[ResultatLigneImport] = []

    for i, ligne in enumerate(lignes):
        numero_ligne = i + 2  # +1 pour l'en-tête, +1 pour l'indexation à 1
        email = ligne.get("email", "").strip()
        try:
            if not email or not ligne.get("nom") or not ligne.get("prenom") or not ligne.get("classe"):
                raise HTTPException(status_code=422, detail="Colonnes obligatoires manquantes (email, nom, prenom, classe)")

            with get_cursor(commit=True) as cur:
                classe_id = _resoudre_classe_par_nom(cur, admin.etablissement_id, ligne["classe"])
                utilisateur_id, mot_de_passe = _creer_compte_eleve_core(
                    cur, admin.etablissement_id, email, ligne["nom"], ligne["prenom"],
                    classe_id, ligne.get("matricule"))

            resultats.append(ResultatLigneImport(ligne=numero_ligne, email=email, statut="cree",
                                                   mot_de_passe_provisoire=mot_de_passe))
        except HTTPException as e:
            resultats.append(ResultatLigneImport(ligne=numero_ligne, email=email or None, statut="erreur",
                                                   erreur=str(e.detail)))
        except psycopg2.errors.UniqueViolation:
            resultats.append(ResultatLigneImport(ligne=numero_ligne, email=email or None, statut="erreur",
                                                   erreur="Email ou matricule déjà utilisé"))
        except Exception as e:
            resultats.append(ResultatLigneImport(ligne=numero_ligne, email=email or None, statut="erreur",
                                                   erreur=f"Erreur inattendue : {e}"))

    crees = sum(1 for r in resultats if r.statut == "cree")
    return RapportImport(total_lignes=len(lignes), nombre_crees=crees,
                          nombre_erreurs=len(lignes) - crees, resultats=resultats)


@router.post("/enseignants/import", response_model=RapportImport)
async def importer_enseignants(
    fichier: UploadFile = File(...),
    admin: AdministratifConnecte = Depends(get_administratif_connecte),
):
    """Colonnes attendues : email, nom, prenom, specialite (optionnel),
    affectations (optionnel, format 'Classe:Matière;Classe:Matière')."""
    lignes = _lire_fichier_tabulaire(fichier)
    resultats: list[ResultatLigneImport] = []

    for i, ligne in enumerate(lignes):
        numero_ligne = i + 2
        email = ligne.get("email", "").strip()
        try:
            if not email or not ligne.get("nom") or not ligne.get("prenom"):
                raise HTTPException(status_code=422, detail="Colonnes obligatoires manquantes (email, nom, prenom)")

            with get_cursor(commit=True) as cur:
                affectations = _parser_affectations(cur, admin.etablissement_id, ligne.get("affectations", ""))
                utilisateur_id, mot_de_passe = _creer_compte_enseignant_core(
                    cur, admin.etablissement_id, email, ligne["nom"], ligne["prenom"],
                    ligne.get("specialite"), affectations)

            resultats.append(ResultatLigneImport(ligne=numero_ligne, email=email, statut="cree",
                                                   mot_de_passe_provisoire=mot_de_passe))
        except HTTPException as e:
            resultats.append(ResultatLigneImport(ligne=numero_ligne, email=email or None, statut="erreur",
                                                   erreur=str(e.detail)))
        except psycopg2.errors.UniqueViolation:
            resultats.append(ResultatLigneImport(ligne=numero_ligne, email=email or None, statut="erreur",
                                                   erreur="Email déjà utilisé"))
        except Exception as e:
            resultats.append(ResultatLigneImport(ligne=numero_ligne, email=email or None, statut="erreur",
                                                   erreur=f"Erreur inattendue : {e}"))

    crees = sum(1 for r in resultats if r.statut == "cree")
    return RapportImport(total_lignes=len(lignes), nombre_crees=crees,
                          nombre_erreurs=len(lignes) - crees, resultats=resultats)
