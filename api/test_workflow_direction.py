import sys
sys.path.insert(0, ".")
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def login(email, mot_de_passe):
    r = client.post("/auth/login", json={"email": email, "mot_de_passe": mot_de_passe})
    assert r.status_code == 200, r.json()
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


headers_etab1 = login("directeur@lyceembankomo.cm", "direction123")
headers_etab2 = login("directeur@collegeexcellence.cm", "direction123")

print("=== Un élève ne doit PAS pouvoir utiliser une route direction ===")
headers_eleve = login("jean.dupont@test.cm", "eleve123")
r = client.get("/direction/tableau-de-bord", headers=headers_eleve)
print(f"Statut : {r.status_code}")
assert r.status_code == 401
print("✅ Cloisonnement confirmé.\n")

print("=== Tableau de bord — Lycée de Mbankomo (étab. 1) ===")
r = client.get("/direction/tableau-de-bord", headers=headers_etab1)
tb1 = r.json()
print(tb1)
assert r.status_code == 200
assert tb1["effectif_eleves"] >= 1

print("\n=== Tableau de bord — Collège Excellence Douala (étab. 2) ===")
r = client.get("/direction/tableau-de-bord", headers=headers_etab2)
tb2 = r.json()
print(tb2)
assert r.status_code == 200

print("\n=== VÉRIFICATION D'ISOLATION : les deux tableaux doivent différer ===")
assert tb1["montant_du_total"] != tb2["montant_du_total"] or tb1["effectif_eleves"] != tb2["effectif_eleves"], \
    "SUSPECT : les deux établissements montrent des chiffres identiques"
print(f"Étab. 1 — élèves: {tb1['effectif_eleves']}, montant dû: {tb1['montant_du_total']}")
print(f"Étab. 2 — élèves: {tb2['effectif_eleves']}, montant dû: {tb2['montant_du_total']}")
assert tb2["montant_du_total"] == 200000.0, "Fuite : étab. 2 ne devrait voir que son propre paiement de 200000"
assert tb2["montant_paye_total"] == 200000.0
print("✅ Aucune fuite de données financières entre établissements.\n")

print("=== Paiements en retard — Étab. 1 (doit inclure l'élève en retard) ===")
r = client.get("/direction/paiements/retards", headers=headers_etab1)
retards1 = r.json()
print(retards1)
assert len(retards1) == 1
assert retards1[0]["montant_restant"] == 70000.0
print("✅ Retard détecté correctement.\n")

print("=== Paiements en retard — Étab. 2 (paiement complet, donc aucun retard attendu) ===")
r = client.get("/direction/paiements/retards", headers=headers_etab2)
retards2 = r.json()
print(retards2)
assert retards2 == [], "L'élève de l'étab. 2 a payé intégralement, il ne devrait pas apparaître"
print("✅ Aucun faux positif.\n")

print("=== VÉRIFICATION CROISÉE : étab. 2 ne doit voir AUCUN élève de l'étab. 1 ===")
noms_retards1 = {(r["eleve_nom"], r["eleve_prenom"]) for r in retards1}
noms_retards2 = {(r["eleve_nom"], r["eleve_prenom"]) for r in retards2}
assert noms_retards1.isdisjoint(noms_retards2)
print("✅ Aucun élève ne fuite d'un établissement à l'autre.\n")

print("=== Validations en attente — Étab. 1 ===")
r = client.get("/direction/validations-en-attente", headers=headers_etab1)
print(f"Statut : {r.status_code} — {r.json()}")
assert r.status_code == 200

print("\n=== Validations en attente — Étab. 2 (aucun enseignant affecté → liste vide) ===")
r = client.get("/direction/validations-en-attente", headers=headers_etab2)
print(f"Statut : {r.status_code} — {r.json()}")
assert r.json() == []
print("✅ Établissement sans enseignant affecté → périmètre vide, comportement correct.\n")

print("=== Activité des enseignants — Étab. 1 ===")
r = client.get("/direction/enseignants/activite", headers=headers_etab1)
print(f"Statut : {r.status_code} — {r.json()}")
assert r.status_code == 200
assert len(r.json()) >= 1

print("\n=== Moyennes par classe — Étab. 1 ===")
r = client.get("/direction/classes/moyennes", headers=headers_etab1)
print(f"Statut : {r.status_code} — {r.json()}")
assert r.status_code == 200

print("\n🎉 Tous les tests du Module Direction sont passés, isolation multi-établissement confirmée.")
