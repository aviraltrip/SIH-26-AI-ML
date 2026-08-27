from fastapi import FastAPI
from app.routes.jargon import router as jargon_router

app = FastAPI(
    title="SIH 26 AI-ML Stuff",
    description="Stateless AI/ML microservice for scheme matching, document processing, and vernacular advisory.",
    version="1.0.0",
)

# Register routers
app.include_router(jargon_router)


@app.get("/")
def read_root():
    return {
        "status": "online",
        "message": "Lmao Hi",
        "docs_url": "/docs",
    }


@app.get("/health")
def health_check():
    return {"status": "healthy"}
