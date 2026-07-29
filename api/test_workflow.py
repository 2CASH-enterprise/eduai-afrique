import sys
sys.path.insert(0, ".")
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

r = client.post("/auth/login", json={"email": "prof.test@lyceembankomo.cm", "mot_de_passe": "motdepasse123"})
token = r.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}

print("=== Liste des exercices à valider (périmètre : 6ème / Mathématiques uniquement) ===")
r = client.get("/enseignant/exercices/a-valider", headers=headers)
exercices = r.json()
print(f"Statut : {r.status_code} — {len(exercices)} exercices trouvés")
for ex in exercices[:3]:
    print(f"  [{ex['niveau']} / {ex['matiere']}] {ex['theme']} — {ex['enonce'][:60]}...")
matieres_niveaux_vus = {(ex["niveau"], ex["matiere"]) for ex in exercices}
print(f"Couples (niveau, matière) présents dans la liste : {matieres_niveaux_vus}")
assert matieres_niveaux_vus == {("6ème", "Mathématiques")}, "FUITE DE PÉRIMÈTRE DÉTECTÉE !"
print("✅ Contrôle de périmètre confirmé : aucune fuite vers d'autres matières/niveaux.\n")

premier_id = exercices[0]["id"]

print(f"=== Tentative de validation d'un exercice HORS périmètre (doit échouer en 403) ===")
r = client.get("/enseignant/exercices/a-valider", headers=headers)  # on récupère un ID valide d'abord
import psycopg2
conn = psycopg2.connect(dbname="eduai_test", user="postgres", host="/var/run/postgresql")
cur = conn.cursor()
cur.execute("SELECT id FROM exercices WHERE matiere_id = (SELECT id FROM matieres WHERE nom='SVT') LIMIT 1")
id_hors_perimetre = cur.fetchone()
if id_hors_perimetre:
    r = client.post(f"/enseignant/exercices/{id_hors_perimetre[0]}/valider", headers=headers)
    print(f"Statut : {r.status_code} — {r.json()}")
    assert r.status_code == 403, "LE CONTRÔLE D'ACCÈS A ÉCHOUÉ — un enseignant a pu valider hors périmètre !"
    print("✅ Rejet 403 confirmé.\n")

print(f"=== Modification d'un exercice avant validation (correction d'une coquille) ===")
r = client.patch(f"/enseignant/exercices/{premier_id}", headers=headers,
                  json={"corrige": "CORRIGÉ MODIFIÉ PAR L'ENSEIGNANT POUR LE TEST"})
print(f"Statut : {r.status_code}")
print(f"Corrigé mis à jour : {r.json()['corrige']}")
assert r.json()["corrige"] == "CORRIGÉ MODIFIÉ PAR L'ENSEIGNANT POUR LE TEST"
print("✅ Modification confirmée.\n")

print(f"=== Validation de l'exercice modifié ===")
r = client.post(f"/enseignant/exercices/{premier_id}/valider", headers=headers)
print(f"Statut : {r.status_code} — {r.json()}")
assert r.json()["statut"] == "valide"
print("✅ Validation confirmée.\n")

print(f"=== Nouvelle tentative de validation du même exercice (doit échouer en 409, déjà validé) ===")
r = client.post(f"/enseignant/exercices/{premier_id}/valider", headers=headers)
print(f"Statut : {r.status_code} — {r.json()}")
assert r.status_code == 409
print("✅ Conflit détecté correctement.\n")

deuxieme_id = exercices[1]["id"]
print(f"=== Rejet d'un exercice sans motif (doit échouer en 422, motif obligatoire) ===")
r = client.post(f"/enseignant/exercices/{deuxieme_id}/rejeter", headers=headers, json={"motif": ""})
print(f"Statut : {r.status_code}")
assert r.status_code == 422
print("✅ Validation Pydantic du motif obligatoire confirmée.\n")

print(f"=== Rejet d'un exercice avec motif ===")
r = client.post(f"/enseignant/exercices/{deuxieme_id}/rejeter", headers=headers,
                 json={"motif": "Contexte peu clair pour des élèves de 6ème, à reformuler"})
print(f"Statut : {r.status_code} — {r.json()}")
assert r.json()["statut"] == "rejete"
print("✅ Rejet confirmé.\n")

print("=== Vérification finale en base ===")
cur.execute("SELECT statut, liens->>'motif_rejet' FROM exercices WHERE id = %s", (deuxieme_id,))
print("Statut + motif stocké :", cur.fetchone())

cur.execute("SELECT statut, valide_par_id IS NOT NULL, date_validation IS NOT NULL FROM exercices WHERE id = %s", (premier_id,))
print("Exercice validé :", cur.fetchone())

print("\n🎉 Tous les tests du workflow sont passés.")
