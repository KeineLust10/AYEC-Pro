from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "Web_Arayuzu" / "web"


def test_midnight_global_search_offers_accessible_turkish_voice_input():
    html = (WEB / "index.html").read_text(encoding="utf-8")
    app = (WEB / "app.js").read_text(encoding="utf-8")
    styles = (WEB / "midnight-reference.css").read_text(encoding="utf-8")

    assert 'id="globalSearchVoice"' in html
    assert "window.SpeechRecognition||window.webkitSpeechRecognition" in app
    assert 'recognition.lang="tr-TR"' in app
    assert 'classList.add("listening")' in app
    assert ".global-search-voice.listening" in styles


def test_voice_shortcuts_are_configurable_persistent_and_responsive():
    app = (WEB / "app.js").read_text(encoding="utf-8")
    styles = (WEB / "midnight-reference.css").read_text(encoding="utf-8")

    assert '"voice-shortcuts"' in app
    assert 'settingsSection==="voice-shortcuts"?renderVoiceShortcuts()' in app
    assert 'localStorage.setItem("ayec.web.voice-shortcuts"' in app
    assert 'data-voice-edit' in app
    assert 'data-voice-delete' in app
    assert 'function ayecRunVoiceShortcut' in app
    assert 'function ayecNormalizeVoicePhrase' in app
    assert 'shortcut?(matches(shortcut)?shortcut:null)' in app
    assert "@media(max-width:600px){.voice-shortcuts-page" in styles
