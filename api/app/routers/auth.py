from fastapi import APIRouter, HTTPException, status

from ..db import get_cursor
from ..security import verifier_mot_de_passe, hacher_mot_de_passe, creer_token_acces
from ..schemas import DemandeConnexion, ReponseToken, InscriptionEnseignant

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


@router.post("/inscription-enseignant", response_model=ReponseToken, status_code=status.HTTP_201_CREATED)
def inscription_enseignant(payload: InscriptionEnseignant):
    """Seul rôle qui peut s'auto-inscrire sans dépendre d'un établissement
    (voir TODO.md point 1) — pense aux enseignants dont l'école n'est pas
    encore cliente de la plateforme. Le compte est créé avec
    etablissement_id = NULL ; il pourra rejoindre un établissement plus
    tard via une invitation (voir routers/invitations.py). Connecte
    automatiquement après inscription, comme le reste de la plateforme ne
    demande jamais une double étape inscription→connexion séparée."""
    with get_cursor(commit=True) as cur:
        cur.execute("SELECT 1 FROM utilisateurs WHERE email = %s", (payload.email,))
        if cur.fetchone() is not None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Cet email est déjà utilisé")

        cur.execute(
            """
            INSERT INTO utilisateurs (etablissement_id, role, email, mot_de_passe_hash, nom, prenom)
            VALUES (NULL, 'enseignant', %s, %s, %s, %s)
            RETURNING id
            """,
            (payload.email, hacher_mot_de_passe(payload.mot_de_passe), payload.nom, payload.prenom),
        )
        utilisateur_id = cur.fetchone()[0]
        cur.execute("INSERT INTO enseignants (utilisateur_id, specialite) VALUES (%s, %s)",
                     (utilisateur_id, payload.specialite))

    return ReponseToken(access_token=creer_token_acces(utilisateur_id))
