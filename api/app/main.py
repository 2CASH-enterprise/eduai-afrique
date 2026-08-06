from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .routers import auth, exercices, eleve, direction, administration, parent, cours, classes, etablissement, bulletins_pdf, documents, documents_enseignant, plateforme, invitations, generation_libre, structure_scolaire, classes_personnelles, modules

app = FastAPI(
    title="OskarAI — API",
    description="Modules Enseignant, Élève, Direction, Administration et Parent.",
    version="0.1.0",
)

# CORS : nécessaire pour que les navigateurs autorisent les appels fetch()
# depuis le frontend (origine différente de l'API). allow_origins=["*"] est
# volontairement permissif pour cette phase de développement — à restreindre
# à l'origine réelle du frontend une fois celui-ci déployé sur un domaine fixe.
# allow_credentials=False car l'auth se fait via un header Authorization
# (JWT), pas des cookies — donc pas besoin du mode "credentials" du CORS,
# ce qui permet justement d'utiliser allow_origins=["*"] sans que le
# navigateur ne le rejette (les deux combinés sont invalides en CORS).
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Fichiers uploadés (logo, règlement) — servis tels quels depuis le disque.
# Le dossier est créé automatiquement au premier upload (voir etablissement.py).
DOSSIER_UPLOADS = Path(__file__).resolve().parent.parent / "uploads"
DOSSIER_UPLOADS.mkdir(exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(DOSSIER_UPLOADS)), name="uploads")

app.include_router(auth.router)
app.include_router(exercices.router)
app.include_router(eleve.router)
app.include_router(direction.router)
app.include_router(administration.router)
app.include_router(parent.router)
app.include_router(cours.router)
app.include_router(classes.router)
app.include_router(etablissement.router)
app.include_router(bulletins_pdf.router)
app.include_router(documents.router)
app.include_router(documents_enseignant.router)
app.include_router(plateforme.router)
app.include_router(invitations.router_administration)
app.include_router(invitations.router_enseignant)
app.include_router(generation_libre.router)
app.include_router(structure_scolaire.router)
app.include_router(classes_personnelles.router)
app.include_router(modules.router)


@app.get("/healthz")
def healthz():
    return {"statut": "ok"}
