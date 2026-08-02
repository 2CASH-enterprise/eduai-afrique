from fastapi import APIRouter, Depends

from ..db import get_cursor
from ..deps import get_administratif_connecte
from ..schemas import AdministratifConnecte, DocumentPedagogique

router = APIRouter(prefix="/administration/documents", tags=["documents-rag"])

# Le dépôt et la suppression des programmes officiels sont désormais
# réservés à l'Admin Plateforme (/plateforme/documents) — un admin
# d'établissement ne peut plus que CONSULTER la liste, par transparence sur
# ce qui alimente les générations IA de son établissement. Avant cette
# restriction, n'importe quel admin d'établissement pouvait déposer un
# document visible par toute la plateforme (confiance mutuelle temporaire,
# le temps que ce module existe).


@router.get("", response_model=list[DocumentPedagogique])
def lister_programmes_officiels(admin: AdministratifConnecte = Depends(get_administratif_connecte)):
    """Ne montre que les programmes du MÊME PAYS que l'établissement — un
    admin camerounais n'a aucune raison de voir la liste des programmes
    sénégalais (voir migration 009)."""
    with get_cursor() as cur:
        cur.execute(
            """
            SELECT d.id, d.type_document, d.pays, n.nom, m.nom, d.titre, d.nombre_pages, d.statut, d.erreur_traitement,
                   (SELECT COUNT(*) FROM passages_documents p WHERE p.document_id = d.id)
            FROM documents_pedagogiques d
            LEFT JOIN niveaux n ON n.id = d.niveau_id
            LEFT JOIN matieres m ON m.id = d.matiere_id
            JOIN etablissements e ON e.id = %s
            WHERE d.type_document = 'programme_officiel' AND d.pays = e.pays
            ORDER BY d.created_at DESC
            """,
            (admin.etablissement_id,),
        )
        lignes = cur.fetchall()
    return [DocumentPedagogique(id=str(id_), type_document=t, pays=pays_doc, niveau=n, matiere=m, titre=titre,
                                  nombre_pages=np, statut=s, erreur_traitement=e, nombre_passages=npass)
            for id_, t, pays_doc, n, m, titre, np, s, e, npass in lignes]
