# -*- coding: utf-8 -*-

from __future__ import annotations

import ast
import re
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODERN_APP = ROOT / "ModernDesktopApp.py"
SIDE_MENU = ROOT / "src" / "ui" / "widgets" / "side_menu.py"
DIALOGS_DIR = ROOT / "src" / "ui" / "dialogs"
SETTINGS_WIDGETS_DIR = ROOT / "src" / "ui" / "pages" / "settings_widgets"
PAGES_DIR = ROOT / "src" / "ui" / "pages"
OUT_FILE = ROOT / "docs" / "DESKTOP_TECHNICAL_INVENTORY.md"


@dataclass
class PageEntry:
    index: int
    module_path: str
    class_name: str
    attr_name: str


def parse_page_mapping(text: str) -> list[PageEntry]:
    tree = ast.parse(text)
    entries: list[PageEntry] = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        if not node.targets:
            continue
        target = node.targets[0]
        if not isinstance(target, ast.Attribute) or target.attr != "page_mapping":
            continue
        if not isinstance(node.value, ast.Dict):
            continue

        for k_node, v_node in zip(node.value.keys, node.value.values):
            if not isinstance(k_node, ast.Constant) or not isinstance(k_node.value, int):
                continue
            if not isinstance(v_node, ast.Tuple) or len(v_node.elts) < 3:
                continue

            parts = []
            ok = True
            for e in v_node.elts[:3]:
                if isinstance(e, ast.Constant):
                    parts.append(str(e.value))
                else:
                    ok = False
                    break
            if not ok:
                continue

            entries.append(PageEntry(k_node.value, parts[0], parts[1], parts[2]))

    # unique by index (keep first)
    uniq = {}
    for e in sorted(entries, key=lambda x: x.index):
        uniq.setdefault(e.index, e)
    return list(uniq.values())


def parse_side_menu_groups(text: str) -> list[str]:
    lines = []
    keep = False
    for line in text.splitlines():
        if "def populate_menu(self):" in line:
            keep = True
            continue
        if keep and line.startswith("    def "):
            break
        if keep:
            lines.append(line)

    block = "\n".join(lines)
    groups = []
    for m in re.finditer(r'lang\.get\("menu_[^"]+",\s*"([^"]+)"\)\s*,\s*"[^"]+"\s*,\s*\[', block):
        groups.append(m.group(1))
    return groups


def scan_dialogs() -> list[tuple[str, str]]:
    dialogs: list[tuple[str, str]] = []
    for path in sorted(DIALOGS_DIR.glob("*.py")):
        txt = path.read_text(encoding="utf-8", errors="ignore")
        classes = re.findall(r"class\s+(\w+)\(([^)]*)\):", txt)
        if not classes:
            continue
        for cls, base in classes:
            base_l = base.lower()
            if "qdialog" in base_l or "dialog" in cls.lower():
                dialogs.append((path.name, cls))
    return dialogs


def scan_settings_widgets() -> list[str]:
    out = []
    for path in sorted(SETTINGS_WIDGETS_DIR.glob("*.py")):
        if path.name.startswith("__"):
            continue
        out.append(path.stem)
    return out


def scan_page_classes() -> list[tuple[str, str]]:
    pages: list[tuple[str, str]] = []
    for path in sorted(PAGES_DIR.rglob("*.py")):
        if "__pycache__" in str(path):
            continue
        txt = path.read_text(encoding="utf-8", errors="ignore")
        for cls, _base in re.findall(r"class\s+(\w+)\(([^)]*)\):", txt):
            if cls.endswith("Page") or cls.endswith("Widget"):
                pages.append((str(path.relative_to(ROOT)), cls))
    return pages


def scenario_for_page(class_name: str) -> str:
    name = class_name.lower()
    if "dashboard" in name:
        return "KPI ve operasyon özeti görüntüleme"
    if "customer" in name or "partner" in name:
        return "Müşteri/iş ortağı kayıtlarını yönetme"
    if "stock" in name or "brand" in name:
        return "Stok envanteri ve ürün/marka yönetimi"
    if "accounting" in name or "finance" in name or "bank" in name or "check" in name:
        return "Finansal hareketleri takip etme ve mutabakat"
    if "appointment" in name:
        return "Randevu oluşturma ve takvim planlama"
    if "service" in name or "transaction" in name or "device" in name:
        return "Servis iş akışını başlatma ve takip etme"
    if "report" in name or "summary" in name or "audit" in name:
        return "Raporlama, analiz ve izleme"
    if "settings" in name:
        return "Sistem ve kullanıcı ayarlarını yapılandırma"
    return "İlgili modül iş akışını yürütme"


