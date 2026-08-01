from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from ..db import get_cursor
from ..deps import get_administratif_connecte, get_enseignant_connecte
from ..schemas import AdministratifConnecte, EnseignantConnecte, InvitationEnvoyee, InvitationRecue

router_administration = APIRouter(prefix="/administration/invitations", tags=["invitations"])
router_enseignant = APIRouter(prefix="/enseignant/invitations", tags=["invitations"])


class InvitationParEmail(BaseModel):
    email: str
    classe_id: str | None = None
    matiere_id: str | None = None
    # Les deux absents = invitation à REJOINDRE l'établissement (devient son
    # établissement principal, un seul possible à la fois — TODO.md point 1).
    # Les deux renseignés = invitation à ENSEIGNER cette classe précise,
    # sans devenir membre principal — nombre illimité, permet le
    # multi-établissement (TODO.md point 2).


# ---------------------------------------------------------------------------
# Côté établissement : inviter un enseignant existant sur la plateforme
# ---------------------------------------------------------------------------

@router_administration.post("", response_model=InvitationEnvoyee, status_code=status.HTTP_201_CREATED)
def inviter_enseignant(payload: InvitationParEmail, admin: AdministratifConnecte = Depends(get_administratif_connecte)):
    est_affectation = payload.classe_id is not None
    if bool(payload.classe_id) != bool(payload.matiere_id):
        raise HTTPException(status_code=422, detail="classe_id et matiere_id doivent être renseignés ensemble, ou aucun des deux")

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

        classe_nom = matiere_nom = None
        if est_affectation:
            # Invitation à une classe précise : pas d'exclusivité, cet
            # enseignant peut très bien être déjà rattaché ailleurs (ou même
            # ici) — c'est exactement ce qui permet le multi-établissement.
            cur.execute("SELECT nom FROM classes WHERE id = %s AND etablissement_id = %s", (payload.classe_id, admin.etablissement_id))
            row_classe = cur.fetchone()
            if row_classe is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Classe introuvable dans votre établissement")
            classe_nom = row_classe[0]
            cur.execute("SELECT nom FROM matieres WHERE id = %s", (payload.matiere_id,))
            row_matiere = cur.fetchone()
            if row_matiere is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Matière introuvable")
            matiere_nom = row_matiere[0]

            cur.execute(
                "SELECT 1 FROM affectations_enseignants WHERE enseignant_id = %s AND classe_id = %s AND matiere_id = %s",
                (enseignant_id, payload.classe_id, payload.matiere_id),
            )
            if cur.fetchone() is not None:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Cet enseignant enseigne déjà cette classe pour cette matière")

            cur.execute(
                "SELECT 1 FROM invitations_enseignants WHERE enseignant_id = %s AND classe_id = %s AND matiere_id = %s AND statut = 'en_attente'",
                (enseignant_id, payload.classe_id, payload.matiere_id),
            )
        else:
            # Invitation à rejoindre l'établissement : exclusivité, comme avant.
            if etablissement_actuel is not None:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                                     detail="Cet enseignant est déjà rattaché à un établissement")
            cur.execute(
                "SELECT 1 FROM invitations_enseignants WHERE etablissement_id = %s AND enseignant_id = %s "
                "AND classe_id IS NULL AND statut = 'en_attente'",
                (admin.etablissement_id, enseignant_id),
            )
        if cur.fetchone() is not None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Une invitation est déjà en attente pour cet enseignant")

        cur.execute(
            "INSERT INTO invitations_enseignants (etablissement_id, enseignant_id, classe_id, matiere_id) "
            "VALUES (%s, %s, %s, %s) RETURNING id, created_at",
            (admin.etablissement_id, enseignant_id, payload.classe_id, payload.matiere_id),
        )
        invitation_id, created = cur.fetchone()

    return InvitationEnvoyee(id=str(invitation_id), enseignant_email=payload.email,
                               classe_nom=classe_nom, matiere_nom=matiere_nom, statut="en_attente", created_at=created)


