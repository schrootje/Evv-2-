from fastapi import FastAPI
from fastapi.responses import RedirectResponse

from app.database import engine
from app.models import training as training_models
from app.routers import auth, financial, training

training_models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="EVV App",
    description="Voetbal trainingen aanwezigheidsregistratie + Exact Online koppeling.",
    version="2.0.0",
)

app.include_router(training.router)
app.include_router(auth.router)
app.include_router(financial.router)


@app.get("/", tags=["Status"])
def root():
    return RedirectResponse(url="/training/")
