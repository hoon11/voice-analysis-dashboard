from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse
from datetime import datetime
from pydantic import BaseModel
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
frames_by_session = {}


class AnalysisFrame(BaseModel):
    time_sec: float
    pitch_hz: float
    intensity_db: float
    f1_hz: float
    f2_hz: float
    f3_hz: float
    f4_hz: float
    f5_hz: float
    f6_hz: float


class FramesRequest(BaseModel):
    frames: list[AnalysisFrame]


def error_response(status_code: int, error: str, message: str):
    return JSONResponse(
        status_code=status_code,
        content={"error": error, "message": message},
    )


def average(values: list[float]):
    return sum(values) / len(values)

@app.get("/")
def root():
    return {"status": "ok"}

@app.post("/sessions")
def create_session(data: dict):
    session_id = datetime.now().strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:6]
    data["session_id"] = session_id
    data["created_at"] = datetime.utcnow().isoformat()
    sessions[session_id] = data
    return {"ok": True, "session_id": session_id}

@app.get("/sessions")
def list_sessions():
    return [
        {
            "session_id": s["session_id"],
            "created_at": s["created_at"]
        }
        for s in sessions.values()
    ]

@app.get("/sessions/{session_id}")
def get_session(session_id: str):
    return sessions.get(session_id)


@app.post("/sessions/{session_id}/frames", status_code=201)
def add_session_frames(session_id: str, data: FramesRequest):
    if session_id not in sessions:
        return error_response(404, "session_not_found", "Session not found.")

    if not data.frames:
        return error_response(400, "invalid_frame_data", "frames must not be empty.")

    stored_frames = frames_by_session.setdefault(session_id, [])
    new_frames = [frame.model_dump() for frame in data.frames]
    stored_frames.extend(new_frames)

    return {
        "session_id": session_id,
        "frames_added": len(new_frames),
        "total_frames": len(stored_frames),
        "status": "ok",
    }


@app.get("/sessions/{session_id}/frames")
def get_session_frames(
    session_id: str,
    from_sec: float | None = Query(default=None),
    to_sec: float | None = Query(default=None),
):
    if session_id not in sessions:
        return error_response(404, "session_not_found", "Session not found.")

    frames = frames_by_session.get(session_id, [])

    if from_sec is not None:
        frames = [frame for frame in frames if frame["time_sec"] >= from_sec]

    if to_sec is not None:
        frames = [frame for frame in frames if frame["time_sec"] <= to_sec]

    return {
        "session_id": session_id,
        "frame_interval_sec": 0.02,
        "frames": frames,
    }


@app.get("/sessions/{session_id}/summary")
def get_session_summary(session_id: str):
    if session_id not in sessions:
        return error_response(404, "session_not_found", "Session not found.")

    frames = frames_by_session.get(session_id, [])
    if not frames:
        return error_response(404, "no_frames", "No analysis frames found for this session.")

    pitch_values = [frame["pitch_hz"] for frame in frames]
    intensity_values = [frame["intensity_db"] for frame in frames]

    formants = {
        f"f{index}_avg_hz": round(average([frame[f"f{index}_hz"] for frame in frames]))
        for index in range(1, 7)
    }

    pitch_range = max(pitch_values) - min(pitch_values)
    intensity_range = max(intensity_values) - min(intensity_values)
    f2_avg = formants["f2_avg_hz"]

    return {
        "session_id": session_id,
        "duration_sec": round(max(frame["time_sec"] for frame in frames) + 0.02, 2),
        "frame_count": len(frames),
        "pitch": {
            "avg_hz": round(average(pitch_values), 1),
            "min_hz": min(pitch_values),
            "max_hz": max(pitch_values),
        },
        "intensity": {
            "avg_db": round(average(intensity_values), 1),
            "min_db": min(intensity_values),
            "max_db": max(intensity_values),
        },
        "formants": formants,
        "estimated_quality": {
            "resonance_score": max(0, min(100, round(100 - intensity_range * 3))),
            "stability_score": max(0, min(100, round(100 - pitch_range / 2))),
            "brightness_score": max(0, min(100, round(f2_avg / 25))),
        },
    }
