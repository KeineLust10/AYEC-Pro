from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_public_registration_collects_company_address_and_keeps_errors_inline():
    source = (ROOT / "Web_Arayuzu" / "web" / "app.js").read_text(encoding="utf-8")

    assert 'address.name="company_address"' in source
    assert 'address.required=true' in source
    assert 'sectorSelect.name="sector"' in source
    assert 'apiFetch("/api/auth/register"' in source
    assert 'showRegistrationError(form,error.message)' in source


def test_google_registration_has_a_configured_button_and_disabled_state():
    source = (ROOT / "Web_Arayuzu" / "web" / "google-auth.js").read_text(encoding="utf-8")
    backend = (ROOT / "Web_Arayuzu" / "Main.py").read_text(encoding="utf-8")

    assert 'if(!config.enabled)' in source
    assert 'auth-google-unavailable' in source
    assert 'google.accounts.id.renderButton' in source
    assert 'id_token.verify_oauth2_token(credential, GoogleRequest(), client_id)' in backend
    assert 'apiFetch("/api/auth/google"' in source


def test_ayec_start_does_not_reset_admin_password_and_replaces_its_own_session():
    source = (ROOT / "Web_Arayuzu" / "AYEC_START.ps1").read_text(encoding="utf-8")

    assert "AYEC_ADMIN_RESET_PASSWORD" not in source
    assert "Read-Host \"AYEC Admin password" not in source
    assert "Stop-ScheduledTask -TaskName $taskName" in source
    assert "Stop-OwnedServerListener" in source
    assert "will not terminate an unrelated process" in source
