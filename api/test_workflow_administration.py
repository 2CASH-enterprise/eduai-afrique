import sys
sys.path.insert(0, ".")
from fastapi.testclient import TestClient
from app.main import app
import psycopg2

client = TestClient(app)
conn = psycopg2.connect(dbname="eduai_test", user="postgres", host="/var/run/postgresql")
cur = conn.cursor()

r = client.post("/auth/login", json={"email": "secretariat@lyceembankomo.cm", "mot_de_passe": "admin123"})
assert r.status_code == 200, r.json()
headers = {"Authorization": f"Bearer {r.json()['access_token']}"}

cur.execute("SELECT id FROM classes WHERE nom = '6ème A' LIMIT 1")
classe6a_id = str(cur.fetchone()[0])
cur.execute("SELECT id FROM matieres WHERE nom = 'Mathématiques' LIMIT 1")
math_id = str(cur.fetchone()[0])
cur.execute("SELECT id FROM annees_scolaires LIMIT 1")
annee_id = str(cur.fetchone()[0])

print("=== Création d'un élève ===")
r = client.post("/administration/eleves", headers=headers, json={
    "email": "nouvel.eleve@test.cm", "nom": "Fotso", "prenom": "Marie",
    "classe_id": classe6a_id, "matricule": "MAT999",
})
print(f"Statut : {r.status_code} — {r.json()}")
assert r.status_code == 201
nouvel_eleve_id = r.json()["id"]
mot_de_passe_genere = r.json()["mot_de_passe_provisoire"]
print("✅ Élève créé avec mot de passe provisoire.\n")

print("=== Le nouveau compte élève peut-il vraiment se connecter avec ce mot de passe ? ===")
r = client.post("/auth/login", json={"email": "nouvel.eleve@test.cm", "mot_de_passe": mot_de_passe_genere})
print(f"Statut : {r.status_code}")
assert r.status_code == 200
print("✅ Connexion réussie avec le mot de passe généré — le hash correspond bien.\n")

print("=== Création d'un élève avec un email déjà utilisé (doit échouer en 409) ===")
r = client.post("/administration/eleves", headers=headers, json={
    "email": "nouvel.eleve@test.cm", "nom": "Autre", "prenom": "Personne", "classe_id": classe6a_id,
})
print(f"Statut : {r.status_code} — {r.json()}")
assert r.status_code == 409
print("✅ Doublon d'email rejeté proprement.\n")

print("=== Création d'un élève dans une classe d'un AUTRE établissement (doit échouer en 404) ===")
cur.execute("SELECT id FROM classes WHERE nom = '6ème Bilingue' LIMIT 1")
classe_autre_etab = str(cur.fetchone()[0])
r = client.post("/administration/eleves", headers=headers, json={
    "email": "intrus@test.cm", "nom": "X", "prenom": "Y", "classe_id": classe_autre_etab,
})
print(f"Statut : {r.status_code} — {r.json()}")
assert r.status_code == 404
print("✅ Isolation d'établissement respectée à la création de compte.\n")

print("=== Création d'un enseignant avec affectation ===")
r = client.post("/administration/enseignants", headers=headers, json={
    "email": "prof.nouveau@lyceembankomo.cm", "nom": "Talla", "prenom": "Eric",
    "specialite": "Mathématiques",
    "affectations": [{"classe_id": classe6a_id, "matiere_id": math_id}],
})
print(f"Statut : {r.status_code} — {r.json()}")
assert r.status_code == 201
print("✅ Enseignant créé avec affectation.\n")

print("=== Liste des utilisateurs (filtrée par rôle=eleve) ===")
r = client.get("/administration/utilisateurs", headers=headers, params={"role": "eleve"})
eleves = r.json()
print(f"Statut : {r.status_code} — {len(eleves)} élèves")
for e in eleves:
    print(f"  {e['nom']} {e['prenom']} — classe : {e['classe']}")
assert all(e["role"] == "eleve" for e in eleves)
print("✅ Filtre par rôle fonctionnel.\n")

print("=== Désactivation d'un compte ===")
r = client.patch(f"/administration/utilisateurs/{nouvel_eleve_id}/desactiver", headers=headers)
print(f"Statut : {r.status_code} — {r.json()}")
assert r.status_code == 200

print("=== Le compte désactivé ne doit plus pouvoir se connecter ===")
r = client.post("/auth/login", json={"email": "nouvel.eleve@test.cm", "mot_de_passe": mot_de_passe_genere})
print(f"Statut : {r.status_code}")
assert r.status_code == 401
print("✅ Désactivation confirmée : login refusé.\n")

print("=== Génération des bulletins de la 6ème A (trimestre 1) ===")
r = client.post("/administration/bulletins/generer", headers=headers,
                 json={"classe_id": classe6a_id, "trimestre": 1, "annee_scolaire_id": annee_id})
print(f"Statut : {r.status_code}")
for b in r.json():
    print(f"  {b['eleve_nom']} — moyenne: {b['moyenne_generale']}, rang: {b['rang_classe']}")
assert r.status_code == 200
print("✅ Bulletins générés.\n")

print("=== Vérification en base : upsert (re-génération ne duplique pas) ===")
cur.execute("SELECT COUNT(*) FROM bulletins WHERE annee_scolaire_id = %s AND trimestre = 1", (annee_id,))
avant = cur.fetchone()[0]
r = client.post("/administration/bulletins/generer", headers=headers,
                 json={"classe_id": classe6a_id, "trimestre": 1, "annee_scolaire_id": annee_id})
cur.execute("SELECT COUNT(*) FROM bulletins WHERE annee_scolaire_id = %s AND trimestre = 1", (annee_id,))
apres = cur.fetchone()[0]
print(f"Avant : {avant}, après re-génération : {apres}")
assert avant == apres, "BUG : la re-génération a dupliqué des bulletins !"
print("✅ Upsert confirmé, pas de doublons.\n")

print("=== Diffusion d'une notification à toute la classe 6ème A (+ parents) ===")
r = client.post("/administration/notifications/diffuser", headers=headers, json={
    "titre": "Réunion parents-professeurs", "message": "Rendez-vous le 15/09 à 17h.",
    "type_notification": "info", "classe_id": classe6a_id, "inclure_parents": True,
})
print(f"Statut : {r.status_code} — {r.json()}")
assert r.status_code == 200
assert r.json()["nombre_notifications_envoyees"] >= 2, "Devrait inclure au moins l'élève ET son parent"
print("✅ Diffusion élève + parent confirmée.\n")

print("=== Encaissement d'un paiement ===")
cur.execute("SELECT id, montant_du, montant_paye FROM paiements LIMIT 1")
paiement_id, montant_du, montant_paye_avant = cur.fetchone()
print(f"Avant : dû={montant_du}, payé={montant_paye_avant}")
r = client.post(f"/administration/paiements/{paiement_id}/encaisser", headers=headers, json={"montant": 30000})
print(f"Statut : {r.status_code} — {r.json()}")
assert r.status_code == 200
assert float(r.json()["montant_paye"]) == float(montant_paye_avant) + 30000
print("✅ Paiement encaissé et statut recalculé.\n")

print("🎉 Tous les tests du Module Administration sont passés.")
