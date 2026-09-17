# -*- coding: utf-8 -*-

"""
project_pdf_report.py
Premium, Gorsel Proje Tamamlanma Raporu Olusturucu
"""
from __future__ import annotations
import os
from datetime import datetime
from src.utils.logger import logger


# ──────────────────────────────────────────────────────────────────────────────
# Yardimci: Para bicim
# ──────────────────────────────────────────────────────────────────────────────
def _fmt(val, symbol="₺"):
    try:
        return f"{float(val):,.2f} {symbol}".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return f"0,00 {symbol}"


def _safe(row, key, default="—", idx=None):
    """sqlite3.Row, dict, tuple veya list uzerinden guvenli deger dondurur."""
    # sqlite3.Row — dict-like ama isinstance(dict) False
    if hasattr(row, "keys"):
        try:
            v = row[key]
            return v if v is not None else default
        except (IndexError, KeyError):
            return default
    if isinstance(row, dict):
        v = row.get(key)
        return v if v is not None else default
    if idx is not None and isinstance(row, (tuple, list)) and len(row) > idx:
        v = row[idx]
        return v if v is not None else default
    return default


def _date_display(raw):
    if not raw:
        return "—"
    s = str(raw)[:10]
    try:
        d = datetime.strptime(s, "%Y-%m-%d")
        return d.strftime("%d.%m.%Y")
    except Exception:
        return s or "—"


# ──────────────────────────────────────────────────────────────────────────────
# ANA RAPOR FONKSIYONU
# ──────────────────────────────────────────────────────────────────────────────
def generate_project_report(db, project_id: int, output_path: str) -> tuple[bool, str]:
    try:
        data = _collect_data(db, project_id)
        if output_path.lower().endswith(".html"):
            return _generate_html_report(data, output_path)
        else:
            try:
                return _generate_pdf_reportlab(data, output_path)
            except ImportError:
                logger.warning("ReportLab not found, generating HTML report instead.")
                html_path = output_path.replace(".pdf", ".html")
                ok, msg = _generate_html_report(data, html_path)
                if ok:
                    return True, (
                        f"PDF kutuphanesi bulunamadi. HTML raporu olusturuldu:\n{html_path}\n\n"
                        "Tarayicida acip Ctrl+P ile PDF olarak kaydedebilirsiniz."
                    )
                return ok, msg
    except Exception as e:
        logger.error(f"generate_project_report error: {e}", exc_info=True)
        return False, f"Rapor olusturulamadi: {e}"


# ──────────────────────────────────────────────────────────────────────────────
# VERI TOPLAMA
# ──────────────────────────────────────────────────────────────────────────────
def _collect_data(db, project_id: int) -> dict:
    project = db.get_project_details(project_id)
    financials = db.get_project_financials(project_id)
    install_summary = db.get_project_install_summary(project_id)
    units = list(db.get_project_units(project_id) or [])
    subcontractors = list(db.get_subcontractors(project_id) or [])
    transactions = list(db.get_project_transactions(project_id) or [])

    unit_products = {
        _safe(unit, "id", None, 0): []
        for unit in units
        if _safe(unit, "id", None, 0) is not None
    }
    all_products = list(db.get_project_unit_products(project_id) or [])
    for product in all_products:
        unit_id = _safe(product, "unit_id", None, 1)
        if unit_id is not None:
            unit_products.setdefault(unit_id, []).append(product)

    currency, rate = db.get_project_currency(project_id)
    sym_map = {"TRY": "TL", "USD": "$", "EUR": "EUR", "GBP": "GBP",
               "AED": "AED", "CAD": "CAD", "CHF": "CHF", "JPY": "JPY"}
    symbol = sym_map.get(str(currency).upper(), str(currency))


    # Company branding from Firma Ayarlar\u0131
    try:
        company_name = db.get_setting("company_name", "AYEC Pro") if hasattr(db, "get_setting") else "AYEC Pro"
        logo_path    = db.get_setting("logo_path",    "")         if hasattr(db, "get_setting") else ""
        if not company_name or not company_name.strip():
            company_name = "AYEC Pro"
    except Exception:
        company_name = "AYEC Pro"
        logo_path    = ""

    return {
        "project": project,
        "project_id": project_id,
        "financials": financials,
        "install_summary": install_summary,
        "units": units,
        "subcontractors": subcontractors,
        "transactions": transactions,
        "unit_products": unit_products,
        "currency": currency,
        "rate": rate,
        "symbol": symbol,
        "generated_at": datetime.now().strftime("%d.%m.%Y %H:%M"),
        "company_name": company_name,
        "logo_path":    logo_path,
    }


# ──────────────────────────────────────────────────────────────────────────────
# HTML RAPORU
# ──────────────────────────────────────────────────────────────────────────────

