from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "Web_Arayuzu" / "web"
APP = (WEB / "app.js").read_text(encoding="utf-8")


def test_voice_command_prompts_use_application_dialogs():
    source = (WEB / "voice-command-reference.js").read_text(encoding="utf-8")

    assert "prompt(" not in source
    assert 'data-voice-add="command"' in source
    assert 'data-voice-add="scenario"' in source
    assert 'openDialog(title,"SES KOMUTLARI",body,form=>' in source
    assert 'name="name" required' in source
    assert 'name="phrase" required' in source
    assert 'if(scenario){state.active=name;state.scenarios[name]={triggers:[`"${phrase}"`],action:null};}' in source
    assert 'function openVoiceScenarioEditor(state)' in source
    assert 'name="triggers"' in source
    assert 'name="action"' in source
    assert 'name="auto_search"' in source
    assert 'type:"builtin"' in source
    assert 'type:"page"' in source
    assert 'delete scenarios[name]' in source
    assert 'scenarios:saved.scenarios&&typeof saved.scenarios==="object"' in source
    assert 'id="voiceScenarioName" name="scenario"' in source
    assert 'voiceCommandSaveState(state);render();return true' in source
    assert 'ayecExecuteVoiceAction({type:"Aksiyon",action:match.action.name,voice_trigger:match.phrase},transcript)' in source
    assert "function ayecExecuteVoiceAction(item,transcript=\"\")" in APP
    assert "ayecExecuteVoiceAction(candidate,transcript)" in APP
    assert 'if(action==="apply_zam"){return ayecOpenVoiceStockPriceDialog(transcript)}' in APP
    assert 'JSON.stringify(state.scenarios,null,2)' in source
    assert "function voiceScenarioMatch(state,transcript)" in source
    assert 'voiceScenarioMatch({scenarios:{[state.active]:scenario}},sample)' in source
    assert 'openDialog("Aktif Senaryoyu Test Et"' in source
    assert 'function ayecResolveVoiceConfirmation(accepted)' in APP
    assert 'action==="confirm_yes"||action==="confirm_no"' in APP
    assert 'const action=accepted?pending.confirm:pending.cancel' in APP
    assert 'window.ayecPendingVoiceConfirmation=null;' in APP
