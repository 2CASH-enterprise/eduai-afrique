import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from .db import get_cursor
from .security import decoder_token
from .schemas import EnseignantConnecte, EleveConnecte, DirectionConnecte, AdministratifConnecte, ParentConnecte, AdminPlateformeConnecte

_oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_enseignant_connecte(token: str = Depends(_oauth2_scheme)) -> EnseignantConnecte:
    erreur_auth = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Identifiants invalides ou expirés",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        utilisateur_id = decoder_token(token)
    except jwt.PyJWTError:
        raise erreur_auth

    with get_cursor() as cur:
        cur.execute(
            """
            SELECT u.id, u.nom, u.prenom, u.etablissement_id, COALESCE(et.pays, u.pays)
            FROM utilisateurs u
            JOIN enseignants e ON e.utilisateur_id = u.id
            LEFT JOIN etablissements et ON et.id = u.etablissement_id
            WHERE u.id = %s AND u.role = 'enseignant' AND u.actif = true AND u.deleted_at IS NULL
            """,
            (utilisateur_id,),
        )
        row = cur.fetchone()

    if row is None:
        raise erreur_auth

    return EnseignantConnecte(id=str(row[0]), nom=row[1], prenom=row[2],
                               etablissement_id=str(row[3]) if row[3] else None, pays=row[4])


def get_eleve_connecte(token: str = Depends(_oauth2_scheme)) -> EleveConnecte:
    erreur_auth = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Identifiants invalides ou expirés",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        utilisateur_id = decoder_token(token)
    except jwt.PyJWTError:
        raise erreur_auth

    with get_cursor() as cur:
        cur.execute(
            """
            SELECT u.id, u.nom, u.prenom, el.classe_id, c.niveau_id
            FROM utilisateurs u
            JOIN eleves el ON el.utilisateur_id = u.id
            JOIN classes c ON c.id = el.classe_id
            WHERE u.id = %s AND u.role = 'eleve' AND u.actif = true AND u.deleted_at IS NULL
            """,
            (utilisateur_id,),
        )
        row = cur.fetchone()

    if row is None:
        raise erreur_auth

    return EleveConnecte(id=str(row[0]), nom=row[1], prenom=row[2],
                          classe_id=str(row[3]), niveau_id=str(row[4]))


def get_direction_connecte(token: str = Depends(_oauth2_scheme)) -> DirectionConnecte:
    erreur_auth = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Identifiants invalides ou expirés",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        utilisateur_id = decoder_token(token)
    except jwt.PyJWTError:
        raise erreur_auth

    with get_cursor() as cur:
        cur.execute(
            """
            SELECT id, nom, prenom, etablissement_id FROM utilisateurs
            WHERE id = %s AND role = 'direction' AND actif = true AND deleted_at IS NULL
            """,
            (utilisateur_id,),
        )
        row = cur.fetchone()

    if row is None or row[3] is None:
        raise erreur_auth

    return DirectionConnecte(id=str(row[0]), nom=row[1], prenom=row[2], etablissement_id=str(row[3]))


def get_administratif_connecte(token: str = Depends(_oauth2_scheme)) -> AdministratifConnecte:
    erreur_auth = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Identifiants invalides ou expirés",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        utilisateur_id = decoder_token(token)
    except jwt.PyJWTError:
        raise erreur_auth

    with get_cursor() as cur:
        cur.execute(
            """
            SELECT id, nom, prenom, etablissement_id FROM utilisateurs
            WHERE id = %s AND role = 'administratif' AND actif = true AND deleted_at IS NULL
            """,
            (utilisateur_id,),
        )
        row = cur.fetchone()

    if row is None or row[3] is None:
        raise erreur_auth

    return AdministratifConnecte(id=str(row[0]), nom=row[1], prenom=row[2], etablissement_id=str(row[3]))


def get_admin_plateforme_connecte(token: str = Depends(_oauth2_scheme)) -> AdminPlateformeConnecte:
    erreur_auth = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Identifiants invalides ou expirés",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        utilisateur_id = decoder_token(token)
    except jwt.PyJWTError:
        raise erreur_auth

    with get_cursor() as cur:
        cur.execute(
            """
            SELECT id, nom, prenom FROM utilisateurs
            WHERE id = %s AND role = 'admin_plateforme' AND actif = true AND deleted_at IS NULL
            """,
            (utilisateur_id,),
        )
        row = cur.fetchone()

    if row is None:
        raise erreur_auth

    return AdminPlateformeConnecte(id=str(row[0]), nom=row[1], prenom=row[2])


def get_parent_connecte(token: str = Depends(_oauth2_scheme)) -> ParentConnecte:
    erreur_auth = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Identifiants invalides ou expirés",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        utilisateur_id = decoder_token(token)
    except jwt.PyJWTError:
        raise erreur_auth

    with get_cursor() as cur:
        cur.execute(
            "SELECT id, nom, prenom FROM utilisateurs "
            "WHERE id = %s AND role = 'parent' AND actif = true AND deleted_at IS NULL",
            (utilisateur_id,),
        )
        row = cur.fetchone()

    if row is None:
        raise erreur_auth

    return ParentConnecte(id=str(row[0]), nom=row[1], prenom=row[2])
