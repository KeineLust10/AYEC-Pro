import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace

from src.utils import offline_turkish_asr


MODEL_FILES = ("model.bin", "config.json", "tokenizer.json", "vocabulary.txt")


def _make_model(directory):
    directory.mkdir(parents=True, exist_ok=True)
    for name in MODEL_FILES:
        (directory / name).write_bytes(b"model-test")
    return directory


def test_offline_asr_loads_bundled_model_when_user_data_has_no_model(
    tmp_path, monkeypatch
):
    app_data = tmp_path / "app-data"
    bundled = _make_model(tmp_path / "bundle" / "Speech" / "whisper-small")
    loaded = []

    class _WhisperModel:
        def __init__(self, path, **_options):
            loaded.append(Path(path))

    monkeypatch.setitem(
        sys.modules, "faster_whisper", SimpleNamespace(WhisperModel=_WhisperModel)
    )
    monkeypatch.setattr(
        offline_turkish_asr.PathHelper, "get_app_data_dir", lambda: str(app_data)
    )
    monkeypatch.setattr(
        offline_turkish_asr.PathHelper,
        "get_resource_path",
        lambda *parts: str(tmp_path / "bundle" / Path(*parts)),
    )

    asr = offline_turkish_asr.OfflineTurkishASR()

    assert asr.model_path == bundled
    assert loaded == [bundled]


def test_nuitka_runtime_copies_offline_asr_model_without_building(tmp_path):
    script_path = Path("tools/setup/build_nuitka.py")
    spec = importlib.util.spec_from_file_location("ayec_nuitka_build", script_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    source = _make_model(tmp_path / "source-model")
    target_root = tmp_path / "runtime"
    module.copy_offline_asr_model(target_root, source_dir=source)

    copied = target_root / "Speech" / "whisper-small"
    assert all((copied / name).is_file() for name in MODEL_FILES)
    assert "comtypes" in module.RUNTIME_PACKAGE_ROOTS
    build_source = script_path.read_text(encoding="utf-8")
    assert '"--include-package=pyaudio"' in build_source
    assert '"--include-package=speech_recognition"' in build_source
    assert '"--nofollow-import-to=pyaudio"' not in build_source


def test_customer_installer_prepares_ollama_model_before_launch():
    setup_source = Path("AYECPro_Modern_Setup.iss").read_text(encoding="utf-8")
    installer_source = Path("tools/setup/prepare_ollama_model.ps1").read_text(
        encoding="utf-8"
    )
    workspace_setup = Path("tools/setup/prepare_offline_assistant.ps1").read_text(
        encoding="utf-8"
    )

    assert 'Source: "tools\\setup\\prepare_ollama_model.ps1"' in setup_source
    assert setup_source.index("prepare_ollama_model.ps1") < setup_source.index(
        'Filename: "{app}\\{#MyAppExeName}"'
    )
    assert '"qwen3:4b"' in installer_source
    assert 'Start-Process -FilePath $ollamaPath -ArgumentList "serve" -WindowStyle Hidden' in installer_source
    assert '& $ollamaPath pull $model *> $null' in installer_source
    assert "prepare_ollama_model.ps1" in workspace_setup


def test_offline_assistant_setup_preloads_local_turkish_tts_model():
    workspace_setup = Path("tools/setup/prepare_offline_assistant.ps1").read_text(
        encoding="utf-8"
    )
    tts_setup = Path("tools/setup/install_local_tts_runtime.ps1").read_text(
        encoding="utf-8"
    )

    assert 'Join-Path $PSScriptRoot "install_local_tts_runtime.ps1"' in workspace_setup
    assert "& $ttsSetupScript" in workspace_setup
    assert 'from ema_lightning import EMA; EMA(device=\'cpu\')' in tts_setup
    assert "ready for offline use" in tts_setup
    assert "download on first speech" not in tts_setup