def _logo_html(logo_path):
    """Return an <img> tag with base64-encoded logo, or empty string."""
    if not logo_path or not os.path.exists(logo_path):
        return ""
    try:
        import base64, mimetypes
        mime = mimetypes.guess_type(logo_path)[0] or "image/png"
        with open(logo_path, "rb") as fh:
            b64 = base64.b64encode(fh.read()).decode()
        return f'<img src="data:{mime};base64,{b64}" style="height:55px;margin-bottom:8px;border-radius:6px;object-fit:contain;" alt="logo">'
    except Exception:
        return ""

def _generate_html_report(data: dict, path: str) -> tuple[bool, str]:
    p = data["project"]
    fin = data["financials"]
    ins = data["install_summary"]
    sym = data["symbol"]

    proj_name = _safe(p, "name", "Proje", 1)
    proj_ref = _safe(p, "ref_no", "—", None)
    proj_customer = _safe(p, "customer_name", "—", None)
    proj_status = _safe(p, "status", "—", None)
    proj_start = _date_display(_safe(p, "start_date", "", None))
    proj_end = _date_display(_safe(p, "end_date", "", None))
    proj_budget = float(_safe(p, "budget", 0, None) or 0)
    proj_desc = _safe(p, "description", "", None)

    income = fin.get("income", 0)
    expense = fin.get("expense", 0)
    profit = fin.get("profit", 0)
    income_pending = fin.get("income_pending", 0)
    expense_pending = fin.get("expense_pending", 0)

    total_rooms = ins.get("total", 0)
    completed = ins.get("completed", 0)
    in_progress = ins.get("in_progress", 0)
    total_prods = ins.get("total_products", 0)
    team_count = ins.get("team_count", 0)
    pct = ins.get("pct", 0)

    status_color = {"Tamamlandı": "#22c55e", "Devam Ediyor": "#f59e0b", "İptal": "#ef4444"}.get(proj_status, "#6b7280")
    profit_color = "#22c55e" if profit >= 0 else "#ef4444"

    txn_rows = ""
    for txn in data["transactions"][:60]:
        t_date = _date_display(_safe(txn, "date", ""))
        t_type = _safe(txn, "type", "")
        t_cat = _safe(txn, "category", "")
        t_desc = str(_safe(txn, "description", ""))[:80]
        t_amt = float(_safe(txn, "amount", 0) or 0)
        t_status = _safe(txn, "status", "")
        t_color = "#22c55e" if t_type == "Gelir" else "#ef4444"
        s_color = "#22c55e" if t_status == "Ödendi" else "#f59e0b"
        txn_rows += f"""
        <tr>
          <td>{t_date}</td>
          <td><span class="badge" style="background:{t_color}20;color:{t_color}">{t_type}</span></td>
          <td>{t_cat}</td>
          <td style="max-width:220px;white-space:normal;font-size:11px;color:#6b7280">{t_desc}</td>
          <td style="text-align:right;font-weight:600;color:{t_color}">{_fmt(t_amt, sym)}</td>
          <td><span class="badge" style="background:{s_color}20;color:{s_color};font-size:10px">{t_status}</span></td>
        </tr>"""

    unit_rows = ""
    for unit in data["units"]:
        u_id = _safe(unit, "id", None, 0)
        u_block = _safe(unit, "block_name", "—", 2)
        u_no = _safe(unit, "unit_no", "—", 4)
        u_status = _safe(unit, "status", "Bekliyor", 5)
        prods = data["unit_products"].get(u_id, [])
        u_color = {"Tamamlandı": "#22c55e", "Devam Ediyor": "#f59e0b", "Bekliyor": "#94a3b8"}.get(u_status, "#6b7280")
        u_icon = {"Tamamlandı": "✅", "Devam Ediyor": "🔄", "Bekliyor": "⏳"}.get(u_status, "")
        unit_rows += f"""
        <tr>
          <td><strong>{u_block}</strong></td>
          <td>{u_no}</td>
          <td><span class="badge" style="background:{u_color}20;color:{u_color}">{u_icon} {u_status}</span></td>
          <td style="text-align:center">{len(prods)}</td>
        </tr>"""

    sub_rows = ""
    for sub in data["subcontractors"]:
        s_name = _safe(sub, "name", "—", 1)
        s_job = _safe(sub, "job_type", "—", 2)
        s_amount = float(_safe(sub, "total_contract_amount", 0, 3) or 0)
        s_contact = _safe(sub, "contact_info", "—", 4)
        sub_rows += f"""
        <tr>
          <td><strong>{s_name}</strong></td>
          <td>{s_job}</td>
          <td style="text-align:right">{_fmt(s_amount, sym)}</td>
          <td style="font-size:11px;color:#6b7280">{s_contact}</td>
        </tr>"""
    if not sub_rows:
        sub_rows = '<tr><td colspan="4" style="text-align:center;color:#94a3b8;padding:16px">Ekip üyesi kaydı bulunamadı</td></tr>'

    html = f"""<!DOCTYPE html>
<html lang="tr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Proje Raporu — {proj_name}</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
  *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: 'Inter', sans-serif; background: #f1f5f9; color: #0f172a; font-size: 13px; line-height: 1.6; }}
  .page-wrap {{ max-width: 960px; margin: 0 auto; padding: 32px 24px; }}
  .report-header {{
    background: linear-gradient(135deg, #1e3a5f 0%, #2563eb 100%);
    border-radius: 20px; padding: 36px 40px; color: white; margin-bottom: 28px;
    position: relative; overflow: hidden;
  }}
  .report-header::before {{ content:""; position:absolute; top:-60px; right:-60px; width:220px; height:220px; border-radius:50%; background:rgba(255,255,255,.06); }}
  .header-top {{ display:flex; justify-content:space-between; align-items:flex-start; }}
  .company-badge {{ font-size:11px; font-weight:600; letter-spacing:2px; text-transform:uppercase; opacity:.7; border:1px solid rgba(255,255,255,.3); padding:4px 12px; border-radius:20px; }}
  .proj-title {{ font-size:32px; font-weight:800; margin:16px 0 4px; }}
  .proj-meta {{ display:flex; gap:24px; flex-wrap:wrap; opacity:.85; font-size:12px; margin-top:12px; }}
  .status-pill {{ display:inline-flex; align-items:center; gap:6px; background:rgba(255,255,255,.15); border:1px solid rgba(255,255,255,.3); padding:5px 14px; border-radius:20px; font-size:12px; font-weight:600; margin-top:16px; }}
  .status-dot {{ width:8px; height:8px; border-radius:50%; background:{status_color}; }}
  .stats-grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(140px,1fr)); gap:16px; margin-bottom:28px; }}
  .stat-card {{ background:#fff; border-radius:14px; padding:20px 16px; text-align:center; box-shadow:0 1px 4px rgba(0,0,0,.06); border:1px solid #e2e8f0; }}
  .stat-icon {{ font-size:28px; margin-bottom:8px; }}
  .stat-value {{ font-size:24px; font-weight:800; background:linear-gradient(135deg,#1e3a5f,#2563eb); -webkit-background-clip:text; -webkit-text-fill-color:transparent; margin-bottom:4px; }}
  .stat-label {{ font-size:11px; color:#64748b; font-weight:500; text-transform:uppercase; letter-spacing:.5px; }}
  .finance-grid {{ display:grid; grid-template-columns:repeat(3,1fr); gap:16px; margin-bottom:28px; }}
  .fin-card {{ background:#fff; border-radius:14px; padding:20px; border-left:4px solid; box-shadow:0 1px 4px rgba(0,0,0,.06); }}
  .fin-card-header {{ display:flex; justify-content:space-between; align-items:center; margin-bottom:8px; }}
  .fin-label {{ font-size:11px; font-weight:600; text-transform:uppercase; letter-spacing:.5px; color:#64748b; }}
  .fin-value {{ font-size:20px; font-weight:800; }}
  .fin-pending {{ font-size:11px; color:#f59e0b; margin-top:4px; }}
  .progress-section {{ background:#fff; border-radius:14px; padding:22px 24px; margin-bottom:28px; box-shadow:0 1px 4px rgba(0,0,0,.06); border:1px solid #e2e8f0; }}
  .progress-header {{ display:flex; justify-content:space-between; align-items:center; margin-bottom:14px; }}
  .progress-title {{ font-size:15px; font-weight:700; }}
  .pct-badge {{ font-size:22px; font-weight:800; background:linear-gradient(135deg,#2563eb,#7c3aed); -webkit-background-clip:text; -webkit-text-fill-color:transparent; }}
  .progress-bar-bg {{ background:#e2e8f0; border-radius:999px; height:12px; overflow:hidden; }}
  .progress-bar-fill {{ height:100%; background:linear-gradient(90deg,#2563eb,#7c3aed); border-radius:999px; width:{pct}%; }}
  .section {{ background:#fff; border-radius:16px; margin-bottom:24px; overflow:hidden; box-shadow:0 1px 4px rgba(0,0,0,.06); border:1px solid #e2e8f0; }}
  .section-header {{ display:flex; align-items:center; gap:10px; padding:18px 24px; border-bottom:1px solid #e2e8f0; background:linear-gradient(to right,#f8fafc,#fff); }}
  .section-icon {{ font-size:20px; }}
  .section-title {{ font-size:15px; font-weight:700; }}
  table {{ width:100%; border-collapse:collapse; }}
  th {{ background:#f8fafc; padding:10px 16px; text-align:left; font-size:11px; font-weight:600; text-transform:uppercase; letter-spacing:.5px; color:#64748b; border-bottom:1px solid #e2e8f0; }}
  td {{ padding:11px 16px; border-bottom:1px solid #f1f5f9; vertical-align:middle; }}
  tr:last-child td {{ border-bottom:none; }}
  tr:hover td {{ background:#f8fafc; }}
  .badge {{ display:inline-flex; align-items:center; gap:4px; padding:3px 10px; border-radius:20px; font-size:11px; font-weight:600; }}
  .report-footer {{ margin-top:32px; padding:20px 24px; background:#1e3a5f; border-radius:14px; color:rgba(255,255,255,.7); font-size:11px; display:flex; justify-content:space-between; align-items:center; }}
  .footer-logo {{ font-weight:800; color:white; font-size:14px; }}
  .footer-logo span {{ color:#60a5fa; }}
  .print-btn {{ position:fixed; top:20px; right:20px; background:linear-gradient(135deg,#2563eb,#7c3aed); color:white; border:none; border-radius:10px; padding:12px 20px; font-size:13px; font-weight:700; cursor:pointer; box-shadow:0 4px 12px rgba(37,99,235,.4); z-index:999; font-family:inherit; }}
  @media print {{
    body {{ background:white; }}
    .page-wrap {{ max-width:100%; padding:0; }}
    .report-header {{ margin-bottom:20px; }}
    .no-print {{ display:none!important; }}
    .section {{ break-inside:avoid; }}
    @page {{ margin:15mm; }}
  }}
</style>
</head>
<body>
<button class="print-btn no-print" onclick="window.print()">🖨️ PDF'e Yazdır</button>
<div class="page-wrap">
  <div class="report-header">
    <div class="header-top">
      {_logo_html(data["logo_path"])}
      <span class="company-badge">{data['company_name']} — Proje Raporu</span>
      <div style="font-size:11px;opacity:.6;text-align:right">Rapor: {data["generated_at"]}<br>Ref: {proj_ref}</div>
    </div>
    <div class="proj-title">{proj_name}</div>
    <div class="proj-meta">
      <span>👤 {proj_customer}</span>
      <span>📅 {proj_start} → {proj_end}</span>
      <span>💱 {data["currency"]}</span>
    </div>
    <div><span class="status-pill"><span class="status-dot"></span>{proj_status}</span></div>
  </div>

  <div class="stats-grid">
    <div class="stat-card"><div class="stat-icon">🏠</div><div class="stat-value">{total_rooms}</div><div class="stat-label">Toplam Oda</div></div>
    <div class="stat-card"><div class="stat-icon">✅</div><div class="stat-value" style="background:linear-gradient(135deg,#16a34a,#22c55e);-webkit-background-clip:text;-webkit-text-fill-color:transparent">{completed}</div><div class="stat-label">Tamamlandı</div></div>
    <div class="stat-card"><div class="stat-icon">🔄</div><div class="stat-value" style="background:linear-gradient(135deg,#d97706,#f59e0b);-webkit-background-clip:text;-webkit-text-fill-color:transparent">{in_progress}</div><div class="stat-label">Devam Ediyor</div></div>
    <div class="stat-card"><div class="stat-icon">📦</div><div class="stat-value">{total_prods}</div><div class="stat-label">Kurulu Ürün</div></div>
    <div class="stat-card"><div class="stat-icon">👥</div><div class="stat-value">{team_count}</div><div class="stat-label">Ekip Üyesi</div></div>
    <div class="stat-card"><div class="stat-icon">📊</div><div class="stat-value">{pct}%</div><div class="stat-label">Tamamlanma</div></div>
  </div>

  <div class="progress-section">
    <div class="progress-header"><span class="progress-title">Kurulum İlerleme Durumu</span><span class="pct-badge">{pct}%</span></div>
    <div class="progress-bar-bg"><div class="progress-bar-fill"></div></div>
    <div style="display:flex;justify-content:space-between;margin-top:8px;font-size:11px;color:#94a3b8"><span>0%</span><span>50%</span><span>100%</span></div>
  </div>

  <div class="finance-grid">
    <div class="fin-card" style="border-color:#22c55e">
      <div class="fin-card-header"><span class="fin-label">💰 Gelir (Tahsil)</span></div>
      <div class="fin-value" style="color:#22c55e">{_fmt(income, sym)}</div>
      {'<div class="fin-pending">⏳ Bekleyen: ' + _fmt(income_pending, sym) + '</div>' if income_pending > 0 else ''}
    </div>
    <div class="fin-card" style="border-color:#ef4444">
      <div class="fin-card-header"><span class="fin-label">💸 Gider (Ödenen)</span></div>
      <div class="fin-value" style="color:#ef4444">{_fmt(expense, sym)}</div>
      {'<div class="fin-pending">⏳ Bekleyen: ' + _fmt(expense_pending, sym) + '</div>' if expense_pending > 0 else ''}
    </div>
    <div class="fin-card" style="border-color:{'#22c55e' if profit >= 0 else '#ef4444'}">
      <div class="fin-card-header"><span class="fin-label">📈 Net Kâr</span></div>
      <div class="fin-value" style="color:{profit_color}">{_fmt(profit, sym)}</div>
      <div style="font-size:11px;color:#94a3b8;margin-top:4px">Bütçe: {_fmt(proj_budget, sym)}</div>
    </div>
  </div>

  <div class="section">
    <div class="section-header"><span class="section-icon">📋</span><span class="section-title">Finansal Hareketler</span></div>
    <table>
      <thead><tr><th>Tarih</th><th>Tür</th><th>Kategori</th><th>Açıklama</th><th style="text-align:right">Tutar</th><th>Durum</th></tr></thead>
      <tbody>{txn_rows if txn_rows else '<tr><td colspan="6" style="text-align:center;padding:20px;color:#94a3b8">Hareket kaydı bulunamadı</td></tr>'}</tbody>
    </table>
  </div>

  <div class="section">
    <div class="section-header"><span class="section-icon">🏠</span><span class="section-title">Oda / Daire Kurulum Durumu</span></div>
    <table>
      <thead><tr><th>Blok</th><th>Daire No</th><th>Durum</th><th style="text-align:center">Ürün Sayısı</th></tr></thead>
      <tbody>{unit_rows if unit_rows else '<tr><td colspan="4" style="text-align:center;padding:20px;color:#94a3b8">Kayıt bulunamadı</td></tr>'}</tbody>
    </table>
  </div>

  <div class="section">
    <div class="section-header"><span class="section-icon">👥</span><span class="section-title">Ekip / Alt Yüklenici</span></div>
    <table>
      <thead><tr><th>Ad / Firma</th><th>Uzmanlık</th><th style="text-align:right">Sözleşme Tutarı</th><th>İletişim</th></tr></thead>
      <tbody>{sub_rows}</tbody>
    </table>
  </div>

  {'<div class="section"><div class="section-header"><span class="section-icon">📝</span><span class="section-title">Proje Notları</span></div><div style="padding:20px 24px;color:#475569;line-height:1.8">' + str(proj_desc) + '</div></div>' if proj_desc and proj_desc not in ('—', '') else ''}

  <div class="report-footer">
    <div><div class="footer-logo">{data['company_name']}</div><div style="margin-top:2px">Teknik Servis Yönetim Sistemi</div></div>
    <div style="text-align:right"><div>{data["generated_at"]} tarihinde oluşturulmuştur.</div><div>Proje ID: {data["project_id"]}</div></div>
  </div>
</div>
</body>
</html>"""

    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write(html)
        return True, f"HTML raporu basariyla olusturuldu:\n{path}"
    except Exception as e:
        return False, f"HTML raporu yazilamadi: {e}"


