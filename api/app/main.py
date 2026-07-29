from fastapi import FastAPI

from .routers import auth, exercices, eleve, direction, administration, parent

app = FastAPI(
    title="ÉduAI Afrique — API",
    description="Modules Enseignant, Élève, Direction, Administration et Parent.",
    version="0.1.0",
)

app.include_router(auth.router)
app.include_router(exercices.router)
app.include_router(eleve.router)
app.include_router(direction.router)
app.include_router(administration.router)
app.include_router(parent.router)


@app.get("/healthz")
def healthz():
    return {"statut": "ok"}
