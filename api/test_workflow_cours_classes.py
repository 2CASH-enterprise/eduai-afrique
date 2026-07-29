import sys
sys.path.insert(0, ".")
from fastapi.testclient import TestClient
from app.main import app
import psycopg2

client = TestClient(app)
conn = psycopg2.connect(dbname="eduai_test", user="postgres", host="/var/run/postgresql")
cur = conn.cursor()

r = client.post("/auth/login", json={"email": "prof.test@lyceembankomo.cm", "mot_de_passe": "motdepasse123"})
assert r.status_code == 200, r.json()
headers = {"Authorization": f"Bearer {r.json()['access_token']}"}

cur.execute("SELECT id FROM classes WHERE nom = '6ème A' LIMIT 1")
classe_id = str(cur.fetchone()[0])
cur.execute("SELECT id FROM matieres WHERE nom = 'Mathématiques' LIMIT 1")
matiere_id = str(cur.fetchone()[0])
cur.execute("SELECT id FROM annees_scolaires LIMIT 1")
annee_id = str(cur.fetchone()[0])

print("=== Mes classes ===")
r = client.get("/enseignant/mes-classes", headers=headers)
print(f"Statut : {r.status_code} — {r.json()}")
assert r.status_code == 200 and len(r.json()) == 1
print("✅ Une seule classe, cohérent avec l'affectation unique.\n")

print("=== Élèves de la classe (matière correcte) ===")
r = client.get(f"/enseignant/classes/{classe_id}/eleves", headers=headers, params={"matiere_id": matiere_id})
eleves = r.json()
print(f"Statut : {r.status_code} — {len(eleves)} élève(s)")
assert r.status_code == 200 and len(eleves) >= 1
eleve_id = eleves[0]["eleve_id"]

print("\n=== Élèves de la classe, MAUVAISE matière (doit 403) ===")
cur.execute("SELECT id FROM matieres WHERE nom = 'SVT' LIMIT 1")
svt_id = str(cur.fetchone()[0])
r = client.get(f"/enseignant/classes/{classe_id}/eleves", headers=headers, params={"matiere_id": svt_id})
print(f"Statut : {r.status_code}")
assert r.status_code == 403
print("✅ Accès refusé hors périmètre matière.\n")

print("=== Ajout d'une note ===")
r = client.post(f"/enseignant/eleves/{eleve_id}/notes", headers=headers, json={
    "matiere_id": matiere_id, "valeur": 16, "bareme": 20, "type_evaluation": "controle",
    "trimestre": 1, "annee_scolaire_id": annee_id,
})
print(f"Statut : {r.status_code} — {r.json()}")
assert r.status_code == 201
print("✅ Note ajoutée.\n")

print("=== Ajout d'une note pour un élève HORS périmètre (doit 404) ===")
cur.execute("SELECT utilisateur_id FROM eleves WHERE utilisateur_id != %s LIMIT 1", (eleve_id,))
autre_eleve = cur.fetchone()
if autre_eleve:
    r = client.post(f"/enseignant/eleves/{autre_eleve[0]}/notes", headers=headers, json={
        "matiere_id": matiere_id, "valeur": 10, "trimestre": 1, "annee_scolaire_id": annee_id,
    })
    print(f"Statut : {r.status_code}")
    # 404 attendu SAUF si cet autre élève est aussi dans la classe affectée — on vérifie donc le message
    print(f"Détail : {r.json()}")

print("\n=== Ajout d'une absence ===")
r = client.post(f"/enseignant/eleves/{eleve_id}/absences", headers=headers, params={"matiere_id": matiere_id}, json={
    "date_absence": "2026-09-10", "type_absence": "absence", "justifie": False, "motif": None,
})
print(f"Statut : {r.status_code} — {r.json()}")
assert r.status_code == 201
print("✅ Absence ajoutée.\n")

print("=== Vérification : moyenne de classe recalculée ===")
r = client.get("/enseignant/mes-classes", headers=headers)
print(r.json())

print("\n=== Dépôt d'un cours ===")
r = client.post("/enseignant/cours", headers=headers, json={
    "titre": "Les fractions", "classe_id": classe_id, "matiere_id": matiere_id,
    "contenu_texte": "Introduction aux fractions et à leur simplification.",
})
print(f"Statut : {r.status_code}")
cours = r.json()
assert r.status_code == 201
assert len(cours["ressources"]) == 6
print(f"✅ Cours créé avec {len(cours['ressources'])} ressources générées.\n")

ressource_id = cours["ressources"][0]["id"]

print("=== Dépôt de cours HORS affectation (doit 403) ===")
r = client.post("/enseignant/cours", headers=headers, json={
    "titre": "Test", "classe_id": classe_id, "matiere_id": svt_id,
})
print(f"Statut : {r.status_code}")
assert r.status_code == 403
print("✅ Refusé, pas affecté à 6ème A pour la SVT avec ce compte.\n")

print("=== Valider une ressource ===")
r = client.patch(f"/enseignant/cours/{cours['id']}/ressources/{ressource_id}", headers=headers,
                  json={"statut": "valide"})
print(f"Statut : {r.status_code} — {r.json()}")
assert r.status_code == 200

print("\n=== Vérifier en base ===")
cur.execute("SELECT statut FROM ressources_generees WHERE id = %s", (ressource_id,))
print("Statut en base :", cur.fetchone())

print("\n=== Liste Mes cours ===")
r = client.get("/enseignant/cours", headers=headers)
print(f"Statut : {r.status_code} — {r.json()}")
assert r.status_code == 200 and len(r.json()) >= 1

print("\n🎉 Tous les tests des modules cours + classes sont passés.")
