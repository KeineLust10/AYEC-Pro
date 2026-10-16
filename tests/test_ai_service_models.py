from types import SimpleNamespace

from src.utils import ai_service as ai_service_module
from src.utils.ai_service import (
    AIService,
    DEFAULT_GEMINI_MODEL,
    RECOMMENDED_GEMINI_MODELS,
    normalize_gemini_model,
)


def test_retired_model_names_are_migrated():
    assert normalize_gemini_model("gemini-2.0-flash") == DEFAULT_GEMINI_MODEL
    assert normalize_gemini_model("models/gemini-1.5-pro") == "gemini-3.5-flash"
    assert normalize_gemini_model("") == DEFAULT_GEMINI_MODEL


def test_model_list_fallback_contains_current_recommendations():
    service = AIService()
    service.client = SimpleNamespace()

    assert service.get_available_models() == list(RECOMMENDED_GEMINI_MODELS)


def test_generation_uses_saved_limits_rotation_settings_and_masks_sensitive_values(monkeypatch):
    values = {
        "gemini_max_output_tokens": "4096",
        "gemini_temperature": "0.7",
        "gemini_smart_token_compression": "1",
        "gemini_sensitive_data_masking": "1",
        "gemini_zero_downtime_rotation": "0",
        "gemini_auto_load_shedding": "1",
    }
    class CountingGate:
        def __init__(self):
            self.entries = 0

        def __enter__(self):
            self.entries += 1
            return self

        def __exit__(self, *_args):
            return False

    gate = CountingGate()
    monkeypatch.setattr(ai_service_module, "GEMINI_REQUEST_GATE", gate)
    service = AIService()
    service.db = SimpleNamespace(get_setting=lambda key, default="": values.get(key, default))
    captured = {}
    service.client = SimpleNamespace(
        models=SimpleNamespace(
            generate_content=lambda **kwargs: (
                captured.update(kwargs) or SimpleNamespace(text="ok")
            )
        )
    )

    assert service.generate_response(
        "Call +90 532 555 12 34 or ops@example.com, IBAN TR330006100519786457841326\n\n\nFollow up"
    ) == "ok"
    assert captured["config"] == {"max_output_tokens": 4096, "temperature": 0.7}
    assert captured["contents"].count("[MASKED]") == 3
    assert "+90 532 555 12 34" not in captured["contents"]
    assert "ops@example.com" not in captured["contents"]
    assert "\n\n\n" not in captured["contents"]
    assert gate.entries == 1
