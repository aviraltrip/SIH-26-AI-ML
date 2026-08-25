from fastapi import FastAPI

app = FastAPI(
    title="SIH 26 AI-ML Stuff",
    description="Mock API for AI/ML Stuff",
    version="1.0.0"
)

@app.get("/")
def read_root():
    return {
        "status": "online",
        "message": "Lmao Hi",
        "docs_url": "/docs"
    }

@app.get("/health")
def health_check():
    return {"status": "healthy"}
