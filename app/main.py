"""FastAPI: orquestra gravação, transcrição e análise das reuniões."""

from __future__ import annotations

import os
import threading
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app import db
from app.analyze import analyze_transcript
from app.audio_capture import MicRecorder, StreamRecorder, find_device_index, list_devices
from app.auto_listen import AutoListener
from app.merge import format_transcript, merge_transcripts
from app.project_context import build_context, list_project_names
from app.transcribe import transcribe_wav

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

FRONTEND_DIR = BASE_DIR / "frontend"
RECORDINGS_DIR = BASE_DIR / "data" / "recordings"
WHISPER_MODEL_PATH = BASE_DIR / os.environ.get("WHISPER_MODEL_PATH", "data/models/ggml-medium.bin")
VOLTBRAS_DIR = os.environ.get("VOLTBRAS_DIR", "/Users/sls/voltbras")
MIC_SPEAKER_NAME = os.environ.get("MIC_SPEAKER_NAME", "Bruno Sales")
SYSTEM_AUDIO_DEVICE_NAME = os.environ.get("SYSTEM_AUDIO_DEVICE_NAME", "BlackHole 2ch")
AUTO_LISTEN = os.environ.get("AUTO_LISTEN", "1") == "1"
AUTO_LISTEN_START_SECONDS = float(os.environ.get("AUTO_LISTEN_START_SECONDS", 5))
AUTO_LISTEN_STOP_SECONDS = float(os.environ.get("AUTO_LISTEN_STOP_SECONDS", 30))
AUTO_LISTEN_THRESHOLD = float(os.environ.get("AUTO_LISTEN_THRESHOLD", 0.01))

_state_lock = threading.Lock()
_current_meeting_id: Optional[str] = None

system_monitor: Optional[StreamRecorder] = None
mic_recorder = MicRecorder()
auto_listener: Optional[AutoListener] = None


def _meeting_dir(meeting_id: str) -> Path:
    d = RECORDINGS_DIR / meeting_id
    d.mkdir(parents=True, exist_ok=True)
    return d


def start_meeting() -> str:
    global _current_meeting_id
    with _state_lock:
        if _current_meeting_id is not None:
            return _current_meeting_id
        meeting_id = uuid.uuid4().hex[:12]
        d = _meeting_dir(meeting_id)
        mic_path = d / "mic.wav"
        system_path = d / "system.wav"
        started_at = datetime.now(timezone.utc).isoformat()

        db.create_meeting(meeting_id, started_at, str(mic_path), str(system_path))
        mic_recorder.start(mic_path)
        if system_monitor is not None:
            system_monitor.start_writing(system_path)

        _current_meeting_id = meeting_id
        return meeting_id


def stop_meeting() -> Optional[str]:
    global _current_meeting_id
    with _state_lock:
        meeting_id = _current_meeting_id
        if meeting_id is None:
            return None

        mic_recorder.stop()
        if system_monitor is not None:
            system_monitor.stop_writing()

        db.set_ended(meeting_id, datetime.now(timezone.utc).isoformat())
        db.set_status(meeting_id, "transcribing")
        _current_meeting_id = None

    threading.Thread(target=_process_meeting, args=(meeting_id,), daemon=True).start()
    return meeting_id


def _process_meeting(meeting_id: str) -> None:
    meeting = db.get_meeting(meeting_id)
    try:
        mic_segments = transcribe_wav(Path(meeting["mic_path"]), WHISPER_MODEL_PATH)
        system_segments = transcribe_wav(Path(meeting["system_path"]), WHISPER_MODEL_PATH)
        merged = merge_transcripts(mic_segments, system_segments, mic_speaker=MIC_SPEAKER_NAME)
        db.save_transcript(meeting_id, merged)
        db.set_status(meeting_id, "analyzing")

        transcript_text = format_transcript(merged)
        context = build_context(VOLTBRAS_DIR)
        known_projects = list_project_names(VOLTBRAS_DIR)
        analysis = analyze_transcript(transcript_text, context, known_projects)
        db.save_analysis(meeting_id, analysis)
    except Exception as exc:  # noqa: BLE001 - grava qualquer falha do pipeline para exibir no dashboard
        db.set_status(meeting_id, "error", error_message=str(exc))


def _startup() -> None:
    global system_monitor, auto_listener
    db.init_db()

    device_index = find_device_index(SYSTEM_AUDIO_DEVICE_NAME)
    if device_index is None:
        print(
            f"[aviso] Dispositivo de áudio de sistema '{SYSTEM_AUDIO_DEVICE_NAME}' não encontrado. "
            "Complete o setup do BlackHole (veja README.md). Gravação manual/automática ficará indisponível."
        )
        return

    system_monitor = StreamRecorder(device_index)
    system_monitor.open()

    if AUTO_LISTEN:
        auto_listener = AutoListener(
            monitor=system_monitor,
            threshold=AUTO_LISTEN_THRESHOLD,
            start_seconds=AUTO_LISTEN_START_SECONDS,
            stop_seconds=AUTO_LISTEN_STOP_SECONDS,
            poll_interval=0.5,
            on_start=start_meeting,
            on_stop=stop_meeting,
        )
        auto_listener.start()


def _shutdown() -> None:
    if auto_listener is not None:
        auto_listener.stop()
    if system_monitor is not None:
        system_monitor.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    _startup()
    yield
    _shutdown()


app = FastAPI(title="Assistente de Reuniões", lifespan=lifespan)


@app.get("/")
def index():
    return FileResponse(FRONTEND_DIR / "index.html")


app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")


@app.get("/api/devices")
def api_devices():
    return [
        {"index": i, "name": d["name"], "max_input_channels": d["max_input_channels"]}
        for i, d in enumerate(list_devices())
    ]


@app.post("/api/meetings/start")
def api_start():
    if system_monitor is None:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Dispositivo '{SYSTEM_AUDIO_DEVICE_NAME}' não encontrado. "
                "Configure o BlackHole e o Multi-Output Device (veja README.md)."
            ),
        )
    meeting_id = start_meeting()
    if auto_listener is not None:
        auto_listener.notify_external_start()
    return {"id": meeting_id, "status": "recording"}


@app.post("/api/meetings/{meeting_id}/stop")
def api_stop(meeting_id: str):
    with _state_lock:
        active = _current_meeting_id
    if active != meeting_id:
        raise HTTPException(status_code=400, detail="Essa reunião não está em gravação.")
    stop_meeting()
    if auto_listener is not None:
        auto_listener.notify_external_stop()
    return {"id": meeting_id, "status": "transcribing"}


@app.get("/api/meetings")
def api_list():
    return db.list_meetings()


@app.get("/api/meetings/{meeting_id}")
def api_get(meeting_id: str):
    meeting = db.get_meeting(meeting_id)
    if meeting is None:
        raise HTTPException(status_code=404, detail="Reunião não encontrada")
    return meeting


@app.get("/api/meetings/{meeting_id}/status")
def api_status(meeting_id: str):
    meeting = db.get_meeting(meeting_id)
    if meeting is None:
        raise HTTPException(status_code=404, detail="Reunião não encontrada")
    return {"id": meeting_id, "status": meeting["status"], "error_message": meeting.get("error_message")}