# ──────────────────────────────────────────────────────────────────────────────
# PDF - REPORTLAB (Duzeltilmis: Turkce font + emoji kaldirild)
# ──────────────────────────────────────────────────────────────────────────────
def _get_turkish_fonts():
    """Windows'ta Turkce destekli TTF fontlari bul ve kaydet."""
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    candidates = [
        ("C:/Windows/Fonts/calibri.ttf",  "C:/Windows/Fonts/calibrib.ttf",  "Calibri",  "Calibri-Bold"),
        ("C:/Windows/Fonts/arial.ttf",    "C:/Windows/Fonts/arialbd.ttf",   "Arial",    "Arial-Bold"),
        ("C:/Windows/Fonts/segoeui.ttf",  "C:/Windows/Fonts/segoeuib.ttf",  "Segoe",    "Segoe-Bold"),
        ("C:/Windows/Fonts/tahoma.ttf",   "C:/Windows/Fonts/tahomabd.ttf",  "Tahoma",   "Tahoma-Bold"),
    ]
    for reg_path, bold_path, reg_name, bold_name in candidates:
        if os.path.exists(reg_path):
            try:
                pdfmetrics.registerFont(TTFont(reg_name, reg_path))
                if os.path.exists(bold_path):
                    pdfmetrics.registerFont(TTFont(bold_name, bold_path))
                else:
                    bold_name = reg_name
                logger.info(f"PDF font registered: {reg_name}")
                return reg_name, bold_name
            except Exception as e:
                logger.warning(f"Could not register {reg_name}: {e}")
    # Fallback: built-in Helvetica (partial Turkish support)
    return "Helvetica", "Helvetica-Bold"


