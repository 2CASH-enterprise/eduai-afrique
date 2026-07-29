"""
Orchestrateur : relie génération, validation automatique, et insertion dans
la table `exercices` du schéma PostgreSQL (schema_eduai_afrique.sql).

Logique de statut appliquée (reflète le vrai processus de validation, pas
un raccourci) :

  - Maths/Physique générés par template Python + validés par SymPy
      → validation_ia = True, validation_humaine = False, statut = 'en_validation'
        (le calcul est garanti juste, mais un enseignant reste libre de
        vérifier la pertinence pédagogique avant publication — V1 prudente)

  - Français/SVT/Histoire-Géo générés par Mistral
      → validation_ia = False, validation_humaine = False, statut = 'en_validation'
        (aucun contrôle automatique fiable n'existe pour ces matières :
        direction honnête plutôt qu'optimiste)

Rien n'est jamais inséré avec statut = 'valide' directement : ça, c'est le
rôle du Module Enseignant (interface de relecture), pas du pipeline.
"""

from __future__ import annotations
import os
import psycopg2
from psycopg2.extras import Json

from generator_math import generer_lot, TEMPLATES, NIVEAU_PAR_DEFAUT
from generator_llm import generer_lot_llm, generer_lot_depuis_plan
from validation import valider_exercice_math_genere, valider_exercice_llm_genere, detecter_doublon_probable


def _doublon_exact_template(ex: dict, existants_enonces: set[str]) -> bool:
    """Pour les exercices de template (maths), un 'doublon' n'a de sens que si
    l'énoncé est EXACTEMENT identique (même valeur numérique tirée deux fois).
    La similarité Jaccard textuelle (utile pour repérer les paraphrases d'un
    LLM) donne des faux positifs ici car les phrases-modèles partagent
    volontairement la même structure ('Écris ce nombre en toutes lettres')
    — seul le nombre change, et c'est ce nombre qui doit être comparé.
    """
    return ex["enonce"] in existants_enonces


def _connexion():
    return psycopg2.connect(
        dbname=os.environ.get("PGDATABASE", "eduai_test"),
        user=os.environ.get("PGUSER", "postgres"),
        host=os.environ.get("PGHOST", "/var/run/postgresql"),
    )


def _recuperer_ids_reference(cur, niveau_nom: str, matiere_nom: str) -> tuple[str, str]:
    cur.execute("SELECT id FROM niveaux WHERE nom = %s LIMIT 1", (niveau_nom,))
    row = cur.fetchone()
    if row is None:
        raise ValueError(f"Niveau introuvable en base : {niveau_nom}")
    niveau_id = row[0]

    cur.execute("SELECT id FROM matieres WHERE nom = %s LIMIT 1", (matiere_nom,))
    row = cur.fetchone()
    if row is None:
        raise ValueError(f"Matière introuvable en base : {matiere_nom}")
    matiere_id = row[0]

    return niveau_id, matiere_id


def _inserer_exercice(cur, exercice: dict, niveau_id: str, matiere_id: str,
                       source: str, validation_ia: bool) -> str:
    cur.execute(
        """
        INSERT INTO exercices (
            pays, niveau_id, matiere_id, theme, sous_theme, type_exercice,
            difficulte, enonce, corrige, etapes, contexte, programme,
            source, validation_ia, validation_humaine, statut, tags
        ) VALUES (
            %s, %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s
        ) RETURNING id
        """,
        (
            "Cameroun", niveau_id, matiere_id, exercice["theme"],
            exercice.get("sous_theme"), exercice.get("type_exercice", "application"),
            exercice.get("difficulte", "moyen"), exercice["enonce"], exercice["corrige"],
            exercice.get("etapes", []), exercice.get("contexte"),
            "Programme Cameroun 2026-2027", source, validation_ia, False,
            "en_validation", exercice.get("tags", []),
        ),
    )
    return cur.fetchone()[0]


