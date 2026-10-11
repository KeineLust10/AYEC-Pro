from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "Web_Arayuzu" / "web"


def test_report_templates_have_wider_preview_and_readable_type_scale():
    styles = (WEB / "midnight-reference.css").read_text(encoding="utf-8")

    assert 'body[data-page="report-templates"] .report-template-layout{grid-template-columns:minmax(0,2fr) minmax(390px,1fr)' in styles
    assert 'body[data-page="report-templates"] .report-template-table td{font-size:13px' in styles
    assert 'body[data-page="report-templates"] .report-template-preview-text{font-size:13px' in styles
    assert '@media(max-width:760px){body[data-page="report-templates"] .report-template-layout{grid-template-columns:minmax(0,1fr)}' in styles


def test_report_template_filters_and_tables_fit_phone_widths():
    styles = (WEB / "midnight-reference.css").read_text(encoding="utf-8")

    assert '@media(max-width:480px){body[data-page="report-templates"] .report-template-filters{grid-template-columns:minmax(0,1fr)}' in styles
    assert 'body[data-page="report-templates"] .report-template-table{max-width:calc(100vw - 24px)}' in styles
    assert 'body[data-page="report-templates"] .report-template-table table{min-width:780px}' in styles
