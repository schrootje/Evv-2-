from fastapi import FastAPI

from app.routers import auth, financial

app = FastAPI(
    title="Exact Online API",
    description="FastAPI wrapper voor de Exact Online REST API — financieel/grootboek module.",
    version="1.0.0",
)

app.include_router(auth.router)
app.include_router(financial.router)


@app.get("/", tags=["Status"])
def root():
    return {"status": "ok", "docs": "/docs"}