def pipeline_template(module_generateur, matiere_nom: str, template_nom: str,
                       niveau_nom: str, quantite: int) -> dict:
    """Génère, valide et insère un lot d'exercices à partir d'un template
    déterministe — fonctionne pour n'importe quelle matière tant que le
    module respecte le contrat de generator_math.py : TEMPLATES (dict de
    fonctions), generer_lot(), et un champ `_verif` structuré par exercice.
    """
    conn = _connexion()
    cur = conn.cursor()
    niveau_id, matiere_id = _recuperer_ids_reference(cur, niveau_nom, matiere_nom)

    cur.execute(
        "SELECT enonce FROM exercices WHERE niveau_id = %s AND matiere_id = %s",
        (niveau_id, matiere_id),
    )
    existants_enonces = {row[0] for row in cur.fetchall()}

    brouillons = module_generateur.generer_lot(template_nom, niveau_nom, quantite)
    rapport = {"generes": len(brouillons), "inseres": 0, "rejetes_calcul": 0, "rejetes_doublon": 0}

    for ex in brouillons:
        ok, erreurs = valider_exercice_math_genere(ex)
        if not ok:
            rapport["rejetes_calcul"] += 1
            continue
        if _doublon_exact_template(ex, existants_enonces):
            rapport["rejetes_doublon"] += 1
            continue

        _inserer_exercice(cur, ex, niveau_id, matiere_id,
                           source="python_genere", validation_ia=True)
        existants_enonces.add(ex["enonce"])
        rapport["inseres"] += 1

    conn.commit()
    cur.close()
    conn.close()
    return rapport


def pipeline_maths(template_nom: str, niveau_nom: str, quantite: int) -> dict:
    """Alias rétrocompatible : pipeline_template fixé sur generator_math."""
    import generator_math
    return pipeline_template(generator_math, "Mathématiques", template_nom, niveau_nom, quantite)


def pipeline_llm(matiere_nom: str, niveau_nom: str, themes: list[str] | None = None,
                  client=None) -> dict:
    """Génère, valide et insère un lot d'exercices via Mistral (ou un client
    injecté pour les tests). Si `themes` est omis, utilise le plan de
    génération THEMES_PAR_MATIERE_NIVEAU pour ce couple matière/niveau.

    IMPORTANT : contrairement à pipeline_template (maths), le rapport compte
    un `rejetes_validation` distinct de `erreurs_api` — un exercice peut très
    bien revenir avec un JSON valide de l'API tout en étant structurellement
    suspect (corrigé vide, répétition dégénérée, etc.), et ces deux causes
    de rejet ont des implications différentes (l'une coûte un appel API pour
    rien, l'autre est un vrai signal de qualité du prompt à ajuster).
    """
    conn = _connexion()
    cur = conn.cursor()
    niveau_id, matiere_id = _recuperer_ids_reference(cur, niveau_nom, matiere_nom)

    if themes is not None:
        resultats = generer_lot_llm(matiere_nom, niveau_nom, themes, client=client)
    else:
        resultats = generer_lot_depuis_plan(matiere_nom, niveau_nom, client=client)

    rapport = {"tentes": len(resultats), "inseres": 0, "erreurs_api": 0,
               "rejetes_validation": 0, "cout_total_usd": 0.0, "tokens_total": 0}

    for resultat in resultats:
        rapport["cout_total_usd"] += resultat.cout_estime_usd
        rapport["tokens_total"] += resultat.tokens_utilises
        if resultat.erreur or resultat.exercice is None:
            rapport["erreurs_api"] += 1
            continue

        ok, erreurs = valider_exercice_llm_genere(resultat.exercice)
        if not ok:
            rapport["rejetes_validation"] += 1
            continue

        _inserer_exercice(cur, resultat.exercice, niveau_id, matiere_id,
                           source="mistral_ai", validation_ia=False)
        rapport["inseres"] += 1

    conn.commit()
    cur.close()
    conn.close()
    return rapport


if __name__ == "__main__":
    import generator_math
    import generator_physique_chimie

    def executer_lot(module, matiere_nom, titre):
        print(f"=== {titre} ===\n")
        totaux = {"generes": 0, "inseres": 0, "rejetes_calcul": 0, "rejetes_doublon": 0}
        for template_nom in module.TEMPLATES:
            niveau_cible = module.NIVEAU_PAR_DEFAUT[template_nom]
            rapport = pipeline_template(module, matiere_nom, template_nom, niveau_cible, quantite=10)
            for cle in totaux:
                totaux[cle] += rapport[cle]
            print(f"{template_nom:32s} ({niveau_cible:8s}) : {rapport}")
        print(f"\n=== TOTAL {matiere_nom} : {totaux['inseres']}/{totaux['generes']} insérés "
              f"({totaux['rejetes_calcul']} rejets calcul, {totaux['rejetes_doublon']} rejets doublon) ===\n")
        return totaux

    t1 = executer_lot(generator_math, "Mathématiques", "Pipeline Mathématiques : 13 templates × 10")
    t2 = executer_lot(generator_physique_chimie, "Physique-Chimie", "Pipeline Physique-Chimie : 9 templates × 10")

    grand_total_generes = t1["generes"] + t2["generes"]
    grand_total_inseres = t1["inseres"] + t2["inseres"]
    print(f"=== GRAND TOTAL (Maths + PC) : {grand_total_inseres}/{grand_total_generes} insérés ===")
