import argparse
import torch
import soundfile as sf
import os
import time

from engine import get_device, convert_to_wav, load_tts_model


def generate_voice(model, text, ref_audio_path, ref_text, output_path):
    """Generates speech using the already loaded model."""
    print(f"\nGenerating speech for: '{text}'")

    start_time = time.perf_counter()
    with torch.inference_mode():
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
    parser = argparse.ArgumentParser(description="Qwen Voice Studio — Interactive CLI")
    parser.add_argument("--ref-audio", required=True, metavar="PATH",
                        help="Reference audio file (.m4a, .wav, etc.)")
    parser.add_argument("--ref-text", required=True, metavar="TEXT",
                        help="Exact transcript of the reference audio")
    parser.add_argument("--output-dir", default=".", metavar="DIR",
                        help="Directory to save generated files (default: current dir)")
    args = parser.parse_args()

    if not os.path.exists(args.ref_audio):
        print(f"[!] Reference audio not found: '{args.ref_audio}'")
        return

    actual_audio_path = convert_to_wav(args.ref_audio)
    if not actual_audio_path or not os.path.exists(actual_audio_path):
        print("[!] Failed to prepare reference audio.")
        return

    os.makedirs(args.output_dir, exist_ok=True)

    device = get_device()
    print(f"[*] Using device: {device}")
    model = load_tts_model(device)

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

            output_path = os.path.join(args.output_dir, f"output_{counter}.wav")
            generate_voice(model, target_text, actual_audio_path, args.ref_text, output_path)
            counter += 1

            if device == "mps":
                torch.mps.empty_cache()

        except KeyboardInterrupt:
            print("\nExiting...")
            break
        except Exception as e:
            print(f"[!] An error occurred: {e}")


if __name__ == "__main__":
    main()
