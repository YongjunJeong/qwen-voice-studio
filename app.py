import asyncio
import torch
import soundfile as sf
import os
import time
from dataclasses import dataclass
from datetime import datetime
from functools import partial
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uvicorn

from engine import get_device, convert_to_wav, load_tts_model, load_stt_model

ALLOWED_EXTENSIONS = {".m4a", ".wav", ".mp3", ".flac"}
MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MB
UPLOADS_DIR = os.path.abspath("uploads")


@dataclass
class AppState:
    tts_model: object = None
    stt_model: object = None
    device: str = ""


state = AppState()


@asynccontextmanager
async def lifespan(app: FastAPI):
    state.device = get_device()
    print(f"\n[*] Using device: {state.device}")
    print("[1/2] Loading Qwen3-TTS model...")
    state.tts_model = load_tts_model(state.device)
    print("[2/2] Loading Whisper-tiny STT model...")
    state.stt_model = load_stt_model(state.device)
    print(f"[*] All models ready on {state.device}!")
    yield


app = FastAPI(title="Qwen Voice Studio", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

for dir_name in ["static", "uploads", "generations"]:
    os.makedirs(dir_name, exist_ok=True)

app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/generations", StaticFiles(directory="generations"), name="generations")


@app.get("/")
def serve_home():
    return FileResponse("static/index.html")

@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    from fastapi.responses import Response
    return Response(content=b"", media_type="image/x-icon")


def _run_prepare_audio(stt_model, temp_path: str) -> tuple[str | None, str]:
    """Convert + normalize audio, then transcribe. Runs in thread pool."""
    wav_path = convert_to_wav(temp_path)
    if not wav_path:
        return None, ""

    transcribed_text = ""
    if stt_model:
        try:
            result = stt_model(wav_path, generate_kwargs={"language": "korean"})
            transcribed_text = result["text"].strip()
            print(f"[*] Auto-transcribed: {transcribed_text}")
        except Exception as e:
            print(f"[!] STT error: {e}")

    return wav_path, transcribed_text


@app.post("/api/upload")
async def upload_reference_audio(file: UploadFile = File(...)):
    """Uploads an m4a/wav file, converts it, and returns the usable path."""
    contents = await file.read()
    if len(contents) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="파일이 너무 큽니다. 최대 10MB까지 가능합니다.")

    original_name = os.path.basename(file.filename or "")
    _, ext = os.path.splitext(original_name)
    if ext.lower() not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"지원하지 않는 파일 형식입니다. 허용: {', '.join(ALLOWED_EXTENSIONS)}")

    safe_filename = original_name.replace(" ", "_")
    temp_path = os.path.join("uploads", safe_filename)

    with open(temp_path, "wb") as buffer:
        buffer.write(contents)

    loop = asyncio.get_running_loop()
    wav_path, transcribed_text = await loop.run_in_executor(
        None, partial(_run_prepare_audio, state.stt_model, temp_path)
    )

    if not wav_path:
        raise HTTPException(status_code=500, detail="오디오 파일 변환에 실패했습니다.")

    return {
        "message": "File prepared successfully",
        "ref_audio_path": wav_path,
        "original_name": file.filename,
        "auto_transcription": transcribed_text
    }


def _run_tts(model, text, ref_audio, ref_text, output_path, device):
    """Synchronous TTS inference — runs in a thread pool to avoid blocking the event loop."""
    with torch.inference_mode():
        wavs, sr = model.generate_voice_clone(
            text=text,
            language="Auto",
            ref_audio=ref_audio,
            ref_text=ref_text,
        )
    sf.write(output_path, wavs[0], sr)
    if device == "mps":
        torch.mps.empty_cache()


@app.post("/api/generate")
async def generate_audio(text: str = Form(...), ref_text: str = Form(...), ref_audio_path: str = Form(...)):
    """Generates audio for the requested text using the uploaded ref."""
    if not state.tts_model:
        raise HTTPException(status_code=503, detail="Model is loading. Please try again in a few seconds.")

    abs_ref = os.path.abspath(ref_audio_path)
    if not abs_ref.startswith(UPLOADS_DIR + os.sep):
        raise HTTPException(status_code=400, detail="잘못된 레퍼런스 오디오 경로입니다.")
    if not os.path.exists(abs_ref):
        raise HTTPException(status_code=404, detail="레퍼런스 오디오 파일을 찾을 수 없습니다.")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_filename = f"out_{timestamp}.wav"
    output_path = os.path.join("generations", output_filename)

    try:
        start_time = time.perf_counter()
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(
            None,
            partial(_run_tts, state.tts_model, text, abs_ref, ref_text, output_path, state.device)
        )
        end_time = time.perf_counter()

        return {
            "success": True,
            "filename": output_filename,
            "url": f"/generations/{output_filename}",
            "time_taken": f"{end_time - start_time:.2f}",
            "text": text,
            "timestamp": datetime.now().strftime("%I:%M %p")
        }
    except Exception as e:
        print(f"Generation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    print("\nStarting Qwen Voice Studio Web Server...")
    print("Open http://localhost:8000 in your browser.")
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=False)
