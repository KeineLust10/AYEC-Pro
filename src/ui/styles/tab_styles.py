# -*- coding: utf-8 -*-

"""
Premium Tab Widget Styling
Tüm sayfalarda tutarlı sekme görünümü için ortak stil tanımları
"""

def get_tab_style():
    """
    Returns the centralized stylesheet for QTabWidget.
    Features:
    - Wider tabs (Expanded look)
    - Center aligned text
    - Premium color palette (Orange highlight)
    - Smooth hover effects
    """
    return """
        QTabWidget::pane {
            border: 1px solid lightgray;
            background: white;
            border-radius: 8px;
            margin-top: -1px;
            /* Hafif gölge efekti */
        }
        
        QTabBar::tab {
            background: whitesmoke;
            color: dimgray;
            padding: 12px 30px;  /* Daha geniş dolgu */
            border: 1px solid silver;
            border-bottom: none;
            border-top-left-radius: 8px;
            border-top-right-radius: 8px;
            margin-right: 4px;   /* Sekmeler arası boşluk */
            font-weight: 600;
            font-family: "Segoe UI", sans-serif;
            font-size: 14px;
            min-width: 160px;    /* Minimum genişlik artırıldı (sağa yayılma için) */
            margin-top: 2px;     /* Seçili olmayanlar hafif aşağıda */
        }

        QTabBar::tab:hover {
            background: gainsboro;
            color: black;
        }

        QTabBar::tab:selected {
            background: orange; /* Premium Turuncu */
            color: white;
            border-color: darkorange;
            border-bottom-color: orange; /* Panelle bütünleşmesi için */
            margin-top: 0px;
        }
    """

# Backward compatibility (Eski kullanimlar icin)
TAB_STYLE = get_tab_style()

