from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.api.routes import router

app = FastAPI(title="TripAI", version="2.0.0", description="Agentic AI Trip Planner")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(status_code=500, content={"detail": f"Internal server error: {str(exc)}"})


@app.get("/")
async def root():
    return {
        "name": "TripAI",
        "version": "2.0.0",
        "status": "running",
        "docs": "/docs",
    }


@app.on_event("startup")
async def startup():
    print("""
  ╔════════════════════════════════╗
  ║       TripAI v2.0 — Ready      ║
  ║  API:    http://localhost:8000  ║
  ║  Docs:   http://localhost:8000/docs ║
  ║  Health: http://localhost:8000/health ║
  ╚════════════════════════════════╝
    """)
