from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.matches import router as matches_router
from backend.app.video_jobs import router as video_jobs_router

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(matches_router)
app.include_router(video_jobs_router)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
