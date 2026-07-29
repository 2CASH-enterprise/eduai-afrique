from fastapi import APIRouter, HTTPException, status

from ..db import get_cursor
from ..security import verifier_mot_de_passe, creer_token_acces
from ..schemas import DemandeConnexion, ReponseToken

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=ReponseToken)
def login(payload: DemandeConnexion):
    """Point d'entrée unique pour tous les rôles (enseignant, élève, parent,
    direction...). Le token ne contient que l'identifiant utilisateur — le
    rôle n'y est jamais encodé, pour éviter de faire confiance à une
    information potentiellement obsolète si le rôle change après émission
    du token. Chaque dépendance spécifique à un rôle (get_enseignant_connecte,
    get_eleve_connecte...) revérifie l'appartenance directement en base à
    chaque requête, via sa propre jointure.
    """
    with get_cursor() as cur:
        cur.execute(
            """
            SELECT id, mot_de_passe_hash FROM utilisateurs
            WHERE email = %s AND actif = true AND deleted_at IS NULL
            """,
            (payload.email,),
        )
        row = cur.fetchone()

    # Même message d'erreur que l'email n'existe pas ou que le mot de passe
    # soit faux — ne jamais révéler quel champ était incorrect (évite l'énumération
    # de comptes existants).
    erreur = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Email ou mot de passe incorrect")

    if row is None:
        raise erreur

    utilisateur_id, mot_de_passe_hash = row
    if not verifier_mot_de_passe(payload.mot_de_passe, mot_de_passe_hash):
        raise erreur

    return ReponseToken(access_token=creer_token_acces(utilisateur_id))
