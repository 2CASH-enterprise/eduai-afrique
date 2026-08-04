"""Export PDF des ressources de cours (TODO.md point 19.1) — permet à
l'enseignant d'imprimer une fiche, un contrôle, un QCM... Utilise
reportlab/Platypus (déjà une dépendance du projet, voir bulletins_pdf.py),
avec la mise en page automatique adaptée au texte de longueur variable —
contrairement aux bulletins (mise en page fixe), le contenu ici peut
largement dépasser une page.
"""
import io

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, ListFlowable, ListItem, HRFlowable

COULEUR_ENCRE = HexColor("#22304A")
COULEUR_ACCENT = HexColor("#B08D57")
COULEUR_GRIS = HexColor("#5B6472")
COULEUR_LIGNE = HexColor("#E7E2D6")

_feuilles = getSampleStyleSheet()
STYLE_TITRE = ParagraphStyle("TitreRessource", parent=_feuilles["Title"], textColor=COULEUR_ENCRE, fontSize=18, spaceAfter=2)
STYLE_META = ParagraphStyle("Meta", parent=_feuilles["Normal"], textColor=COULEUR_GRIS, fontSize=9, spaceAfter=10)
STYLE_SECTION = ParagraphStyle("Section", parent=_feuilles["Heading2"], textColor=COULEUR_ACCENT, fontSize=12,
                                spaceBefore=14, spaceAfter=6)
STYLE_CORPS = ParagraphStyle("Corps", parent=_feuilles["Normal"], textColor=COULEUR_ENCRE, fontSize=10.5,
                              leading=15, alignment=TA_LEFT, spaceAfter=6)
STYLE_CORRIGE = ParagraphStyle("Corrige", parent=STYLE_CORPS, textColor=COULEUR_GRIS)
STYLE_LISTE = ParagraphStyle("Liste", parent=STYLE_CORPS, spaceAfter=2)


def _echapper(texte) -> str:
    if texte is None:
        return ""
    return str(texte).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br/>")


def _bloc_exercice(elements, numero, enonce, corrige, difficulte=None, points=None):
    entete = f"<b>Exercice {numero}</b>"
    if difficulte:
        entete += f" — {difficulte}"
    if points is not None:
        entete += f" ({points} pts)"
    elements.append(Paragraph(entete, STYLE_CORPS))
    elements.append(Paragraph(_echapper(enonce), STYLE_CORPS))
    elements.append(Paragraph(f"<i>Corrigé :</i> {_echapper(corrige)}", STYLE_CORRIGE))
    elements.append(Spacer(1, 8))


