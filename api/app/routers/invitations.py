from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from ..db import get_cursor
from ..deps import get_administratif_connecte, get_enseignant_connecte
from ..schemas import AdministratifConnecte, EnseignantConnecte, InvitationEnvoyee, InvitationRecue

router_administration = APIRouter(prefix="/administration/invitations", tags=["invitations"])
router_enseignant = APIRouter(prefix="/enseignant/invitations", tags=["invitations"])


class InvitationParEmail(BaseModel):
    email: str


# ---------------------------------------------------------------------------
# Côté établissement : inviter un enseignant indépendant existant
# ---------------------------------------------------------------------------

@router_administration.post("", response_model=InvitationEnvoyee, status_code=status.HTTP_201_CREATED)
def inviter_enseignant(payload: InvitationParEmail, admin: AdministratifConnecte = Depends(get_administratif_connecte)):
    """Ne fonctionne que pour un enseignant DÉJÀ inscrit sur la plateforme,
    actuellement indépendant (etablissement_id NULL) — voir TODO.md point 1.
    Pas encore de gestion du cas où l'enseignant travaille déjà ailleurs
    (multi-établissement simultané, TODO.md point 2, chantier séparé)."""
    with get_cursor(commit=True) as cur:
        cur.execute(
            "SELECT id, etablissement_id FROM utilisateurs WHERE email = %s AND role = 'enseignant' AND deleted_at IS NULL",
            (payload.email,),
        )
        row = cur.fetchone()
        if row is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                 detail="Aucun enseignant inscrit avec cet email sur la plateforme")
        enseignant_id, etablissement_actuel = row
        if etablissement_actuel is not None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                                 detail="Cet enseignant est déjà rattaché à un établissement")

        cur.execute(
            "SELECT 1 FROM invitations_enseignants WHERE etablissement_id = %s AND enseignant_id = %s AND statut = 'en_attente'",
            (admin.etablissement_id, enseignant_id),
        )
        if cur.fetchone() is not None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                                 detail="Une invitation est déjà en attente pour cet enseignant")

        cur.execute(
            "INSERT INTO invitations_enseignants (etablissement_id, enseignant_id) VALUES (%s, %s) RETURNING id, created_at",
            (admin.etablissement_id, enseignant_id),
        )
        invitation_id, created = cur.fetchone()

    return InvitationEnvoyee(id=str(invitation_id), enseignant_email=payload.email, statut="en_attente", created_at=created)


@router_administration.get("", response_model=list[InvitationEnvoyee])
def lister_invitations_envoyees(admin: AdministratifConnecte = Depends(get_administratif_connecte)):
    with get_cursor() as cur:
        cur.execute(
            """
            SELECT i.id, u.email, i.statut, i.created_at
            FROM invitations_enseignants i
            JOIN utilisateurs u ON u.id = i.enseignant_id
            WHERE i.etablissement_id = %s
            ORDER BY i.created_at DESC
            """,
            (admin.etablissement_id,),
        )
        lignes = cur.fetchall()
    return [InvitationEnvoyee(id=str(id_), enseignant_email=email, statut=s, created_at=c) for id_, email, s, c in lignes]


# ---------------------------------------------------------------------------
# Côté enseignant : consulter/accepter/refuser une invitation reçue
# ---------------------------------------------------------------------------

@router_enseignant.get("", response_model=list[InvitationRecue])
def lister_invitations_recues(enseignant: EnseignantConnecte = Depends(get_enseignant_connecte)):
    with get_cursor() as cur:
        cur.execute(
            """
            SELECT i.id, e.nom, i.statut, i.created_at
            FROM invitations_enseignants i
            JOIN etablissements e ON e.id = i.etablissement_id
            WHERE i.enseignant_id = %s AND i.statut = 'en_attente'
            ORDER BY i.created_at DESC
            """,
            (enseignant.id,),
        )
        lignes = cur.fetchall()
    return [InvitationRecue(id=str(id_), etablissement_nom=nom, statut=s, created_at=c) for id_, nom, s, c in lignes]


@router_enseignant.post("/{invitation_id}/accepter", status_code=status.HTTP_204_NO_CONTENT)
def accepter_invitation(invitation_id: str, enseignant: EnseignantConnecte = Depends(get_enseignant_connecte)):
    if enseignant.etablissement_id is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                             detail="Vous êtes déjà rattaché à un établissement")
    with get_cursor(commit=True) as cur:
        cur.execute(
            "SELECT etablissement_id FROM invitations_enseignants WHERE id = %s AND enseignant_id = %s AND statut = 'en_attente'",
            (invitation_id, enseignant.id),
        )
        row = cur.fetchone()
        if row is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invitation introuvable ou déjà traitée")
        etablissement_id = row[0]

        cur.execute("UPDATE utilisateurs SET etablissement_id = %s WHERE id = %s", (etablissement_id, enseignant.id))
        cur.execute("UPDATE invitations_enseignants SET statut = 'acceptee', traitee_at = now() WHERE id = %s", (invitation_id,))
        # Toute autre invitation encore en attente pour ce même enseignant
        # n'a plus lieu d'être, puisqu'il a rejoint un établissement.
        cur.execute(
            "UPDATE invitations_enseignants SET statut = 'refusee', traitee_at = now() "
            "WHERE enseignant_id = %s AND statut = 'en_attente'",
            (enseignant.id,),
        )


@router_enseignant.post("/{invitation_id}/refuser", status_code=status.HTTP_204_NO_CONTENT)
def refuser_invitation(invitation_id: str, enseignant: EnseignantConnecte = Depends(get_enseignant_connecte)):
    with get_cursor(commit=True) as cur:
        cur.execute(
            "UPDATE invitations_enseignants SET statut = 'refusee', traitee_at = now() "
            "WHERE id = %s AND enseignant_id = %s AND statut = 'en_attente' RETURNING id",
            (invitation_id, enseignant.id),
        )
        if cur.fetchone() is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invitation introuvable ou déjà traitée")
