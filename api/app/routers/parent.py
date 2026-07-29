from fastapi import APIRouter, Depends, HTTPException, status

from ..db import get_cursor
from ..deps import get_parent_connecte
from ..schemas import (EnfantResume, TableauDeBordEnfant, BulletinParent, AbsenceParent,
                        PaiementParent, DevoirParent, NotificationEleve, ParentConnecte)

router = APIRouter(prefix="/parent", tags=["parent"])


def _verifier_enfant_du_parent(cur, parent_id: str, eleve_id: str) -> None:
    """Vérifie que cet élève est bien un enfant déclaré de ce parent, via la
    table parents_eleves. 404 plutôt que 403 — comme pour l'auth, on ne
    confirme pas l'existence d'un élève qui n'est pas le sien.
    """
    cur.execute(
        "SELECT 1 FROM parents_eleves WHERE parent_id = %s AND eleve_id = %s",
        (parent_id, eleve_id),
    )
    if cur.fetchone() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                             detail="Aucun enfant correspondant à cet identifiant pour ce compte parent")


@router.get("/enfants", response_model=list[EnfantResume])
def lister_enfants(parent: ParentConnecte = Depends(get_parent_connecte)):
    with get_cursor() as cur:
        cur.execute(
            """
            SELECT u.id, u.nom, u.prenom, c.nom, n.nom, et.nom
            FROM parents_eleves pe
            JOIN eleves el ON el.utilisateur_id = pe.eleve_id
            JOIN utilisateurs u ON u.id = el.utilisateur_id
            JOIN classes c ON c.id = el.classe_id
            JOIN niveaux n ON n.id = c.niveau_id
            JOIN etablissements et ON et.id = c.etablissement_id
            WHERE pe.parent_id = %s
            ORDER BY u.nom, u.prenom
            """,
            (parent.id,),
        )
        lignes = cur.fetchall()

    return [EnfantResume(eleve_id=str(id_), nom=nom, prenom=prenom, classe=classe,
                           niveau=niveau, etablissement=etab)
            for id_, nom, prenom, classe, niveau, etab in lignes]


@router.get("/enfants/{eleve_id}/tableau-de-bord", response_model=TableauDeBordEnfant)
def tableau_de_bord_enfant(
    eleve_id: str,
    parent: ParentConnecte = Depends(get_parent_connecte),
):
    with get_cursor() as cur:
        _verifier_enfant_du_parent(cur, parent.id, eleve_id)

        cur.execute(
            "SELECT AVG(moyenne_sur_20) FROM vue_moyennes_eleve WHERE eleve_id = %s",
            (eleve_id,),
        )
        moyenne_generale = cur.fetchone()[0]

        cur.execute(
            "SELECT COUNT(*) FILTER (WHERE type_absence = 'absence'), "
            "COUNT(*) FILTER (WHERE type_absence = 'retard') FROM absences WHERE eleve_id = %s",
            (eleve_id,),
        )
        nb_absences, nb_retards = cur.fetchone()

        cur.execute(
            """
            SELECT m.nom, n.valeur, n.bareme, n.type_evaluation, n.created_at
            FROM notes n JOIN matieres m ON m.id = n.matiere_id
            WHERE n.eleve_id = %s ORDER BY n.created_at DESC LIMIT 5
            """,
            (eleve_id,),
        )
        dernieres_notes = [
            {"matiere": m, "valeur": float(v), "bareme": float(b), "type": t, "date": d.isoformat()}
            for m, v, b, t, d in cur.fetchall()
        ]

    return TableauDeBordEnfant(
        moyenne_generale=round(float(moyenne_generale), 2) if moyenne_generale is not None else None,
        nombre_absences=nb_absences, nombre_retards=nb_retards, dernieres_notes=dernieres_notes,
    )


@router.get("/enfants/{eleve_id}/bulletins", response_model=list[BulletinParent])
def bulletins_enfant(
    eleve_id: str,
    parent: ParentConnecte = Depends(get_parent_connecte),
):
    with get_cursor() as cur:
        _verifier_enfant_du_parent(cur, parent.id, eleve_id)
        cur.execute(
            """
            SELECT trimestre, moyenne_generale, rang_classe, fichier_pdf_url, genere_le
            FROM bulletins WHERE eleve_id = %s ORDER BY trimestre
            """,
            (eleve_id,),
        )
        lignes = cur.fetchall()

    return [BulletinParent(trimestre=t, moyenne_generale=float(m) if m is not None else None,
                             rang_classe=r, fichier_pdf_url=url, genere_le=g)
            for t, m, r, url, g in lignes]


@router.get("/enfants/{eleve_id}/absences", response_model=list[AbsenceParent])
def absences_enfant(
    eleve_id: str,
    parent: ParentConnecte = Depends(get_parent_connecte),
):
    with get_cursor() as cur:
        _verifier_enfant_du_parent(cur, parent.id, eleve_id)
        cur.execute(
            """
            SELECT date_absence, type_absence, justifie, motif
            FROM absences WHERE eleve_id = %s ORDER BY date_absence DESC
            """,
            (eleve_id,),
        )
        lignes = cur.fetchall()

    return [AbsenceParent(date_absence=d, type_absence=t, justifie=j, motif=m) for d, t, j, m in lignes]


@router.get("/enfants/{eleve_id}/paiements", response_model=list[PaiementParent])
def paiements_enfant(
    eleve_id: str,
    parent: ParentConnecte = Depends(get_parent_connecte),
):
    with get_cursor() as cur:
        _verifier_enfant_du_parent(cur, parent.id, eleve_id)
        cur.execute(
            """
            SELECT id, montant_du, montant_paye, date_echeance, statut
            FROM paiements WHERE eleve_id = %s ORDER BY date_echeance DESC NULLS LAST
            """,
            (eleve_id,),
        )
        lignes = cur.fetchall()

    return [PaiementParent(id=str(id_), montant_du=float(du), montant_paye=float(paye),
                             date_echeance=echeance, statut=statut)
            for id_, du, paye, echeance, statut in lignes]


@router.get("/enfants/{eleve_id}/devoirs", response_model=list[DevoirParent])
def devoirs_enfant(
    eleve_id: str,
    parent: ParentConnecte = Depends(get_parent_connecte),
):
    with get_cursor() as cur:
        _verifier_enfant_du_parent(cur, parent.id, eleve_id)
        cur.execute(
            """
            SELECT d.titre, m.nom, d.date_limite
            FROM devoirs d
            JOIN matieres m ON m.id = d.matiere_id
            JOIN eleves el ON el.classe_id = d.classe_id
            WHERE el.utilisateur_id = %s AND d.date_limite >= now()
            ORDER BY d.date_limite
            """,
            (eleve_id,),
        )
        lignes = cur.fetchall()

    return [DevoirParent(titre=titre, matiere=matiere, date_limite=date_limite)
            for titre, matiere, date_limite in lignes]


@router.get("/notifications", response_model=list[NotificationEleve])
def mes_notifications(parent: ParentConnecte = Depends(get_parent_connecte)):
    """Notifications adressées directement au parent (le compte parent a son
    propre utilisateur_id, distinct de celui de ses enfants)."""
    with get_cursor() as cur:
        cur.execute(
            """
            SELECT id, titre, message, type_notification, lue, created_at
            FROM notifications WHERE utilisateur_id = %s ORDER BY lue ASC, created_at DESC
            """,
            (parent.id,),
        )
        lignes = cur.fetchall()

    return [NotificationEleve(id=str(id_), titre=titre, message=message, type_notification=type_,
                                lue=lue, created_at=created_at)
            for id_, titre, message, type_, lue, created_at in lignes]
