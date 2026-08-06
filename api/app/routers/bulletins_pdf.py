import io

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader

from ..db import get_cursor
from ..deps import get_administratif_connecte
from ..schemas import AdministratifConnecte
from .etablissement import DOSSIER_UPLOADS

router = APIRouter(prefix="/administration/bulletins", tags=["bulletins-pdf"])

# Palette reprise de l'identité visuelle du frontend (encre bleu-nuit,
# laiton) — pour que le bulletin imprimé ne jure pas avec l'app.
COULEUR_ENCRE = HexColor("#22304A")
COULEUR_ACCENT = HexColor("#B08D57")
COULEUR_GRIS = HexColor("#5B6472")
COULEUR_LIGNE = HexColor("#E7E2D6")


def _generer_pdf_bulletin(etablissement: dict, eleve: dict, bulletin: dict, notes_par_matiere: list[dict]) -> bytes:
    tampon = io.BytesIO()
    c = canvas.Canvas(tampon, pagesize=A4)
    largeur, hauteur = A4
    marge = 20 * mm
    y = hauteur - marge

    # En-tête : logo + nom établissement
    if etablissement.get("logo_url"):
        chemin_logo = DOSSIER_UPLOADS / etablissement["etablissement_id"] / "logo.png"
        if chemin_logo.exists():
            try:
                c.drawImage(ImageReader(str(chemin_logo)), marge, y - 18 * mm, width=18 * mm, height=18 * mm,
                            preserveAspectRatio=True, mask="auto")
            except Exception:
                pass  # un logo cassé ne doit jamais empêcher la génération du bulletin

    c.setFont("Helvetica-Bold", 16)
    c.setFillColor(COULEUR_ENCRE)
    c.drawString(marge + 22 * mm, y - 8 * mm, etablissement["nom"])
    c.setFont("Helvetica", 9)
    c.setFillColor(COULEUR_GRIS)
    c.drawString(marge + 22 * mm, y - 13 * mm, "Bulletin de notes")

    y -= 28 * mm
    c.setStrokeColor(COULEUR_LIGNE)
    c.line(marge, y, largeur - marge, y)
    y -= 10 * mm

    # Identité de l'élève
    c.setFont("Helvetica-Bold", 12)
    c.setFillColor(COULEUR_ENCRE)
    c.drawString(marge, y, f"{eleve['nom']} {eleve['prenom']}")
    c.setFont("Helvetica", 10)
    c.setFillColor(COULEUR_GRIS)
    c.drawString(marge, y - 6 * mm, f"Classe : {eleve['classe']}")
    c.drawRightString(largeur - marge, y, f"Trimestre {bulletin['trimestre']}")
    c.drawRightString(largeur - marge, y - 6 * mm, f"Année scolaire {eleve.get('annee_scolaire', '')}")

    y -= 18 * mm

    # Tableau des notes par matière
    c.setFont("Helvetica-Bold", 9)
    c.setFillColor(COULEUR_ENCRE)
    c.drawString(marge, y, "MATIÈRE")
    c.drawRightString(largeur - marge, y, "MOYENNE / 20")
    y -= 3 * mm
    c.setStrokeColor(COULEUR_ENCRE)
    c.line(marge, y, largeur - marge, y)
    y -= 7 * mm

    c.setFont("Helvetica", 10)
    for ligne in notes_par_matiere:
        if y < marge + 30 * mm:
            c.showPage()
            y = hauteur - marge
        c.setFillColor(COULEUR_ENCRE)
        c.drawString(marge, y, ligne["matiere"])
        c.setFillColor(COULEUR_ACCENT)
        c.drawRightString(largeur - marge, y, f"{ligne['moyenne']:.2f}")
        y -= 3 * mm
        c.setStrokeColor(COULEUR_LIGNE)
        c.line(marge, y, largeur - marge, y)
        y -= 7 * mm

    y -= 10 * mm
    c.setFont("Helvetica-Bold", 12)
    c.setFillColor(COULEUR_ENCRE)
    moyenne_texte = f"{bulletin['moyenne_generale']:.2f} / 20" if bulletin["moyenne_generale"] is not None else "—"
    c.drawString(marge, y, f"Moyenne générale : {moyenne_texte}")
    if bulletin.get("rang_classe"):
        c.drawRightString(largeur - marge, y, f"Rang : {bulletin['rang_classe']}")

    # Pied de page
    c.setFont("Helvetica", 7)
    c.setFillColor(COULEUR_GRIS)
    c.drawCentredString(largeur / 2, marge / 2, f"Généré par OskarAI — {etablissement['nom']}")

    c.showPage()
    c.save()
    tampon.seek(0)
    return tampon.read()


@router.get("/{bulletin_id}/pdf")
def telecharger_bulletin_pdf(
    bulletin_id: str,
    admin: AdministratifConnecte = Depends(get_administratif_connecte),
):
    with get_cursor() as cur:
        cur.execute(
            """
            SELECT b.trimestre, b.moyenne_generale, b.rang_classe,
                   u.nom, u.prenom, c.nom AS classe, an.libelle AS annee_scolaire,
                   el.utilisateur_id, b.annee_scolaire_id
            FROM bulletins b
            JOIN eleves el ON el.utilisateur_id = b.eleve_id
            JOIN utilisateurs u ON u.id = el.utilisateur_id
            JOIN classes c ON c.id = el.classe_id
            JOIN annees_scolaires an ON an.id = b.annee_scolaire_id
            WHERE b.id = %s AND c.etablissement_id = %s
            """,
            (bulletin_id, admin.etablissement_id),
        )
        row = cur.fetchone()
        if row is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                 detail="Bulletin introuvable dans votre établissement")
        (trimestre, moyenne_generale, rang_classe, nom, prenom, classe, annee_scolaire,
         eleve_id, annee_scolaire_id) = row

        cur.execute(
            """
            SELECT m.nom, v.moyenne_sur_20
            FROM vue_moyennes_eleve v
            JOIN matieres m ON m.id = v.matiere_id
            WHERE v.eleve_id = %s AND v.trimestre = %s AND v.annee_scolaire_id = %s
            ORDER BY m.nom
            """,
            (eleve_id, trimestre, annee_scolaire_id),
        )
        notes_par_matiere = [{"matiere": m, "moyenne": float(moy)} for m, moy in cur.fetchall()]

        cur.execute("SELECT nom, logo_url FROM etablissements WHERE id = %s", (admin.etablissement_id,))
        nom_etab, logo_url = cur.fetchone()

    pdf_bytes = _generer_pdf_bulletin(
        etablissement={"nom": nom_etab, "logo_url": logo_url, "etablissement_id": admin.etablissement_id},
        eleve={"nom": nom, "prenom": prenom, "classe": classe, "annee_scolaire": annee_scolaire},
        bulletin={"trimestre": trimestre, "moyenne_generale": float(moyenne_generale) if moyenne_generale is not None else None,
                  "rang_classe": rang_classe},
        notes_par_matiere=notes_par_matiere,
    )

    return StreamingResponse(
        io.BytesIO(pdf_bytes), media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=bulletin_{nom}_{prenom}_T{trimestre}.pdf"},
    )
