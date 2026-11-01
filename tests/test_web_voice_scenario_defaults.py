from __future__ import annotations

import ast
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DESKTOP_SOURCE = ROOT / "src" / "ui" / "pages" / "settings_widgets" / "voice_training_base.py"
WEB_SOURCE = ROOT / "Web_Arayuzu" / "web" / "voice-command-reference.js"


def test_web_scenario_defaults_match_desktop_definitions():
    desktop_tree = ast.parse(DESKTOP_SOURCE.read_text(encoding="utf-8"))
    widget = next(
        node
        for node in desktop_tree.body
        if isinstance(node, ast.ClassDef) and node.name == "VoiceTrainingWidget"
    )
    method = next(
        node
        for node in widget.body
        if isinstance(node, ast.FunctionDef) and node.name == "_default_scenarios"
    )
    assignment = next(
        node
        for node in method.body
        if isinstance(node, ast.Assign)
        and any(isinstance(target, ast.Name) and target.id == "scenarios" for target in node.targets)
    )
    desktop_defaults = ast.literal_eval(assignment.value)

    web_source = WEB_SOURCE.read_text(encoding="utf-8")
    declaration = "const voiceScenarioDefaults = "
    start = web_source.index(declaration) + len(declaration)
    end = web_source.index(";\nfunction voiceRepairScenarios", start)
    web_defaults = json.loads(web_source[start:end])

    assert len(desktop_defaults) == 27
    assert web_defaults == desktop_defaults
    assert 'const added=Object.keys(voiceScenarioDefaults).filter(name=>!state.scenarios[name])' in web_source
    assert 'state.scenarios=voiceRepairScenarios(state.scenarios)' in web_source
    assert 'scenario_defaults_initialized:saved.scenario_defaults_initialized===true' in web_source
    assert 'scenario_defaults_initialized:false' in web_source
    assert 'state.scenario_defaults_initialized&&!Object.keys(state.scenarios).length' in web_source
    assert 'if(!Object.keys(scenarios).length){for(const item of state.commands||[])' not in web_source
    assert "async function runVoiceScenarioHealthcheck(state)" in web_source
    assert 'fetch("/api/desktop/health"' in web_source
    assert 'health?.schema_ready===true' in web_source
    assert 'voiceScenarioMatch({scenarios},item.trigger)?.name===item.name' in web_source
    assert 'desktopSettings?.voice_command_settings' in web_source
    assert 'desktopSettings.voice_command_settings=value' in web_source


def test_voice_customer_360_offscreen_audit_checks_match_and_fallback():
    route_smoke = (ROOT / "tools" / "quality" / "web_route_smoke_offscreen.cjs").read_text(encoding="utf-8")
    assert "voiceCustomer360Matched?.id !== 9902" in route_smoke
    assert 'voiceCustomer360FallbackPage !== "customers"' in route_smoke
    assert "voiceCustomer360FallbackToast.includes" in route_smoke
    assert "voiceCustomer360PrefixOpenedCount !== 0" in route_smoke
    assert 'voiceCustomer360PrefixFallbackPage !== "customers"' in route_smoke
    assert "voiceCustomer360PrefixFallbackToast.includes" in route_smoke


def test_voice_new_service_action_opens_form_without_writing():
    route_smoke = (ROOT / "tools" / "quality" / "web_route_smoke_offscreen.cjs").read_text(encoding="utf-8")
    assert 'voiceScenarioWorkflow.voiceServicePage !== "services"' in route_smoke
    assert "!voiceScenarioWorkflow.voiceServiceDialogOpen" in route_smoke
    assert "voiceServiceWritesAfter !== voiceScenarioWorkflow.voiceServiceWritesBefore" in route_smoke


def test_voice_sync_action_offscreen_audit_checks_rejection_recovery():
    route_smoke = (ROOT / "tools" / "quality" / "web_route_smoke_offscreen.cjs").read_text(encoding="utf-8")
    assert 'new Error("QA sync rejected")' in route_smoke
    assert 'failureHydrateCalls !== 1' in route_smoke
    assert 'failureToast.includes("Senkronizasyon tamamlanamad\\u0131: QA sync rejected")' in route_smoke


def test_voice_financial_summary_audit_checks_success_and_failure():
    route_smoke = (ROOT / "tools" / "quality" / "web_route_smoke_offscreen.cjs").read_text(encoding="utf-8")
    assert "financialSummaryCalls.length !== 1" in route_smoke
    assert 'financialSummaryToast.includes("Net durumunuz")' in route_smoke
    assert 'financialSummaryFailureCalls !== 1' in route_smoke
    assert 'financialSummaryFailureToast.includes("Finansal ozet hazirlanamadi: QA finance unavailable")' in route_smoke