def _construire_sections(type_ressource: str, contenu: dict) -> list:
    elements = []

    # Repli texte simple — mêmes règles que le frontend (RenduRessource) :
    # une seule clé "texte" signifie que l'IA n'a pas respecté le schéma,
    # ou que l'enseignant a modifié le contenu manuellement.
    if contenu.get("texte") is not None and len(contenu) == 1:
        elements.append(Paragraph(_echapper(contenu["texte"]), STYLE_CORPS))
        return elements

    if type_ressource == "fiche_pedagogique":
        if contenu.get("objectifs"):
            elements.append(Paragraph("Objectifs", STYLE_SECTION))
            elements.append(ListFlowable([ListItem(Paragraph(_echapper(o), STYLE_LISTE)) for o in contenu["objectifs"]], bulletType="bullet"))
        if contenu.get("competences_visees"):
            elements.append(Paragraph("Compétences visées", STYLE_SECTION))
            elements.append(ListFlowable([ListItem(Paragraph(_echapper(c), STYLE_LISTE)) for c in contenu["competences_visees"]], bulletType="bullet"))
        if contenu.get("deroulement"):
            elements.append(Paragraph("Déroulement", STYLE_SECTION))
            for etape in contenu["deroulement"]:
                duree = f" ({etape.get('duree')})" if etape.get("duree") else ""
                elements.append(Paragraph(f"<b>{_echapper(etape.get('etape'))}</b>{duree}", STYLE_CORPS))
                elements.append(Paragraph(_echapper(etape.get("description")), STYLE_CORPS))

    elif type_ressource == "resume":
        if contenu.get("definitions_cles"):
            elements.append(Paragraph("Définitions clés", STYLE_SECTION))
            for d in contenu["definitions_cles"]:
                elements.append(Paragraph(f"<b>{_echapper(d.get('terme'))}</b> — {_echapper(d.get('definition'))}", STYLE_CORPS))
        if contenu.get("regles_principales"):
            elements.append(Paragraph("Règles principales", STYLE_SECTION))
            elements.append(ListFlowable([ListItem(Paragraph(_echapper(r), STYLE_LISTE)) for r in contenu["regles_principales"]], bulletType="bullet"))
        if contenu.get("exemple_travaille"):
            elements.append(Paragraph("Exemple travaillé", STYLE_SECTION))
            elements.append(Paragraph(_echapper(contenu["exemple_travaille"].get("enonce")), STYLE_CORPS))
            elements.append(Paragraph(_echapper(contenu["exemple_travaille"].get("resolution")), STYLE_CORRIGE))

    elif type_ressource == "exercices":
        for i, ex in enumerate(contenu.get("exercices", []), start=1):
            _bloc_exercice(elements, ex.get("numero", i), ex.get("enonce"), ex.get("corrige"), ex.get("difficulte"))

    elif type_ressource == "qcm":
        for i, q in enumerate(contenu.get("questions", []), start=1):
            elements.append(Paragraph(f"<b>{q.get('numero', i)}. {_echapper(q.get('question'))}</b>", STYLE_CORPS))
            for j, choix in enumerate(q.get("choix", [])):
                marque = "✓ " if j == q.get("bonne_reponse") else "— "
                elements.append(Paragraph(f"{marque}{chr(65+j)}. {_echapper(choix)}", STYLE_LISTE))
            if q.get("explication"):
                elements.append(Paragraph(f"<i>{_echapper(q['explication'])}</i>", STYLE_CORRIGE))
            elements.append(Spacer(1, 8))

    elif type_ressource in ("devoir", "controle"):
        if contenu.get("duree"):
            elements.append(Paragraph(f"<i>Durée : {_echapper(contenu['duree'])}</i>", STYLE_META))
        for i, ex in enumerate(contenu.get("exercices", []), start=1):
            _bloc_exercice(elements, ex.get("numero", i), ex.get("enonce"), ex.get("corrige"), points=ex.get("points"))
        bloc_final = contenu.get("probleme") or contenu.get("exercice_synthese")
        if bloc_final:
            label = "Problème" if "probleme" in contenu else "Exercice de synthèse"
            elements.append(Paragraph(label, STYLE_SECTION))
            elements.append(Paragraph(_echapper(bloc_final.get("enonce")), STYLE_CORPS))
            elements.append(Paragraph(f"<i>Corrigé :</i> {_echapper(bloc_final.get('corrige'))}", STYLE_CORRIGE))

    return elements


def construire_pdf_ressource(titre_cours: str, matiere: str, classe: str, label_ressource: str,
                               type_ressource: str, contenu: dict) -> bytes:
    """Une seule ressource — ex : imprimer LE contrôle, pas tout le cours."""
    tampon = io.BytesIO()
    doc = SimpleDocTemplate(tampon, pagesize=A4, topMargin=20 * mm, bottomMargin=20 * mm,
                              leftMargin=20 * mm, rightMargin=20 * mm)
    elements = [
        Paragraph(_echapper(titre_cours), STYLE_TITRE),
        Paragraph(f"{_echapper(label_ressource)} — {_echapper(matiere)} — {_echapper(classe)}", STYLE_META),
        HRFlowable(width="100%", color=COULEUR_LIGNE, thickness=0.5, spaceAfter=10),
    ]
    elements += _construire_sections(type_ressource, contenu)
    doc.build(elements)
    return tampon.getvalue()


def construire_pdf_cours_complet(titre_cours: str, matiere: str, classe: str, ressources: list[dict]) -> bytes:
    """Toutes les ressources d'un cours dans un seul PDF, une section par
    ressource — pratique pour tout imprimer d'un coup."""
    tampon = io.BytesIO()
    doc = SimpleDocTemplate(tampon, pagesize=A4, topMargin=20 * mm, bottomMargin=20 * mm,
                              leftMargin=20 * mm, rightMargin=20 * mm)
    elements = [
        Paragraph(_echapper(titre_cours), STYLE_TITRE),
        Paragraph(f"{_echapper(matiere)} — {_echapper(classe)}", STYLE_META),
    ]
    for ressource in ressources:
        elements.append(HRFlowable(width="100%", color=COULEUR_LIGNE, thickness=0.5, spaceBefore=6, spaceAfter=10))
        elements.append(Paragraph(_echapper(ressource["label"]), STYLE_SECTION))
        elements += _construire_sections(ressource["type_ressource"], ressource["contenu"])
    doc.build(elements)
    return tampon.getvalue()
