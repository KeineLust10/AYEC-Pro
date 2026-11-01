import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_offer_summary_normalizes_turkish_statuses_like_desktop_filters():
    source = (ROOT / "Web_Arayuzu" / "web" / "app.js").read_text(encoding="utf-8")
    normalize = re.search(r"^function normalizeOfferStatus\(value\)\{[^\n]*\}", source, re.MULTILINE)
    summary = re.search(r"^function buildOfferListSummary\(rows\)\{[^\n]*\}", source, re.MULTILINE)
    assert normalize is not None
    assert summary is not None
    script = "\n".join((
        normalize.group(0),
        summary.group(0),
        'const result=buildOfferListSummary([{status:"Onayland\\u0131",total_try:80},{status:"ONAYLANDI",total_try:20},{status:"Reddedildi",total_try:1},{status:"Beklemede",total_try:5}]);',
        'if(result.accepted!==2||result.rejected!==1||result.pending!==1||result.total!==4||result.volume!==106)process.exit(1);',
    ))
    result = subprocess.run(
        ["node", "-e", script],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert result.returncode == 0, result.stderr or result.stdout
