import os
import torch
from pydub import AudioSegment
from pydub.effects import normalize
from transformers import pipeline
from qwen_tts import Qwen3TTSModel


def get_device() -> str:
    return "mps" if torch.backends.mps.is_available() else "cpu"


def convert_to_wav(audio_path: str) -> str | None:
    """Convert audio to wav and normalize volume. Caches the result by mtime.

    Always normalizes (even if already .wav) to ensure consistent volume
    for TTS reference audio quality.
    """
    file_name, _ = os.path.splitext(audio_path)
    target_path = f"{file_name}_converted.wav"

    if os.path.exists(target_path) and os.path.getmtime(target_path) >= os.path.getmtime(audio_path):
        return target_path

    try:
        audio = normalize(AudioSegment.from_file(audio_path))
        audio.export(target_path, format="wav")
        return target_path
    except Exception as e:
        print(f"[!] Audio conversion error: {e}")
        return None


def load_tts_model(device: str) -> Qwen3TTSModel:
    """Load Qwen3-TTS model from local files."""
    print(f"[*] Loading Qwen3-TTS model on {device}...")
    model = Qwen3TTSModel.from_pretrained(
        ".",
        device_map=device,
        dtype=torch.float32,
        local_files_only=True,
    )
    print("[*] TTS model loaded.")
    return model


def load_stt_model(device: str):
    """Load Whisper-tiny for auto-transcription."""
    print("[*] Loading Whisper-tiny STT model...")
    model = pipeline(
        "automatic-speech-recognition",
        model="openai/whisper-tiny",
        device=device,
    )
    print("[*] STT model loaded.")
    return model
