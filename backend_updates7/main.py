from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import get_db
from routes import projects, chainage, slope, upload, review, calculation, audit

app = FastAPI(title="Earthwork Quantity System")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(projects.router)
app.include_router(chainage.router)
app.include_router(slope.router)
app.include_router(upload.router)
app.include_router(review.router)
app.include_router(calculation.router)
app.include_router(audit.router)


@app.get("/")
def home():
    return {"message": "Earthwork API is running!"}


@app.get("/test-db")
def test_db():
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        conn.close()
        return {"message": "PostgreSQL connected successfully!"}
    except Exception as e:
        return {"error": str(e)}
