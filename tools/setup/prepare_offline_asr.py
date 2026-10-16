"""Download the Turkish-capable ASR model before running the app offline."""

import sys
from pathlib import Path

from huggingface_hub import snapshot_download

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from src.utils.path_helper import PathHelper


def main():
    model_dir = Path(PathHelper.get_app_data_dir()) / "Speech" / "whisper-small"
    required_files = ("model.bin", "config.json", "tokenizer.json", "vocabulary.txt")
    if model_dir.is_dir() and all((model_dir / name).is_file() for name in required_files):
        print("Offline Turkish speech model is ready.")
        return
    model_dir.mkdir(parents=True, exist_ok=True)
    snapshot_download(
        repo_id="Systran/faster-whisper-small",
        local_dir=str(model_dir),
        allow_patterns=[
            "config.json",
            "preprocessor_config.json",
            "model.bin",
            "tokenizer.json",
            "vocabulary.*",
        ],
    )
    missing_files = [name for name in required_files if not (model_dir / name).is_file()]
    if missing_files:
        raise RuntimeError("Offline ASR model is incomplete: " + ", ".join(missing_files))
    print("Offline Turkish speech model is ready.")


if __name__ == "__main__":
    main()
