from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "Web_Arayuzu" / "web"


def test_voice_command_prompts_use_application_dialogs():
    source = (WEB / "voice-command-reference.js").read_text(encoding="utf-8")

    assert "prompt(" not in source
    assert 'data-voice-add="command"' in source
    assert 'data-voice-add="scenario"' in source
    assert 'openDialog(title,"SES KOMUTLARI",body,form=>' in source
    assert 'name="name" required' in source
    assert 'name="phrase" required' in source
    assert 'if(scenario)state.active=name' in source
    assert 'name="active" list="voiceScenarioOptions" required' in source
    assert 'voiceCommandSaveState(state);render();return true' in source
