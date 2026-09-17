# -*- coding: utf-8 -*-
from PyQt6.QtWidgets import (
    QWidget, QFrame, QLabel, QPushButton, QVBoxLayout, QHBoxLayout,
    QGraphicsDropShadowEffect, QSizePolicy
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QColor, QPalette

from src.utils.theme_colors import theme_qss, tc
from ._dashboard_utils import (
    is_classic_appearance,
    contrast_on,
    hover_on,
    apply_classic_guard,
    render_svg_icon,
)


_DASHBOARD_ICON_SVGS = {
    "add_device": """<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="4" width="18" height="13" rx="2"/><path d="M8 21h8M12 17v4M12 7v6M9 10h6"/></svg>""",
    "all": """<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/></svg>""",
    "today": """<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="5" width="18" height="16" rx="2"/><path d="M16 3v4M8 3v4M3 10h18"/><path d="M8 14h3v3H8z"/></svg>""",
    "pending_approval": """<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/></svg>""",
    "test": """<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="9"/><path d="m8 12 3 3 5-6"/></svg>""",
    "waiting": """<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 7h6l2 2h10v10H3z"/><path d="M3 7V5h7l2 2"/></svg>""",
    "bekliyor": """<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 7h6l2 2h10v10H3z"/><path d="M3 7V5h7l2 2"/></svg>""",
    "active": """<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="m14.7 6.3 3-3a4 4 0 0 1-5.4 5.4l-7.6 7.6a2.1 2.1 0 0 0 3 3l7.6-7.6a4 4 0 0 1 5.4-5.4l-3 3"/></svg>""",
    "tamirde": """<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="m14.7 6.3 3-3a4 4 0 0 1-5.4 5.4l-7.6 7.6a2.1 2.1 0 0 0 3 3l7.6-7.6a4 4 0 0 1 5.4-5.4l-3 3"/></svg>""",
    "done": """<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 6 9 17l-5-5"/></svg>""",
    "teslim": """<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 6 9 17l-5-5"/></svg>""",
    "part": """<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="9" cy="20" r="1"/><circle cx="19" cy="20" r="1"/><path d="M3 4h2l2.5 11h11l2-7H7"/></svg>""",
    "parca": """<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="9" cy="20" r="1"/><circle cx="19" cy="20" r="1"/><path d="M3 4h2l2.5 11h11l2-7H7"/></svg>""",
    "debt": """<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="5" width="20" height="14" rx="2"/><path d="M2 10h20M6 15h4"/></svg>""",
    "borclu": """<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="5" width="20" height="14" rx="2"/><path d="M2 10h20M6 15h4"/></svg>""",
    "cargo_waiting": """<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 6h11v10H3zM14 9h4l3 3v4h-7z"/><circle cx="7" cy="18" r="2"/><circle cx="18" cy="18" r="2"/></svg>""",
    "kargo": """<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 6h11v10H3zM14 9h4l3 3v4h-7z"/><circle cx="7" cy="18" r="2"/><circle cx="18" cy="18" r="2"/></svg>""",
    "invoiced": """<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M5 3h14v18l-3-2-4 2-4-2-3 2z"/><path d="m8 11 2 2 5-5"/></svg>""",
    "uninvoiced": """<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M5 3h14v18l-3-2-4 2-4-2-3 2z"/><path d="m9 9 6 6m0-6-6 6"/></svg>""",
    "external_out": """<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M5 12h13m-5-5 5 5-5 5"/><path d="M5 5v14"/></svg>""",
    "external_return": """<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M19 12H6m5-5-5 5 5 5"/><path d="M19 5v14"/></svg>""",
    "iptal": """<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="9"/><path d="m9 9 6 6m0-6-6 6"/></svg>""",
}


def dashboard_icon(key, color, size=18):
    svg = _DASHBOARD_ICON_SVGS.get(key) or _DASHBOARD_ICON_SVGS["all"]
    return render_svg_icon(svg, color, size=size)


def make_status_tile(
    parent, key, label, subtitle, icon, bg_color, icon_bg=None, db=None
):
    """Create single status tile widget."""
    classic = is_classic_appearance(db=db)
    tile_bg = "#FFFFFF" if classic else bg_color
    hover_color = "#F7F8FA" if classic else hover_on(bg_color)
    text_color = "#111827" if classic else contrast_on(bg_color)
    muted_color = "#374151" if classic else (
        "rgba(255,255,255,0.72)" if text_color == "#F8FAFC" else "rgba(15,23,42,0.72)"
    )
    divider_color = "#B8C0CC" if classic else (
        "rgba(255,255,255,0.86)" if text_color == "#F8FAFC" else "rgba(15,23,42,0.50)"
    )

    frame = QFrame(parent)
    frame.setObjectName("StatusTile")
    frame.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
    apply_classic_guard(frame, db=db)
    frame.setFixedHeight(62 if classic else 72)
    frame.setCursor(Qt.CursorShape.PointingHandCursor)
    if classic:
        frame.setStyleSheet(f"""
            QFrame#StatusTile {{
                background-color: #FFFFFF;
                border: 1px solid #B8C0CC;
                border-left: 4px solid {bg_color};
                border-radius: 0px;
            }}
            QFrame#StatusTile:hover {{
                background-color: #F7F8FA;
            }}
        """)
    else:
        frame.setStyleSheet(
            theme_qss(f"""
            QFrame#StatusTile {{
                background-color: @surface;
                border: 1px solid @border;
                border-left: 5px solid {bg_color};
                border-radius: 12px;
            }}
            QFrame#StatusTile:hover {{
                background-color: @surface_alt;
                border-color: {bg_color};
            }}
            """)
        )
    frame.setGraphicsEffect(None)

    h = QHBoxLayout(frame)
    h.setContentsMargins(8 if classic else 10, 0 if classic else 6, 8 if classic else 10, 0 if classic else 6)
    h.setSpacing(8)

    icon_lbl = QLabel()
    icon_lbl.setObjectName("StatusTileIcon")
    icon_lbl.setProperty("dashboardIconKey", key)
    apply_classic_guard(icon_lbl, db=db)
    icon_lbl.setFixedSize(28 if classic else 32, 28 if classic else 32)
    icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    if classic:
        icon_lbl.setStyleSheet(
            f"font-size: 13px; font-weight: 900; background-color: #F3F4F6;"
            f"border: 1px solid #B8C0CC; border-radius: 0px; color: {bg_color};"
        )
    else:
        icon_lbl.setStyleSheet(
            theme_qss(f"""
            QLabel#StatusTileIcon {{
                font-size: 14px;
                font-weight: 800;
                background-color: {bg_color}22;
                color: {bg_color};
                border-radius: 16px;
                border: 1px solid {bg_color}44;
            }}
            """)
        )
    icon_size = 16
    icon_lbl.setPixmap(dashboard_icon(key, bg_color, icon_size).pixmap(icon_size, icon_size))
    h.addWidget(icon_lbl)

    txt = QVBoxLayout()
    txt.setSpacing(1)
    txt.setContentsMargins(0, 0, 0, 0)

    lbl_title = QLabel(label)
    lbl_title.setObjectName("StatusTileTitle")
    apply_classic_guard(lbl_title, db=db)
    if classic:
        lbl_title.setStyleSheet(
            f"font-size: 11px; font-weight: 800; color: {text_color};"
            "background: transparent; border: none; letter-spacing: 0px;"
        )
    else:
        lbl_title.setStyleSheet(
            theme_qss("""
            QLabel#StatusTileTitle {
                font-size: 10px;
                font-weight: 800;
                color: @text_muted;
                background: transparent;
                border: none;
            }
            """)
        )
    txt.addWidget(lbl_title)

    lbl_count = QLabel("-")
    lbl_count.setObjectName("StatusTileCount")
    apply_classic_guard(lbl_count, db=db)
    if classic:
        lbl_count.setStyleSheet(
            f"font-size: 14px; font-weight: 900; color: {text_color};"
            f"background: transparent; border: none; border-bottom: 1px solid {divider_color};"
        )
    else:
        lbl_count.setStyleSheet(
            theme_qss("""
            QLabel#StatusTileCount {
                font-size: 16px;
                font-weight: 800;
                color: @text;
                background: transparent;
                border: none;
            }
            """)
        )
    txt.addWidget(lbl_count)

    lbl_sub = QLabel(subtitle)
    lbl_sub.setObjectName("StatusTileSub")
    apply_classic_guard(lbl_sub, db=db)
    if classic:
        lbl_sub.setStyleSheet(
            f"font-size: 10px; font-weight: 700; color: {text_color};"
            "background: transparent; border: none;"
        )
    else:
        lbl_sub.setStyleSheet(
            theme_qss("""
            QLabel#StatusTileSub {
                font-size: 9px;
                font-weight: 500;
                color: @text_muted;
                background: transparent;
                border: none;
            }
            """)
        )
    txt.addWidget(lbl_sub)

    h.addLayout(txt, 1)

    pct_lbl = QLabel("")
    pct_lbl.setObjectName("StatusTilePct")
    apply_classic_guard(pct_lbl, db=db)
    pct_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
    if classic:
        pct_lbl.setStyleSheet(
            f"font-size: 10px; font-weight: 700; color: {muted_color};"
            "background: transparent; border: none;"
        )
    else:
        pct_lbl.setStyleSheet(
            theme_qss(f"""
            QLabel#StatusTilePct {{
                font-size: 10px;
                font-weight: 700;
                color: {bg_color};
                background: transparent;
                border: none;
            }}
            """)
        )
    if classic:
        for label_widget in (icon_lbl, lbl_title, lbl_count, lbl_sub, pct_lbl):
            palette = label_widget.palette()
            palette.setColor(QPalette.ColorRole.WindowText, QColor(text_color))
            palette.setColor(QPalette.ColorRole.Text, QColor(text_color))
            label_widget.setPalette(palette)
    h.addWidget(pct_lbl)

    return {
        "frame": frame,
        "title": lbl_title,
        "count": lbl_count,
        "sub": lbl_sub,
        "pct": pct_lbl,
        "base_sub": subtitle,
        "icon": icon_lbl,
        "accent": bg_color,
        "icon_bg": icon_bg or bg_color,
    }


def create_filter_button(parent, key, text, icon, color, action, db=None):
    classic = is_classic_appearance(db=db)
    btn = QPushButton(text, parent)
    btn.setObjectName("DashboardFilterButton")
    btn.setProperty("accent", color)
    btn.setProperty("filterIcon", icon)
    btn.setProperty("filterText", text)
    btn.setProperty("filterAction", action)
    apply_classic_guard(btn, db=db)
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    button_height = 30 if classic else 44
    btn.setMinimumSize(96, button_height)
    btn.setMaximumHeight(button_height)
    btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
    icon_size = 15 if classic else 18
    btn.setIcon(dashboard_icon(key, color, icon_size))
    btn.setIconSize(QSize(icon_size, icon_size))

    if classic:
        btn.setStyleSheet("""
            QPushButton#DashboardFilterButton {
                background-color: #FFFFFF;
                color: #111827;
                border: 1px solid #AEB4BD;
                border-radius: 0px;
                font-size: 11px;
                font-weight: 700;
                text-align: center;
                padding: 3px 8px;
            }
            QPushButton#DashboardFilterButton:hover {
                background-color: #EAF2FF;
                color: #111827;
                border-color: #8BAFD8;
            }
            QPushButton#DashboardFilterButton:pressed {
                background-color: #DCEBFF;
                color: #111827;
                border-color: #2563EB;
            }
            QPushButton#DashboardFilterButton:checked {
                background-color: #DCEBFF;
                color: #111827;
                border-color: #2563EB;
            }
            QToolTip {
                background-color: #FFFFFF;
                color: #111827;
                border: 1px solid #94A3B8;
                padding: 5px 8px;
            }
        """)
        fg = "#111827"
    else:
        btn.setStyleSheet(theme_qss(f"""
            QPushButton {{
                background-color: @surface;
                color: {color};
                border: 1px solid @border;
                border-radius: 12px;
                font-size: 10px;
                font-weight: 800;
                text-align: center;
            }}
            QPushButton:hover {{
                background-color: @surface_alt;
                border-color: {color};
                padding-bottom: 2px;
            }}
            QPushButton:pressed {{
                padding-top: 2px;
            }}
            QToolTip {{
                background-color: #FFFFFF;
                color: #111827;
                border: 1px solid #94A3B8;
                padding: 5px 8px;
            }}
        """))
        fg = color
    palette = btn.palette()
    for group in (
        QPalette.ColorGroup.Active,
        QPalette.ColorGroup.Inactive,
        QPalette.ColorGroup.Disabled
    ):
        palette.setColor(group, QPalette.ColorRole.ButtonText, QColor(fg))
    btn.setPalette(palette)
    return btn


def create_status_tile_widgets(parent, status_tile_defs, db=None):
    status_tiles = {}
    container = QFrame(parent)
    container.setObjectName("InsightStrip")
    container.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
    apply_classic_guard(container, db=db)
    container.setStyleSheet("background: transparent; border: none;")

    outer = QVBoxLayout(container)
    outer.setContentsMargins(0, 0, 0, 0)
    
    classic = is_classic_appearance(db=db)
    outer.setSpacing(0 if classic else 12)

    for row_keys in [
        ["test", "tamirde", "bekliyor", "iptal"],
        ["kargo", "teslim", "parca", "borclu"],
    ]:
        row_widget = QWidget(parent)
        apply_classic_guard(row_widget, db=db)
        row_widget.setStyleSheet("background: transparent;")
        row_layout = QHBoxLayout(row_widget)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(0 if classic else 12)

        for key in row_keys:
            try:
                def_tuple = next(t for t in status_tile_defs if t[0] == key)
            except StopIteration:
                continue
            tile = make_status_tile(parent, *def_tuple, db=db)
            row_layout.addWidget(tile["frame"], 1)
            status_tiles[key] = tile
        outer.addWidget(row_widget)

    return container, status_tiles


def create_appointment_status_style(btn, status_text, db=None):
    status_text = str(status_text or "Bekliyor").strip()
    status_norm = status_text.lower()
    if status_norm in {"tamamlandı", "tamamlandi"}:
        bg, fg, border = tc("surface_alt"), tc("success"), tc("success")
    elif status_norm in {"iptal"}:
        bg, fg, border = tc("surface_alt"), tc("text_muted"), tc("border")
    elif status_norm in {"gidilmedi", "gelmedi"}:
        bg, fg, border = tc("danger_bg"), tc("danger"), tc("danger")
    elif status_norm in {"gidildi", "geldi"}:
        bg, fg, border = tc("selection_bg"), tc("accent_pressed"), tc("accent")
    elif status_norm in {"işlemde", "islemde"}:
        bg, fg, border = tc("surface_alt"), tc("warning"), tc("warning")
    else:
        bg, fg, border = tc("selection_bg"), tc("accent_pressed"), tc("accent")
    btn.setStyleSheet(theme_qss(
        f"""
        QPushButton {{
            background-color: {bg};
            color: {fg};
            border: 1px solid {border};
            border-radius: 12px;
            padding: 6px 10px;
            font-weight: 800;
            font-size: 11px;
        }}
        QPushButton:hover {{
            border: 1px solid {fg};
        }}
        """
    ))
    return btn


def is_appointment_completed(status):
    st = str(status or "").strip().lower()
    return st == "tamamlandı" or st == "tamamlandi"
