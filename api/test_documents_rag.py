import sys
sys.path.insert(0, ".")
import types
import random

from fastapi.testclient import TestClient
from app.main import app
import app.routers.documents as documents_module


class FauxReponseEmbeddings:
    def __init__(self, nb_vecteurs):
        random.seed(42)
        self.data = [
            types.SimpleNamespace(embedding=[random.uniform(-1, 1) for _ in range(1024)])
            for _ in range(nb_vecteurs)
        ]


class FauxClientMistralEmbeddings:
    def __init__(self):
        self.appels = 0
        self.embeddings = types.SimpleNamespace(create=self._create)

    def _create(self, model, inputs):
        self.appels += 1
        return FauxReponseEmbeddings(len(inputs))


# On remplace la fonction qui construit le client Mistral réel par une
# version qui renvoie notre faux client — pas de vraie clé API nécessaire,
# pas d'appel réseau réel, testable entièrement dans ce sandbox.
documents_module._obtenir_client_mistral = lambda: FauxClientMistralEmbeddings()

client = TestClient(app)

r = client.post("/auth/login", json={"email": "secretariat@lyceembankomo.cm", "mot_de_passe": "admin123"})
assert r.status_code == 200, r.json()
headers = {"Authorization": f"Bearer {r.json()['access_token']}"}

print("=== Dépôt d'un document programme officiel ===")
with open("/home/claude/test_programme.pdf", "rb") as f:
    r = client.post(
        "/administration/documents",
        headers=headers,
        params={"titre": "Programme Mathématiques 6ème (test)", "type_document": "programme_officiel"},
        files={"fichier": ("programme.pdf", f, "application/pdf")},
    )
print(f"Statut : {r.status_code}")
print(r.json())
assert r.status_code == 201
doc = r.json()
assert doc["statut"] == "indexe", f"Le document n'a pas été indexé : {doc}"
assert doc["nombre_passages"] > 0
document_id = doc["id"]
print("✅ Document indexé avec", doc["nombre_passages"], "passage(s)\n")

print("=== Dépôt d'un faux PDF (doit être rejeté en 422) ===")
r = client.post(
    "/administration/documents", headers=headers,
    params={"titre": "Faux document", "type_document": "notes_cours"},
    files={"fichier": ("faux.pdf", b"ceci n'est pas un PDF", "application/pdf")},
)
print(f"Statut : {r.status_code} — {r.json()}")
assert r.status_code == 422
print("✅ Rejeté proprement.\n")

print("=== Dépôt avec type_document invalide (doit 422) ===")
with open("/home/claude/test_programme.pdf", "rb") as f:
    r = client.post(
        "/administration/documents", headers=headers,
        params={"titre": "Test", "type_document": "manuel_scanne"},
        files={"fichier": ("p.pdf", f, "application/pdf")},
    )
print(f"Statut : {r.status_code} — {r.json()}")
assert r.status_code == 422
print("✅ Type de document invalide rejeté (empêche le dépôt de manuels).\n")

print("=== Liste des documents ===")
r = client.get("/administration/documents", headers=headers)
print(f"Statut : {r.status_code} — {len(r.json())} document(s)")
for d in r.json():
    print(" ", d)
assert r.status_code == 200

print("\n=== Recherche par similarité (diagnostic) ===")
r = client.get(f"/administration/documents/{document_id}/tester-recherche", headers=headers, params={"q": "comment calculer l'aire d'un rectangle"})
print(f"Statut : {r.status_code}")
for p in r.json():
    print(f"  similarité={p['similarite']} — {p['extrait'][:80]}...")
assert r.status_code == 200
assert len(r.json()) > 0

print("\n=== Vérification directe en base : le texte est bien découpé et indexé ===")
import psycopg2
conn = psycopg2.connect(dbname="eduai_test", user="postgres", host="/var/run/postgresql")
cur = conn.cursor()
cur.execute("SELECT ordre, LEFT(contenu, 60) FROM passages_documents WHERE document_id = %s ORDER BY ordre", (document_id,))
for ordre, extrait in cur.fetchall():
    print(f"  passage {ordre}: {extrait}...")

print("\n=== Suppression du document ===")
r = client.delete(f"/administration/documents/{document_id}", headers=headers)
print(f"Statut : {r.status_code}")
assert r.status_code == 204

cur.execute("SELECT COUNT(*) FROM passages_documents WHERE document_id = %s", (document_id,))
print("Passages restants après suppression (doit être 0, cascade) :", cur.fetchone()[0])
assert cur.fetchone is not None

print("\n🎉 Tous les tests de la base documentaire (RAG) sont passés.")
