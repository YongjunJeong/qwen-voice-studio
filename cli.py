import torch
import soundfile as sf
import os
import time
from qwen_tts import Qwen3TTSModel
from pydub import AudioSegment

def convert_to_wav(audio_path):
    """Converts non-wav files (like .m4a) to .wav format, caching the result to save time."""
    file_name, file_ext = os.path.splitext(audio_path)
    if file_ext.lower() == ".wav":
        return audio_path

    target_path = f"{file_name}_converted.wav"
    
    # Optimization: Skip conversion if cached output exists and is newer than the source file
    if os.path.exists(target_path):
        if os.path.getmtime(target_path) >= os.path.getmtime(audio_path):
            print(f"[*] Using cached wav conversion: {target_path}")
            return target_path

    print(f"[*] Converting '{audio_path}' to wav format...")
    try:
        audio = AudioSegment.from_file(audio_path)
        audio.export(target_path, format="wav")
        print(f"[*] Conversion complete: {target_path}")
        return target_path
    except Exception as e:
        print(f"[!] Error during conversion: {e}")
        return None

def load_tts_model():
    """Loads the Qwen3-TTS-Base model once into memory."""
    print(f"\n[1/2] Loading model: Qwen/Qwen3-TTS-12Hz-1.7B-Base...")
    device = "mps" if torch.backends.mps.is_available() else "cpu"
    print(f"[*] Using device: {device}")
    
    model = Qwen3TTSModel.from_pretrained(
        ".", 
        device_map=device,
        dtype=torch.float32,
        local_files_only=True,
    )
    print("[*] Model loaded successfully!")
    return model, device

@torch.inference_mode()
def generate_voice(model, text, ref_audio_path, ref_text, output_counter):
    """Generates speech using the already loaded model with gradients disabled."""
    output_path = f"output_{output_counter}.wav"
    print(f"\nGenerating speech for: '{text}'")
    
    start_time = time.perf_counter()
    wavs, sr = model.generate_voice_clone(
        text=text,
        language="Auto",
        ref_audio=ref_audio_path,
        ref_text=ref_text,
    )
    end_time = time.perf_counter()
    
    sf.write(output_path, wavs[0], sr)
    print(f"[*] Done in {end_time - start_time:.2f}s! Saved to: {output_path}")

def main():
    # Change REFERENCE_AUDIO to your .m4a or .wav file
    REFERENCE_AUDIO = "sample_reference.wav" 
    REFERENCE_TEXT = "이 파일에서 실제로 말하고 있는 문장을 정확하게 여기에 적어주세요."
    
    if not os.path.exists(REFERENCE_AUDIO):
        print(f"[!] Error: Reference audio file '{REFERENCE_AUDIO}' not found.")
        return

    # Auto-convert if it's not a wav file (with caching)
    actual_audio_path = convert_to_wav(REFERENCE_AUDIO)
    
    if not actual_audio_path or not os.path.exists(actual_audio_path):
        print("[!] Failed to prepare reference audio.")
        return

    # Load model only once
    model, device = load_tts_model()
    
    print("\n" + "="*50)
    print(" Interactive Voice Cloning Mode ")
    print(" (Type 'exit', 'quit', or Ctrl+C to stop) ")
    print("="*50)
    
    counter = 1
    while True:
        try:
            target_text = input(f"\n[#{counter}] Enter text to generate: ").strip()
            
            if not target_text:
                continue
            if target_text.lower() in ['exit', 'quit', 'exit()', 'q']:
                print("\nExiting...")
                break
                
            generate_voice(model, target_text, actual_audio_path, REFERENCE_TEXT, counter)
            counter += 1
            
            # Optimization: Explicitly free MPS memory after each generation round
            if device == "mps":
                torch.mps.empty_cache()
                
        except KeyboardInterrupt:
            print("\nExiting...")
            break
        except Exception as e:
            print(f"[!] An error occurred: {e}")

if __name__ == "__main__":
    main()
