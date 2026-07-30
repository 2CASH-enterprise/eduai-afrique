from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers import auth, exercices, eleve, direction, administration, parent, cours, classes

app = FastAPI(
    title="ÉduAI Afrique — API",
    description="Modules Enseignant, Élève, Direction, Administration et Parent.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(exercices.router)
app.include_router(eleve.router)
app.include_router(direction.router)
app.include_router(administration.router)
app.include_router(parent.router)
app.include_router(cours.router)
app.include_router(classes.router)


@app.get("/healthz")
def healthz():
    return {"statut": "ok"}
