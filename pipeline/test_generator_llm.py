"""
Tests de generator_llm.py + validation LLM avec un client Mistral simulé.

Pourquoi un mock plutôt qu'un vrai appel : ce environnement n'a pas accès à
api.mistral.ai (liste blanche réseau restreinte à PyPI/npm/GitHub). Un mock
honnête vaut mieux qu'une affirmation non vérifiée que "ça marche" — et il
permet en plus de tester des cas que l'API réelle ne produira qu'occasion-
nellement (JSON cassé, dérive de génération), donc c'est utile même avec un
accès réseau complet.
"""

import json
import types


class FausseReponseMistral:
    """Imite la forme de l'objet retourné par client.chat.complete()."""
    def __init__(self, contenu_texte: str, tokens: int = 180):
        self.choices = [types.SimpleNamespace(message=types.SimpleNamespace(content=contenu_texte))]
        self.usage = types.SimpleNamespace(total_tokens=tokens)


class FauxClientMistral:
    """Simule client.chat.complete() en renvoyant une réponse prédéfinie par
    thème, pour tester le pipeline sans réseau. `scenario` contrôle le type
    de réponse renvoyée pour chaque appel (voir SCENARIOS ci-dessous).
    """
    def __init__(self, scenario: str = "valide"):
        self.scenario = scenario
        self.appels = 0
        self.chat = types.SimpleNamespace(complete=self._complete)

    def _complete(self, **kwargs):
        self.appels += 1
        theme = kwargs["messages"][1]["content"]

        if self.scenario == "valide":
            contenu = json.dumps({
                "sous_theme": "Sous-thème généré",
                "enonce": f"Explique le mécanisme principal lié au thème abordé dans « {theme[:40]}... ».",
                "corrige": "La réponse détaillée couvre les mécanismes biologiques et historiques attendus.",
                "etapes": ["Identifier le phénomène.", "Expliquer la cause.", "Relier à l'exemple donné."],
                "contexte": "Cameroun",
                "tags": ["notion", "programme officiel"],
            }, ensure_ascii=False)
            return FausseReponseMistral(contenu)

        if self.scenario == "json_casse":
            # JSON tronqué — arrive en pratique quand max_tokens coupe la réponse
            return FausseReponseMistral('{"enonce": "Question incomplète', tokens=50)

        if self.scenario == "markdown_residuel":
            # Le LLM ignore la consigne "sans balises markdown"
            contenu = "```json\n" + json.dumps({
                "sous_theme": "Test", "enonce": "Décris le phénomène étudié dans ce chapitre du programme.",
                "corrige": "Réponse.", "etapes": ["Étape 1"], "contexte": None, "tags": [],
            }) + "\n```"
            return FausseReponseMistral(contenu)

        if self.scenario == "corrige_vide":
            contenu = json.dumps({
                "sous_theme": "Test", "enonce": "Décris le phénomène étudié dans ce chapitre du programme.",
                "corrige": "", "etapes": [], "contexte": None, "tags": [],
            })
            return FausseReponseMistral(contenu)

        if self.scenario == "corrige_recopie_enonce":
            enonce = "Décris le phénomène étudié dans ce chapitre du programme scolaire camerounais."
            contenu = json.dumps({
                "sous_theme": "Test", "enonce": enonce,
                "corrige": enonce,  # le LLM "abandonne" et recopie la question
                "etapes": ["Étape 1"], "contexte": None, "tags": [],
            })
            return FausseReponseMistral(contenu)

        if self.scenario == "repetition_degeneree":
            segment = "le phénomène se répète encore et encore et encore "
            contenu = json.dumps({
                "sous_theme": "Test", "enonce": "Décris le phénomène étudié dans ce chapitre.",
                "corrige": segment * 8, "etapes": ["Étape 1"], "contexte": None, "tags": [],
            })
            return FausseReponseMistral(contenu)

        raise ValueError(f"Scénario de test inconnu : {self.scenario}")


if __name__ == "__main__":
    from generator_llm import generer_lot_depuis_plan, generer_lot_llm, THEMES_PAR_MATIERE_NIVEAU
    from validation import valider_exercice_llm_genere

    print("=== Scénario : réponses valides (SVT 6ème) ===")
    client = FauxClientMistral(scenario="valide")
    resultats = generer_lot_depuis_plan("SVT", "6ème", client=client)
    for r in resultats:
        if r.erreur:
            print(f"  ERREUR GÉNÉRATION : {r.erreur}")
            continue
        ok, erreurs = valider_exercice_llm_genere(r.exercice)
        print(f"  {r.exercice['theme'][:45]:45s} : {'OK' if ok else erreurs}")

    print("\n=== Récupération d'un habillage markdown résiduel (doit réussir) ===")
    client = FauxClientMistral(scenario="markdown_residuel")
    resultats = generer_lot_llm("SVT", "6ème", ["Test"], client=client)
    r = resultats[0]
    if r.erreur:
        print(f"  ⚠️ ÉCHEC INATTENDU : {r.erreur}")
    else:
        ok, erreurs = valider_exercice_llm_genere(r.exercice)
        print(f"  JSON extrait malgré les balises ```json : {'OK, récupéré avec succès' if ok else erreurs}")

    print("\n=== Scénarios réellement pathologiques (doivent tous être rejetés proprement) ===")
    for scenario in ["json_casse", "corrige_vide",
                      "corrige_recopie_enonce", "repetition_degeneree"]:
        client = FauxClientMistral(scenario=scenario)
        resultats = generer_lot_llm("SVT", "6ème", ["Test"], client=client)
        r = resultats[0]
        if r.erreur:
            print(f"  {scenario:28s} : rejeté à la génération → {r.erreur}")
        else:
            ok, erreurs = valider_exercice_llm_genere(r.exercice)
            statut = "⚠️ ACCEPTÉ À TORT" if ok else f"rejeté à la validation → {erreurs}"
            print(f"  {scenario:28s} : {statut}")

    print(f"\n=== Couverture du plan de thèmes ===")
    for (matiere, niveau), themes in THEMES_PAR_MATIERE_NIVEAU.items():
        print(f"  {matiere:22s} {niveau:8s} : {len(themes)} thèmes")
