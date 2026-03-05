"""Next Best Action — FastAPI app backed by Lakebase Autoscale."""

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from server.db import db
from server.routes.actions import router as actions_router
from server.routes.contacts import router as contacts_router
from server.routes.genie import router as genie_router

app = FastAPI(title="Next Best Action", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(actions_router)
app.include_router(contacts_router)
app.include_router(genie_router)


@app.on_event("shutdown")
async def shutdown() -> None:
    await db.close()


# Serve React frontend
frontend_dir = os.path.join(os.path.dirname(__file__), "frontend", "dist")
if os.path.exists(frontend_dir):
    assets_dir = os.path.join(frontend_dir, "assets")
    if os.path.exists(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        if full_path.startswith("api/"):
            return None  # let FastAPI handle API routes
        path = os.path.join(frontend_dir, full_path)
        if os.path.isfile(path):
            return FileResponse(path)
        return FileResponse(os.path.join(frontend_dir, "index.html"))
