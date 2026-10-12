from fastapi import FastAPI

app = FastAPI(
    title="GitHub Repository Analytics",
    description="An API for analyzing GitHub repositories.",
    version="0.1.0"
)


@app.get("/")
def root():
    return {"message": "GitHub Repository Analytics API"}

@app.get("/health")
def health_check(): 
    return {"status": "ok"}