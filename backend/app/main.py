import socketio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.config import FRONTEND_URL
from app.database import connect_db, close_db
from app.sio_instance import sio
from app.routes import sessions, checkins, questions, clusters


@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_db()
    yield
    await close_db()


app = FastAPI(title="AskSafe API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_URL, "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Socket.IO server (imported from sio_instance to avoid circular imports)
sio_app = socketio.ASGIApp(sio, app)

# Register REST routes
app.include_router(sessions.router, prefix="/api/sessions", tags=["sessions"])
app.include_router(checkins.router, prefix="/api/checkins", tags=["checkins"])
app.include_router(questions.router, prefix="/api/questions", tags=["questions"])
app.include_router(clusters.router, prefix="/api/clusters", tags=["clusters"])
