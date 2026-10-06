import re

def normalizar_tema_chave(t):
    s = (t or "").lower()
    if "passé composé" in s or "passe compose" in s:
        return "passe_compose"
    if "accord" in s and "participe" in s:
        return "accord_participe"
    if "négation" in s or "negation" in s:
        return "negation"
    if "famille" in s:
        return "famille"
    if "1er groupe" in s or "verbe" in s or "présent" in s:
        return "verbes_present"
    if "article" in s or "partitif" in s:
        return "articles"
    if "imparfait" in s:
        return "imparfait"
    if "pronom" in s or "cod" in s or "coi" in s:
        return "pronoms"
    if "subjonctif" in s:
        return "subjonctif"
    if "conditionnel" in s or "hypothèse" in s or "hypothese" in s:
        return "conditionnel"
    if "préposition" in s or "preposition" in s or "lieu" in s:
        return "prepositions"
    if "salutation" in s or "présentation" in s or "presentation" in s:
        return "salutations"
    if "restaurant" in s or "boulangerie" in s or "nourriture" in s or "café" in s:
        return "restaurant"
    return "geral"

print("passe_compose:", normalizar_tema_chave("Le Passé Composé: Être vs Avoir"))
print("accord:", normalizar_tema_chave("L'Accord du Participe Passé"))
print("negation:", normalizar_tema_chave("La Négation Simple (ne ... pas)"))
print("famille:", normalizar_tema_chave("Le Vocabulaire de la Famille"))
print("articles:", normalizar_tema_chave("Les Articles Définis, Indéfinis et Partitifs"))
print("custom:", normalizar_tema_chave("Commander au restaurant"))
