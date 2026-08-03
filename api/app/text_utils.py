"""Petits utilitaires partagés entre les modules de génération IA."""


def aplatir_en_texte(valeur, niveau: int = 0) -> str:
    """Convertit n'importe quelle valeur JSON en texte lisible. Filet de
    sécurité : rien ne garantit qu'un modèle de langage respecte à 100% la
    consigne de renvoyer une chaîne simple pour un champ donné — mieux vaut
    aplatir proprement une structure inattendue (objet, liste imbriquée)
    que planter (incidents des 02/08 et 03/08 : React qui refuse d'afficher
    un objet directement, puis Pydantic qui rejette un objet là où une
    chaîne était attendue)."""
    prefixe = "  " * niveau
    if isinstance(valeur, str):
        return valeur
    if isinstance(valeur, (int, float, bool)) or valeur is None:
        return str(valeur)
    if isinstance(valeur, list):
        return "\n".join(f"{prefixe}- {aplatir_en_texte(v, niveau + 1)}" for v in valeur)
    if isinstance(valeur, dict):
        lignes = []
        for cle, sous_valeur in valeur.items():
            libelle = str(cle).replace("_", " ").capitalize()
            sous_texte = aplatir_en_texte(sous_valeur, niveau + 1)
            if "\n" in sous_texte:
                lignes.append(f"{prefixe}{libelle} :\n{sous_texte}")
            else:
                lignes.append(f"{prefixe}{libelle} : {sous_texte}")
        return "\n".join(lignes)
    return str(valeur)
