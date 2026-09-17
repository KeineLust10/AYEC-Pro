from src.services.assistant_manager import AssistantManager


class _GreetingHarness:
    def __init__(self, voice_enabled=True):
        self.voice_enabled = voice_enabled
        self.calls = 0
        self.failures = []

    def _assistant_voice_enabled(self):
        return self.voice_enabled

    def arz_et_gunluk_plan(self):
        self.calls += 1

    def _log_soft_failure(self, context, exc):
        self.failures.append((context, exc))


def test_startup_greeting_runs_once_per_application_instance():
    harness = _GreetingHarness()

    AssistantManager.startup_greeting(harness)
    AssistantManager.startup_greeting(harness)

    assert harness.calls == 1
    assert harness.failures == []


def test_startup_greeting_respects_voice_setting():
    harness = _GreetingHarness(voice_enabled=False)

    AssistantManager.startup_greeting(harness)

    assert harness.calls == 0
    assert not hasattr(harness, "_startup_greeting_done")
