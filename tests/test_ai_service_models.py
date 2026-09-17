from types import SimpleNamespace

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