def _generate_pdf_reportlab(data: dict, path: str) -> tuple[bool, str]:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.units import mm
    from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table,
                                     TableStyle, HRFlowable)
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

    FONT_REG, FONT_BOLD = _get_turkish_fonts()

    p = data["project"]
    fin = data["financials"]
    ins = data["install_summary"]
    sym = data["symbol"]

    C_PRIMARY = colors.HexColor("#1e3a5f")
    C_ACCENT  = colors.HexColor("#2563eb")
    C_SUCCESS = colors.HexColor("#22c55e")
    C_DANGER  = colors.HexColor("#ef4444")
    C_WARNING = colors.HexColor("#f59e0b")
    C_GRAY    = colors.HexColor("#64748b")
    C_LIGHT   = colors.HexColor("#f8fafc")
    C_BORDER  = colors.HexColor("#e2e8f0")

    proj_name     = str(_safe(p, "name", "Proje", 1))
    proj_customer = str(_safe(p, "customer_name", "—", None))
    proj_status   = str(_safe(p, "status", "—", None))
    proj_start    = _date_display(_safe(p, "start_date", "", None))
    proj_end      = _date_display(_safe(p, "end_date", "", None))
    proj_ref      = str(_safe(p, "ref_no", "—", None))
    proj_budget   = float(_safe(p, "budget", 0, None) or 0)
    proj_desc     = str(_safe(p, "description", "", None) or "")

    pct           = ins.get("pct", 0)
    income        = fin.get("income", 0)
    expense       = fin.get("expense", 0)
    profit        = fin.get("profit", 0)
    inc_p         = fin.get("income_pending", 0)
    exp_p         = fin.get("expense_pending", 0)
    profit_color  = C_SUCCESS if profit >= 0 else C_DANGER

    def S(name, **kw):
        return ParagraphStyle(name, fontName=kw.pop("fontName", FONT_REG), **kw)

    st_hdr_sub = S("HdrSub", fontSize=8,  textColor=colors.HexColor("#94a3b8"), leading=12, alignment=TA_RIGHT)
    st_title   = S("T1",     fontSize=26, textColor=colors.white, fontName=FONT_BOLD, leading=32)
    st_meta    = S("Meta",   fontSize=9,  textColor=colors.HexColor("#cbd5e1"), leading=14)
    st_h2      = S("H2",     fontSize=12, textColor=C_PRIMARY, fontName=FONT_BOLD, leading=16, spaceBefore=4)
    st_body    = S("Body",   fontSize=9,  textColor=colors.HexColor("#374151"), leading=13)
    st_lbl     = S("Lbl",    fontSize=8,  textColor=C_GRAY, fontName=FONT_BOLD, leading=11, alignment=TA_CENTER)
    st_val     = S("Val",    fontSize=18, textColor=C_ACCENT, fontName=FONT_BOLD, leading=22, alignment=TA_CENTER)
    st_th      = S("TH",     fontSize=8,  textColor=colors.white, fontName=FONT_BOLD, leading=11)
    st_thC     = S("THC",    fontSize=8,  textColor=colors.white, fontName=FONT_BOLD, leading=11, alignment=TA_CENTER)
    st_td      = S("TD",     fontSize=8,  textColor=colors.HexColor("#374151"), leading=11)
    st_tdC     = S("TDC",    fontSize=8,  textColor=colors.HexColor("#374151"), leading=11, alignment=TA_CENTER)
    st_tdR     = S("TDR",    fontSize=8,  textColor=colors.HexColor("#374151"), leading=11, alignment=TA_RIGHT)
    st_foot    = S("Foot",   fontSize=7,  textColor=C_GRAY, alignment=TA_CENTER, leading=10)
    st_sm      = S("Sm",     fontSize=7,  textColor=C_GRAY, leading=9)

    doc = SimpleDocTemplate(
        path, pagesize=A4,
        rightMargin=18*mm, leftMargin=18*mm,
        topMargin=18*mm, bottomMargin=18*mm
    )
    story = []

    # ── HEADER BANNER ──────────────────────────────────────────────────────
    hdr_data = [
        [
            Paragraph(f"{data['company_name'].upper()} — PROJE RAPORU", S("CB", fontSize=8, textColor=colors.HexColor("#94a3b8"), fontName=FONT_BOLD, leading=11)),
            Paragraph(f"Ref: {proj_ref}   {data['generated_at']}", st_hdr_sub)
        ],
        [Paragraph(proj_name, st_title), ""],
        [Paragraph(f"Musteri: {proj_customer}   |   {proj_start} — {proj_end}   |   Durum: {proj_status}", st_meta), ""],
    ]
    hdr_tbl = Table(hdr_data, colWidths=["*", 120])
    hdr_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), C_PRIMARY),
        ("SPAN", (0,1), (-1,1)), ("SPAN", (0,2), (-1,2)),
        ("TOPPADDING", (0,0), (-1,-1), 10), ("BOTTOMPADDING", (0,0), (-1,-1), 10),
        ("LEFTPADDING", (0,0), (-1,-1), 18), ("RIGHTPADDING", (0,0), (-1,-1), 18),
        ("ROUNDEDCORNERS", (0,0), (-1,-1), 10),
    ]))
    story.append(hdr_tbl)
    story.append(Spacer(1, 12))

    # ── STAT CARDS ─────────────────────────────────────────────────────────
    stats = [
        ("Toplam Oda",     str(ins.get("total", 0))),
        ("Tamamlandi",     str(ins.get("completed", 0))),
        ("Devam Ediyor",   str(ins.get("in_progress", 0))),
        ("Kurulu Urun",    str(ins.get("total_products", 0))),
        ("Ekip Uyesi",     str(ins.get("team_count", 0))),
        ("Tamamlanma",     f"{pct}%"),
    ]
    stat_cells = [[Paragraph(v, st_val) for _, v in stats],
                  [Paragraph(l, st_lbl) for l, _ in stats]]
    stat_tbl = Table(stat_cells, colWidths=[None]*6)
    stat_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), C_LIGHT),
        ("BOX", (0,0), (-1,-1), 0.5, C_BORDER),
        ("INNERGRID", (0,0), (-1,-1), 0.3, C_BORDER),
        ("TOPPADDING", (0,0), (-1,-1), 10), ("BOTTOMPADDING", (0,0), (-1,-1), 8),
        ("ROUNDEDCORNERS", (0,0), (-1,-1), 8),
    ]))
    story.append(stat_tbl)
    story.append(Spacer(1, 12))

    # ── FINANS OZET ────────────────────────────────────────────────────────
    fin_lbl_style = S("FL", fontSize=8, textColor=colors.white, fontName=FONT_BOLD, alignment=TA_CENTER, leading=11)
    fin_val_g = S("FVG", fontSize=14, textColor=C_SUCCESS, fontName=FONT_BOLD, alignment=TA_CENTER, leading=18)
    fin_val_d = S("FVD", fontSize=14, textColor=C_DANGER,  fontName=FONT_BOLD, alignment=TA_CENTER, leading=18)
    fin_val_p = S("FVP", fontSize=14, textColor=profit_color, fontName=FONT_BOLD, alignment=TA_CENTER, leading=18)
    fin_data = [
        [Paragraph("GELIR", fin_lbl_style), Paragraph("GIDER", fin_lbl_style), Paragraph("NET KAR", fin_lbl_style)],
        [Paragraph(_fmt(income, sym), fin_val_g), Paragraph(_fmt(expense, sym), fin_val_d), Paragraph(_fmt(profit, sym), fin_val_p)],
        [
            Paragraph(f"Bekleyen: {_fmt(inc_p, sym)}" if inc_p > 0 else " ", st_sm),
            Paragraph(f"Bekleyen: {_fmt(exp_p, sym)}" if exp_p > 0 else " ", st_sm),
            Paragraph(f"Butce: {_fmt(proj_budget, sym)}", st_sm),
        ],
    ]
    fin_tbl = Table(fin_data, colWidths=["*","*","*"])
    fin_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), C_PRIMARY),
        ("BACKGROUND", (0,1), (-1,-1), C_LIGHT),
        ("BOX", (0,0), (-1,-1), 0.5, C_BORDER),
        ("INNERGRID", (0,0), (-1,-1), 0.3, C_BORDER),
        ("TOPPADDING", (0,0), (-1,-1), 8), ("BOTTOMPADDING", (0,0), (-1,-1), 8),
        ("ALIGN", (0,0), (-1,-1), "CENTER"),
        ("ROUNDEDCORNERS", (0,0), (-1,-1), 8),
    ]))
    story.append(fin_tbl)
    story.append(Spacer(1, 16))

    # ── FINANSAL HAREKETLER ────────────────────────────────────────────────
    story.append(Paragraph("Finansal Hareketler", st_h2))
    story.append(Spacer(1, 6))
    txn_hdr = [
        Paragraph("Tarih", st_th), Paragraph("Tur", st_th), Paragraph("Kategori", st_th),
        Paragraph("Aciklama", st_th),
        Paragraph("Tutar", S("THR", fontSize=8, textColor=colors.white, fontName=FONT_BOLD, leading=11, alignment=TA_RIGHT)),
        Paragraph("Durum", st_th),
    ]
    txn_rows_pdf = [txn_hdr]
    for txn in data["transactions"][:50]:
        t_date = _date_display(_safe(txn, "date", ""))
        t_type = str(_safe(txn, "type", ""))
        t_cat  = str(_safe(txn, "category", ""))
        t_desc = str(_safe(txn, "description", ""))[:55]
        t_amt  = float(_safe(txn, "amount", 0) or 0)
        t_stat = str(_safe(txn, "status", ""))
        t_clr  = C_SUCCESS if t_type == "Gelir" else C_DANGER
        txn_rows_pdf.append([
            Paragraph(t_date, st_td),
            Paragraph(t_type, S(f"TT{id(txn)}", fontSize=8, textColor=t_clr, fontName=FONT_BOLD, leading=11)),
            Paragraph(t_cat,  st_td),
            Paragraph(t_desc, S("TDS", fontSize=7, textColor=colors.HexColor("#6b7280"), fontName=FONT_REG, leading=9)),
            Paragraph(_fmt(t_amt, sym), S(f"TA{id(txn)}", fontSize=8, textColor=t_clr, fontName=FONT_BOLD, leading=11, alignment=TA_RIGHT)),
            Paragraph(t_stat, S("TS", fontSize=7, textColor=C_SUCCESS if t_stat == "Odendi" else C_WARNING, fontName=FONT_REG, leading=9)),
        ])
    if len(txn_rows_pdf) == 1:
        txn_rows_pdf.append([Paragraph("Hareket kaydi bulunamadi", st_td), "", "", "", "", ""])

    txn_tbl = Table(txn_rows_pdf, colWidths=[58, 42, 78, None, 78, 52])
    txn_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), C_PRIMARY),
        ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, C_LIGHT]),
        ("BOX", (0,0), (-1,-1), 0.5, C_BORDER),
        ("INNERGRID", (0,0), (-1,-1), 0.3, C_BORDER),
        ("TOPPADDING", (0,0), (-1,-1), 5), ("BOTTOMPADDING", (0,0), (-1,-1), 5),
        ("LEFTPADDING", (0,0), (-1,-1), 6), ("RIGHTPADDING", (0,0), (-1,-1), 6),
    ]))
    story.append(txn_tbl)
    story.append(Spacer(1, 16))

    # ── ODA/DAIRE KURULUM ─────────────────────────────────────────────────
    story.append(Paragraph("Oda / Daire Kurulum Durumu", st_h2))
    story.append(Spacer(1, 6))
    unit_rows_pdf = [[Paragraph("Blok", st_th), Paragraph("Daire No", st_th), Paragraph("Durum", st_th), Paragraph("Urun", st_thC)]]
    for unit in data["units"]:
        u_id     = _safe(unit, "id", None, 0)
        u_block  = str(_safe(unit, "block_name", "—", 2))
        u_no     = str(_safe(unit, "unit_no", "—", 4))
        u_status = str(_safe(unit, "status", "Bekliyor", 5))
        prods    = data["unit_products"].get(u_id, [])
        stat_map = {"Tamamlandi": C_SUCCESS, "Devam Ediyor": C_WARNING, "Bekliyor": C_GRAY}
        u_clr    = stat_map.get(u_status, C_GRAY)
        unit_rows_pdf.append([
            Paragraph(u_block, st_td),
            Paragraph(u_no, st_td),
            Paragraph(u_status, S(f"US{id(unit)}", fontSize=8, textColor=u_clr, fontName=FONT_BOLD, leading=11)),
            Paragraph(str(len(prods)), st_tdC),
        ])
    if len(unit_rows_pdf) == 1:
        unit_rows_pdf.append([Paragraph("Kayit bulunamadi", st_td), "", "", ""])

    unit_tbl = Table(unit_rows_pdf, colWidths=[110, 110, 110, 80])
    unit_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), C_ACCENT),
        ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, C_LIGHT]),
        ("BOX", (0,0), (-1,-1), 0.5, C_BORDER),
        ("INNERGRID", (0,0), (-1,-1), 0.3, C_BORDER),
        ("TOPPADDING", (0,0), (-1,-1), 5), ("BOTTOMPADDING", (0,0), (-1,-1), 5),
        ("LEFTPADDING", (0,0), (-1,-1), 8),
    ]))
    story.append(unit_tbl)
    story.append(Spacer(1, 16))

    # ── EKİP / TASERON ────────────────────────────────────────────────────
    if data["subcontractors"]:
        story.append(Paragraph("Ekip / Alt Yuklenici", st_h2))
        story.append(Spacer(1, 6))
        sub_rows_pdf = [[Paragraph("Ad / Firma", st_th), Paragraph("Uzmanlik", st_th), Paragraph("Sozlesme", S("THR2", fontSize=8, textColor=colors.white, fontName=FONT_BOLD, leading=11, alignment=TA_RIGHT)), Paragraph("Iletisim", st_th)]]
        for sub in data["subcontractors"]:
            s_name = str(_safe(sub, "name", "—", 1))
            s_job  = str(_safe(sub, "job_type", "—", 2))
            s_amt  = float(_safe(sub, "total_contract_amount", 0, 3) or 0)
            s_con  = str(_safe(sub, "contact_info", "—", 4))[:40]
            sub_rows_pdf.append([
                Paragraph(s_name, S("SN", fontSize=8, textColor=C_PRIMARY, fontName=FONT_BOLD, leading=11)),
                Paragraph(s_job, st_td),
                Paragraph(_fmt(s_amt, sym), st_tdR),
                Paragraph(s_con, S("SC", fontSize=7, textColor=C_GRAY, fontName=FONT_REG, leading=9)),
            ])
        sub_tbl = Table(sub_rows_pdf, colWidths=[130, 100, 100, 100])
        sub_tbl.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), C_PRIMARY),
            ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, C_LIGHT]),
            ("BOX", (0,0), (-1,-1), 0.5, C_BORDER),
            ("INNERGRID", (0,0), (-1,-1), 0.3, C_BORDER),
            ("TOPPADDING", (0,0), (-1,-1), 5), ("BOTTOMPADDING", (0,0), (-1,-1), 5),
            ("LEFTPADDING", (0,0), (-1,-1), 8),
        ]))
        story.append(sub_tbl)
        story.append(Spacer(1, 16))

    # ── NOTLAR ────────────────────────────────────────────────────────────
    if proj_desc and proj_desc not in ("—", ""):
        story.append(Paragraph("Proje Notlari", st_h2))
        story.append(Spacer(1, 4))
        story.append(Paragraph(proj_desc[:500], st_body))
        story.append(Spacer(1, 12))

    # ── FOOTER ────────────────────────────────────────────────────────────
    story.append(HRFlowable(width="100%", thickness=0.5, color=C_BORDER))
    story.append(Spacer(1, 8))
    story.append(Paragraph(
        f"Bu rapor {data['company_name']} tarafindan "
        f"{data['generated_at']} tarihinde olusturulmustur.  |  Proje ID: {data['project_id']}",
        st_foot
    ))

    doc.build(story)
    return True, f"PDF raporu basariyla olusturuldu:\n{path}"