@router_administration.get("", response_model=list[InvitationEnvoyee])
def lister_invitations_envoyees(admin: AdministratifConnecte = Depends(get_administratif_connecte)):
    with get_cursor() as cur:
        cur.execute(
            """
            SELECT i.id, u.email, c.nom, m.nom, i.statut, i.created_at
            FROM invitations_enseignants i
            JOIN utilisateurs u ON u.id = i.enseignant_id
            LEFT JOIN classes c ON c.id = i.classe_id
            LEFT JOIN matieres m ON m.id = i.matiere_id
            WHERE i.etablissement_id = %s
            ORDER BY i.created_at DESC
            """,
            (admin.etablissement_id,),
        )
        lignes = cur.fetchall()
    return [InvitationEnvoyee(id=str(id_), enseignant_email=email, classe_nom=cn, matiere_nom=mn, statut=s, created_at=c)
            for id_, email, cn, mn, s, c in lignes]


# ---------------------------------------------------------------------------
# Côté enseignant : consulter/accepter/refuser une invitation reçue
# ---------------------------------------------------------------------------

@router_enseignant.get("", response_model=list[InvitationRecue])
def lister_invitations_recues(enseignant: EnseignantConnecte = Depends(get_enseignant_connecte)):
    with get_cursor() as cur:
        cur.execute(
            """
            SELECT i.id, e.nom, c.nom, m.nom, i.statut, i.created_at
            FROM invitations_enseignants i
            JOIN etablissements e ON e.id = i.etablissement_id
            LEFT JOIN classes c ON c.id = i.classe_id
            LEFT JOIN matieres m ON m.id = i.matiere_id
            WHERE i.enseignant_id = %s AND i.statut = 'en_attente'
            ORDER BY i.created_at DESC
            """,
            (enseignant.id,),
        )
        lignes = cur.fetchall()
    return [InvitationRecue(id=str(id_), etablissement_nom=nom, classe_nom=cn, matiere_nom=mn, statut=s, created_at=c)
            for id_, nom, cn, mn, s, c in lignes]


@router_enseignant.post("/{invitation_id}/accepter", status_code=status.HTTP_204_NO_CONTENT)
def accepter_invitation(invitation_id: str, enseignant: EnseignantConnecte = Depends(get_enseignant_connecte)):
    with get_cursor(commit=True) as cur:
        cur.execute(
            "SELECT etablissement_id, classe_id, matiere_id FROM invitations_enseignants "
            "WHERE id = %s AND enseignant_id = %s AND statut = 'en_attente'",
            (invitation_id, enseignant.id),
        )
        row = cur.fetchone()
        if row is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invitation introuvable ou déjà traitée")
        etablissement_id, classe_id, matiere_id = row

        if classe_id is not None:
            # Invitation à une classe précise : crée l'affectation, ne touche
            # jamais l'établissement principal — c'est ce qui permet d'en
            # accepter plusieurs, dans plusieurs établissements différents.
            cur.execute(
                "INSERT INTO affectations_enseignants (enseignant_id, classe_id, matiere_id) VALUES (%s, %s, %s) "
                "ON CONFLICT DO NOTHING",
                (enseignant.id, classe_id, matiere_id),
            )
            cur.execute("UPDATE invitations_enseignants SET statut = 'acceptee', traitee_at = now() WHERE id = %s", (invitation_id,))
        else:
            # Invitation à rejoindre : comportement inchangé du point 1.
            if enseignant.etablissement_id is not None:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                                     detail="Vous êtes déjà rattaché à un établissement")
            cur.execute("UPDATE utilisateurs SET etablissement_id = %s WHERE id = %s", (etablissement_id, enseignant.id))
            cur.execute("UPDATE invitations_enseignants SET statut = 'acceptee', traitee_at = now() WHERE id = %s", (invitation_id,))
            # Seules les AUTRES invitations à REJOINDRE deviennent caduques —
            # les invitations à enseigner une classe précise restent valables,
            # elles ne dépendent pas de l'établissement principal.
            cur.execute(
                "UPDATE invitations_enseignants SET statut = 'refusee', traitee_at = now() "
                "WHERE enseignant_id = %s AND statut = 'en_attente' AND classe_id IS NULL",
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
