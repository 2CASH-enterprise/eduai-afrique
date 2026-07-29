import sys
sys.path.insert(0, ".")
from fastapi.testclient import TestClient
from app.main import app
import psycopg2

client = TestClient(app)
conn = psycopg2.connect(dbname="eduai_test", user="postgres", host="/var/run/postgresql")
cur = conn.cursor()

print("=== Login élève ===")
r = client.post("/auth/login", json={"email": "jean.dupont@test.cm", "mot_de_passe": "eleve123"})
print(f"Statut : {r.status_code}")
assert r.status_code == 200
token = r.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}

print("\n=== Un enseignant ne doit PAS pouvoir utiliser une route élève avec son propre token ===")
r_ens = client.post("/auth/login", json={"email": "prof.test@lyceembankomo.cm", "mot_de_passe": "motdepasse123"})
headers_ens = {"Authorization": f"Bearer {r_ens.json()['access_token']}"}
r = client.get("/eleve/exercices", headers=headers_ens)
print(f"Statut : {r.status_code}")
assert r.status_code == 401, "FUITE : un enseignant a pu accéder à une route élève !"
print("✅ Cloisonnement des rôles confirmé (401, pas juste une liste vide).\n")

print("=== Liste des exercices disponibles (statut='valide' seulement) ===")
r = client.get("/eleve/exercices", headers=headers)
exercices = r.json()
print(f"Statut : {r.status_code} — {len(exercices)} exercices")
for ex in exercices[:3]:
    print(f"  {ex['theme']} — {ex['enonce'][:60]}...")
    assert "corrige" not in ex, "FUITE : le corrigé est visible avant révélation !"
print("✅ Aucun corrigé visible dans la liste.\n")

premier_id = exercices[0]["id"]

print(f"=== Consultation du corrigé ===")
r = client.post(f"/eleve/exercices/{premier_id}/reveler", headers=headers)
print(f"Statut : {r.status_code} — corrigé : {r.json()['corrige'][:50]}...")
assert r.status_code == 200
print("✅ Corrigé révélé.\n")

print(f"=== Déclaration d'une tentative réussie ===")
r = client.post(f"/eleve/exercices/{premier_id}/tentative", headers=headers,
                 json={"reussi": True, "temps_passe_secondes": 90})
print(f"Statut : {r.status_code} — {r.json()}")
assert r.status_code == 200
print("✅ Tentative enregistrée.\n")

print(f"=== Vérification des statistiques recalculées sur l'exercice ===")
cur.execute("SELECT statistiques FROM exercices WHERE id = %s", (premier_id,))
print("Statistiques :", cur.fetchone()[0])

print(f"\n=== Tentative sur un exercice inexistant (doit 404) ===")
r = client.post("/eleve/exercices/00000000-0000-0000-0000-000000000000/tentative", headers=headers,
                 json={"reussi": True})
print(f"Statut : {r.status_code}")
assert r.status_code == 404
print("✅ 404 confirmé.\n")

print("=== Mes résultats ===")
r = client.get("/eleve/mes-resultats", headers=headers)
print(f"Statut : {r.status_code} — {r.json()}")
assert r.status_code == 200

print("\n=== Mon planning ===")
r = client.get("/eleve/mon-planning", headers=headers)
print(f"Statut : {r.status_code} — {r.json()}")
assert r.status_code == 200 and len(r.json()) >= 1
print("✅ Devoir à venir trouvé.\n")

print("=== Mes notifications ===")
r = client.get("/eleve/notifications", headers=headers)
notifs = r.json()
print(f"Statut : {r.status_code} — {notifs}")
assert len(notifs) >= 1
notif_id = notifs[0]["id"]

print(f"\n=== Marquer une notification comme lue ===")
r = client.patch(f"/eleve/notifications/{notif_id}/lu", headers=headers)
print(f"Statut : {r.status_code} — {r.json()}")
assert r.status_code == 200

r = client.get("/eleve/notifications", headers=headers)
notif_maj = next(n for n in r.json() if n["id"] == notif_id)
assert notif_maj["lue"] is True
print("✅ Statut lu confirmé en base.\n")

print("🎉 Tous les tests du Module Élève sont passés.")
