"""Explicit one-time download of public multilingual speech weights to F: workspace."""
from pathlib import Path
from faster_whisper.utils import download_model

target = Path(__file__).resolve().parents[1] / "data" / "speech" / "faster-whisper-tiny"
if __name__ == "__main__":
    installed = download_model("tiny", output_dir=str(target))
    print("Local speech model installed:", installed)
