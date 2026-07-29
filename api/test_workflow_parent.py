import sys
sys.path.insert(0, ".")
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def login(email, mot_de_passe):
    r = client.post("/auth/login", json={"email": email, "mot_de_passe": mot_de_passe})
    assert r.status_code == 200, r.json()
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


headers_parent = login("parent.dupont@test.cm", "parent123")
headers_intrus = login("parent.intrus@test.cm", "parent123")

print("=== Liste des enfants du parent Dupont ===")
r = client.get("/parent/enfants", headers=headers_parent)
enfants = r.json()
print(f"Statut : {r.status_code} — {enfants}")
assert r.status_code == 200 and len(enfants) == 1
eleve_id = enfants[0]["eleve_id"]
print("✅ Un enfant trouvé.\n")

print("=== Liste des enfants du parent intrus (aucun enfant lié) ===")
r = client.get("/parent/enfants", headers=headers_intrus)
print(f"Statut : {r.status_code} — {r.json()}")
assert r.json() == []
print("✅ Liste vide correcte.\n")

print("=== Tableau de bord de l'enfant (parent légitime) ===")
r = client.get(f"/parent/enfants/{eleve_id}/tableau-de-bord", headers=headers_parent)
print(f"Statut : {r.status_code} — {r.json()}")
assert r.status_code == 200
assert r.json()["nombre_absences"] == 1 and r.json()["nombre_retards"] == 1
print("✅ Absences et retards comptés correctement.\n")

print("=== TENTATIVE D'INTRUSION : le parent intrus essaie d'accéder au tableau de bord de l'enfant d'un autre ===")
r = client.get(f"/parent/enfants/{eleve_id}/tableau-de-bord", headers=headers_intrus)
print(f"Statut : {r.status_code} — {r.json()}")
assert r.status_code == 404, "FAILLE DE SÉCURITÉ : un parent a pu voir les données d'un enfant qui n'est pas le sien !"
print("✅ Accès refusé (404) — aucune fuite de données entre familles.\n")

print("=== Même vérification sur bulletins / absences / paiements / devoirs ===")
for route in ["bulletins", "absences", "paiements", "devoirs"]:
    r = client.get(f"/parent/enfants/{eleve_id}/{route}", headers=headers_intrus)
    print(f"  /{route} → {r.status_code}")
    assert r.status_code == 404, f"FUITE sur /parent/enfants/{{id}}/{route} !"
print("✅ Isolation confirmée sur toutes les routes enfant.\n")

print("=== Le parent légitime, lui, accède normalement à tout ===")
for route in ["bulletins", "absences", "paiements", "devoirs"]:
    r = client.get(f"/parent/enfants/{eleve_id}/{route}", headers=headers_parent)
    print(f"  /{route} → {r.status_code} — {r.json()}")
    assert r.status_code == 200
print("✅ Accès légitime confirmé.\n")

print("=== ID d'enfant totalement inexistant (doit aussi 404, pas 500) ===")
r = client.get("/parent/enfants/00000000-0000-0000-0000-000000000000/tableau-de-bord", headers=headers_parent)
print(f"Statut : {r.status_code}")
assert r.status_code == 404
print("✅ Pas de crash sur ID invalide.\n")

print("🎉 Tous les tests du Module Parent sont passés, isolation inter-familles confirmée.")
