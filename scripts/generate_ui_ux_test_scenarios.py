# -*- coding: utf-8 -*-
"""Regenerate tests/ui_ux_test_scenarios.md from src/ui static analysis."""
from __future__ import annotations

import ast
import re
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UI_ROOT = ROOT / "src" / "ui"
OUT = ROOT / "tests" / "ui_ux_test_scenarios.md"

WIDGET_TYPES = {
    "QPushButton",
    "QCheckBox",
    "QRadioButton",
    "QComboBox",
    "QAction",
    "AnimatedToggle",
    "ModernComboBox",
}

SIGNALS = {
    "QPushButton": "clicked",
    "QCheckBox": "stateChanged",
    "QRadioButton": "toggled",
    "QComboBox": "currentIndexChanged",
    "QAction": "triggered",
    "AnimatedToggle": "toggled",
    "ModernComboBox": "currentIndexChanged",
}


@dataclass
class UIElement:
    file: Path
    line: int
    name: str
    widget_type: str
    signal: str
    handler: str
    connected: bool


def rel_path(path: Path) -> str:
    return str(path.relative_to(ROOT)).replace("/", "\\")


def find_connects(source: str) -> set[tuple[str, str]]:
    found: set[tuple[str, str]] = set()
    for m in re.finditer(
        r"self\.(\w+)\.(\w+)\.connect\s*\(\s*([^)\n]+)",
        source,
    ):
        found.add((m.group(1), m.group(2)))
    return found


def analyze_file(path: Path) -> list[UIElement]:
    source = path.read_text(encoding="utf-8", errors="replace")
    connects = find_connects(source)
    elements: list[UIElement] = []
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return elements

    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        if len(node.targets) != 1:
            continue
        target = node.targets[0]
        if not isinstance(target, ast.Attribute):
            continue
        if not isinstance(target.value, ast.Name) or target.value.id != "self":
            continue
        name = target.attr
        call = node.value
        widget_type = None
        if isinstance(call, ast.Call):
            func = call.func
            if isinstance(func, ast.Name):
                widget_type = func.id
            elif isinstance(func, ast.Attribute):
                widget_type = func.attr
        if widget_type not in WIDGET_TYPES:
            continue
        signal = SIGNALS.get(widget_type, "clicked")
        connected = (name, signal) in connects or (name, "clicked") in connects
        if widget_type == "QPushButton":
            connected = connected or (name, "toggled") in connects
        if widget_type in ("QCheckBox", "AnimatedToggle"):
            connected = connected or (name, "stateChanged") in connects or (name, "toggled") in connects
        if widget_type == "QComboBox":
            connected = connected or (name, "currentTextChanged") in connects or (name, "activated") in connects
        handler = "Tespit edilmedi"
        if connected:
            for w, sig in connects:
                if w == name:
                    handler = f"self.{sig} handler"
                    break
            else:
                handler = "Bağlı"
        line = node.lineno
        elements.append(
            UIElement(
                file=path,
                line=line,
                name=name,
                widget_type=widget_type,
                signal=signal,
                handler=handler,
                connected=connected,
            )
        )
    return elements


def render(elements: list[UIElement]) -> str:
    by_file: dict[Path, list[UIElement]] = {}
    for el in elements:
        by_file.setdefault(el.file, []).append(el)

    lines = [
        "# UI/UX Test Senaryoları - AYEC Pro",
        "",
        "## Kapsam",
        "- src/ui altındaki sayfalar, diyaloglar ve widget'lar",
        "- Ana menü, alt menüler, butonlar, mouse olayları, toggle anahtarları, işlevsel butonlar (PDF/Excel dışa aktarma, fiş/yazdırma)",
        "- Sinyal-slot bağları, olay işleyici tetiklemeleri, servis çağrıları ve UI tepkileri",
        "",
        "## Yürütme Notları",
        "- Gerçek Sonuç varsayılanı 'Çalıştırılmadı' olup manuel çalıştırmada doldurulmalıdır",
        "- Bağlantı Durumu, sinyal bağlantıları ve olay override'larının statik taramasından türetilir",
        "- Son güncelleme: otomatik üretici (`scripts/generate_ui_ux_test_scenarios.py`)",
        "",
        "## Test Vakaları",
    ]
    tc = 1
    unconnected: list[UIElement] = []
    for path in sorted(by_file.keys()):
        lines.append(f"### {rel_path(path)}")
        for el in sorted(by_file[path], key=lambda x: x.line):
            status = "Bağlı" if el.connected else "Bağlı Değil"
            if not el.connected:
                unconnected.append(el)
            ui_label = el.name
            if not el.connected:
                ui_label = f"{el.name} (bağlı değil {el.widget_type})"
            lines.extend(
                [
                    f"- ID: TC-{tc:05d}",
                    f"  - UI Öğesi: {ui_label} ({el.signal})",
                    f"  - Konum: {rel_path(el.file)}:{el.line}",
                    f"  - Bağlantı: {el.handler}",
                    f"  - Etkileşim: Sinyali tetikleyin ve handler çalışmasını gözlemleyin",
                    f"  - Beklenen Davranış: Handler hatasız çalışır, UI güncellenir ve/veya servis çağrısı tamamlanır",
                    f"  - Gerçek Sonuç: Çalıştırılmadı",
                    f"  - Hata Senaryoları: Yanıt yok, istisna, yanlış sayfa/işlem, eksik veri doğrulaması",
                    f"  - Bağlantı Durumu: {status}",
                ]
            )
            tc += 1
        lines.append("")

    lines.extend(["## Bağlı Olmayan Öğeler Özeti"])
    for el in unconnected:
        lines.append(f"- {rel_path(el.file)}:{el.line} - {el.name} ({el.widget_type})")
    lines.append("")
    lines.append(f"**Toplam test:** {tc - 1} | **Bağlı olmayan:** {len(unconnected)}")
    return "\n".join(lines)


def main():
    all_elements: list[UIElement] = []
    for path in sorted(UI_ROOT.rglob("*.py")):
        if path.name.startswith("_"):
            continue
        all_elements.extend(analyze_file(path))
    OUT.write_text(render(all_elements), encoding="utf-8")
    unconnected = [e for e in all_elements if not e.connected]
    print(f"Wrote {OUT}")
    print(f"Total: {len(all_elements)}, unconnected: {len(unconnected)}")


if __name__ == "__main__":
    main()
