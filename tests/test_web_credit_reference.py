from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "Web_Arayuzu" / "web"


def test_credit_workspace_uses_compact_metrics_and_mobile_controls():
    page = (WEB / "loans.js").read_text(encoding="utf-8")
    styles = (WEB / "midnight-reference.css").read_text(encoding="utf-8")

    assert 'class="loan-metrics"' in page
    assert 'id="loanContract"' in page
    assert 'id="loanTableBody"' in page
    assert 'id="loanCreate"' in page
    assert 'body[data-page="loans"] .loan-metrics article{gap:5px;min-height:84px;padding:11px 14px' in styles
    assert '@media(max-width:760px){body[data-page="loans"] .loan-metrics{grid-template-columns:repeat(2,minmax(0,1fr))}' in styles
    assert '@media(max-width:420px){body[data-page="loans"] .loan-metrics{grid-template-columns:minmax(0,1fr)}' in styles
