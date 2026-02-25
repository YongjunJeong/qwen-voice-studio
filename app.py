import torch
import soundfile as sf
import os
import time
import shutil
from datetime import datetime
from pydub import AudioSegment
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uvicorn

from qwen_tts import Qwen3TTSModel

@asynccontextmanager
async def lifespan(app: FastAPI):
    global TTS_MODEL, STT_MODEL, DEVICE
    TTS_MODEL, STT_MODEL, DEVICE = load_models()
    yield

app = FastAPI(title="Qwen Voice Studio", lifespan=lifespan)

# CORS config
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Core Directories
for dir_name in ["static", "uploads", "generations"]:
    os.makedirs(dir_name, exist_ok=True)

app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/generations", StaticFiles(directory="generations"), name="generations")

# System State
TTS_MODEL = None
STT_MODEL = None
DEVICE = None

def convert_to_wav(audio_path):
    """Convert audio to wav and normalize volume so the reference audio is clearly audible."""
    file_name, file_ext = os.path.splitext(audio_path)
    
    target_path = f"{file_name}_converted.wav"
    
    if os.path.exists(target_path) and os.path.getmtime(target_path) >= os.path.getmtime(audio_path):
        return target_path

    try:
        audio = AudioSegment.from_file(audio_path)
        
        # Normalize audio volume to maximize amplitude (fixes the quiet audio issue)
        from pydub.effects import normalize
        audio = normalize(audio)
        
        audio.export(target_path, format="wav")
        return target_path
    except Exception as e:
        print(f"Error during conversion/normalization: {e}")
        return None

def load_models():
    print(f"\n[1/2] Loading Qwen3-TTS model for Web UI...")
    device = "mps" if torch.backends.mps.is_available() else "cpu"
    
    tts_model = Qwen3TTSModel.from_pretrained(
        ".", 
        device_map=device,
        dtype=torch.float32,
        local_files_only=True,
    )
    
    print(f"\n[2/2] Loading lightweight STT model (Whisper-tiny) for auto-transcription...")
    from transformers import pipeline
    stt_model = pipeline(
        "automatic-speech-recognition",
        model="openai/whisper-tiny",
        device=device
    )
    
    print(f"[*] Models loaded successfully on {device}!")
    return tts_model, stt_model, device

@app.get("/")
def serve_home():
    return FileResponse("static/index.html")

@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    from fastapi.responses import Response
    return Response(content=b"", media_type="image/x-icon")


@app.post("/api/upload")
async def upload_reference_audio(file: UploadFile = File(...)):
    """Uploads an m4a/wav file, converts it, and returns the usable path."""
    safe_filename = file.filename.replace(" ", "_")
    temp_path = os.path.join("uploads", safe_filename)
    
    with open(temp_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    wav_path = convert_to_wav(temp_path)
    if not wav_path:
        raise HTTPException(status_code=500, detail="Failed to parse audio format")
        
    # Automatically transcribe the audio using Whisper
    transcribed_text = ""
    if STT_MODEL:
        try:
            result = STT_MODEL(wav_path, generate_kwargs={"language": "korean"})
            transcribed_text = result["text"].strip()
            print(f"[*] Auto-transcribed text: {transcribed_text}")
        except Exception as e:
            print(f"[!] STT Error: {e}")
        
    return {
        "message": "File prepared successfully", 
        "ref_audio_path": wav_path,
        "original_name": file.filename,
        "auto_transcription": transcribed_text
    }

@app.post("/api/generate")
@torch.inference_mode()
async def generate_audio(text: str = Form(...), ref_text: str = Form(...), ref_audio_path: str = Form(...)):
    """Generates audio for the requested text using the uploaded ref."""
    if not TTS_MODEL:
        raise HTTPException(status_code=503, detail="Model is loading. Please try again in a few seconds.")
        
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_filename = f"out_{timestamp}.wav"
    output_path = os.path.join("generations", output_filename)
    
    try:
        start_time = time.perf_counter()
        wavs, sr = TTS_MODEL.generate_voice_clone(
            text=text,
            language="Auto",
            ref_audio=ref_audio_path,
            ref_text=ref_text,
        )
        end_time = time.perf_counter()
        
        sf.write(output_path, wavs[0], sr)
        
        # Free up Mac VRAM to prevent memory leaks across sessions
        if DEVICE == "mps":
            torch.mps.empty_cache()
            
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
