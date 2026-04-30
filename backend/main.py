from fastapi import FastAPI
from datetime import datetime
import uuid
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

sessions = {}

@app.get("/")
def root():
    return {"status": "ok"}

@app.post("/session")
def create_session(data: dict):
    session_id = datetime.now().strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:6]
    data["session_id"] = session_id
    data["created_at"] = datetime.utcnow().isoformat()
    sessions[session_id] = data
    return {"ok": True, "session_id": session_id}

@app.get("/session")
def list_sessions():
    return [
        {
            "session_id": s["session_id"],
            "created_at": s["created_at"]
        }
        for s in sessions.values()
    ]

@app.get("/session/{session_id}")
def get_session(session_id: str):
    return sessions.get(session_id)