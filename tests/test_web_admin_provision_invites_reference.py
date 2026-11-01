from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP_SOURCE = ROOT / "Web_Arayuzu" / "web" / "app.js"
ROUTE_SMOKE = ROOT / "tools" / "quality" / "web_route_smoke_offscreen.cjs"


def test_provisioning_invite_uses_central_create_and_revoke_endpoints():
    app = APP_SOURCE.read_text(encoding="utf-8")

    assert 'apiFetch("/api/control/provision-invites")' in app
    assert 'apiFetch("/api/control/provision-invite", {method:"POST",body:JSON.stringify(payload)})' in app
    assert 'apiFetch("/api/control/provision-invite/revoke", {method:"POST",body:JSON.stringify({invite_id:Number(button.dataset.provisionInviteRevoke)})})' in app
    assert 'name="expires_in_hours" type="number" min="1" max="720"' in app
    assert 'name="max_uses" type="number" min="1" max="20"' in app


def test_offscreen_route_audit_covers_invite_validation_create_and_revoke():
    route_smoke = ROUTE_SMOKE.read_text(encoding="utf-8")

    assert "controlCenterProvisionInviteWorkflow" in route_smoke
    assert "QA-INVITE-ONCE" in route_smoke
    assert 'if(expiry)expiry.value="24"' in route_smoke
    assert 'if(maxUses)maxUses.value="2"' in route_smoke
    assert 'provision-invite/revoke' in route_smoke


def test_control_center_password_reset_preserves_user_entered_whitespace():
    app = APP_SOURCE.read_text(encoding="utf-8")
    start = app.index("function controlUserPasswordDialog(")
    end = app.index("\nfunction renderVehicleMaintenance()", start)
    flow = app[start:end]

    assert 'String(formData.get("new_password")||"")' in flow
    assert 'String(formData.get("new_password")||"").trim()' not in flow