def main() -> int:
    app_text = MODERN_APP.read_text(encoding="utf-8", errors="ignore")
    side_menu_text = SIDE_MENU.read_text(encoding="utf-8", errors="ignore")

    pages = parse_page_mapping(app_text)
    menu_groups = parse_side_menu_groups(side_menu_text)
    dialogs = scan_dialogs()
    settings_widgets = scan_settings_widgets()
    page_classes = scan_page_classes()

    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with OUT_FILE.open("w", encoding="utf-8", newline="\n") as f:
        f.write("# AYEC Pro Masaüstü Teknik Envanteri\n\n")
        f.write("## 1) Sistem Özeti\n")
        f.write("- Uygulama çekirdeği: `ModernDesktopApp.py`\n")
        f.write("- UI ana katmanı: `src/ui`\n")
        f.write("- Veri erişim katmanı: `src/db` + `src/database.py`\n")
        f.write("- Yardımcı servisler: `src/utils`\n")
        f.write("- Toplam sayfa eşlemesi: **{}**\n\n".format(len(pages)))

        f.write("## 2) Ana Menü / Alt Menü Yapısı\n")
        for group in menu_groups:
            f.write(f"- {group}\n")
        f.write("\n")

        f.write("## 3) Sayfa Modül Envanteri\n")
        f.write("| Index | Class | Module | Kullanım Senaryosu | Girdi/Çıktı |\n")
        f.write("|---|---|---|---|---|\n")
        for p in pages:
            f.write(
                f"| {p.index} | `{p.class_name}` | `{p.module_path}` | {scenario_for_page(p.class_name)} | "
                f"Girdi: DB + kullanıcı aksiyonu / Çıktı: UI state + DB güncelleme |\n"
            )
        f.write("\n")

        f.write("## 4) Dialog Pencereleri\n")
        f.write(f"- Toplam tespit edilen dialog sınıfı: **{len(dialogs)}**\n")
        for file_name, cls_name in dialogs:
            f.write(f"- `{file_name}` → `{cls_name}`\n")
        f.write("\n")

        f.write("## 5) Ayarlar Alt Modülleri\n")
        for w in settings_widgets:
            f.write(f"- `{w}`\n")
        f.write("\n")

        f.write("## 6) İş Mantığı Özeti\n")
        f.write("- Sayfalar `page_mapping` üzerinden lazy-load edilir.\n")
        f.write("- Menü tıklaması `on_menu_click(index)` ile yönlenir ve breadcrumb güncellenir.\n")
        f.write("- Temalar `ThemeManager` ile palette + QSS + runtime remap şeklinde uygulanır.\n")
        f.write("- Lisans, hatırlatıcı, asistan ve websocket süreçleri ana pencerede zamanlayıcı/worker tabanlı yürür.\n")
        f.write("- Form süreçlerinde doğrulama + DB commit + toast bildirimi deseni kullanılır.\n\n")

        f.write("## 7) Form/Modal/Report Envanteri\n")
        f.write("### Form odaklı bileşenler\n")
        for p, cls in page_classes:
            cl = cls.lower()
            if "form" in cl or "transaction" in cl or "invoice" in cl or "settings" in cl:
                f.write(f"- `{cls}` (`{p}`): veri girişi/doğrulama/kayıt akışı\n")

        f.write("\n### Raporlama odaklı bileşenler\n")
        for p, cls in page_classes:
            cl = cls.lower()
            if "report" in cl or "summary" in cl or "audit" in cl or "tracking" in cl:
                f.write(f"- `{cls}` (`{p}`): filtreleme, metrik üretimi, export\n")

        f.write("\n### Dialog tabanlı etkileşimler\n")
        for file_name, cls_name in dialogs:
            f.write(
                f"- `{cls_name}` (`src/ui/dialogs/{file_name}`): "
                "Senaryo=Kullanıcı aksiyonu/ onay / detay giriş, "
                "Girdi=parent state + DB, Çıktı=save/cancel sonucu\n"
            )
        f.write("\n")

        f.write("## 8) Web'e Dönüşüm Notları\n")
        f.write("- Her `index` değeri web router path eşlemesine dönüştürülecek.\n")
        f.write("- Dialog sınıfları webde modal drawer/overlay bileşenlerine çevrilecek.\n")
        f.write("- Sayfa bazlı iş mantığı API + frontend state management'e ayrıştırılacak.\n")

    print(f"generated: {OUT_FILE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
