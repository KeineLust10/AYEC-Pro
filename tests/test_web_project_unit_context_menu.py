from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_project_unit_context_menu_matches_desktop_status_and_product_actions():
    desktop = (ROOT / "src/ui/pages/project_management/project_detail_components.py").read_text(
        encoding="utf-8"
    )
    web = (ROOT / "Web_Arayuzu/web/app.js").read_text(encoding="utf-8")
    desktop_start = desktop.index("def _show_context_menu(self, pos):")
    desktop_end = desktop.index("# --- UNIT PRODUCTS DIALOG ---", desktop_start)
    desktop_menu = desktop[desktop_start:desktop_end]
    web_start = web.index(
        'document.addEventListener("contextmenu", event => {',
        web.index("const p9ProjectState"),
    )
    web_end = web.index("function p9ProjectTransactionDetailDialog", web_start)
    web_menu = web[web_start:web_end]

    assert "page_id=200" in desktop_menu
    assert 'menu.addAction("\u23f3 Bekliyor")' in desktop_menu
    assert 'menu.addAction("\U0001f504 Devam Ediyor")' in desktop_menu
    assert 'menu.addAction("\u2705 Tamamland\u0131")' in desktop_menu
    assert 'menu.addAction("\U0001f4e6 \u00dcr\u00fcnleri Y\u00f6net")' in desktop_menu
    assert desktop_menu.count("menu.addSeparator()") == 1
    assert 'data-p9-unit-card="${esc(unit.id)}"' in web
    assert 'ayecContextMenuEnabled("project-detail")' in web_menu
    assert 'data-p9-unit-context-status="${esc(status)}"' in web_menu
    assert 'role="menuitemradio"' in web_menu and 'aria-checked=' in web_menu
    assert 'data-p9-unit-context-products=' in web_menu
    assert '"/api/desktop/table/project_units"' in web_menu
    assert 'card.querySelector("[data-p9-unit-products]")?.click()' in web_menu


def test_project_unit_context_menu_matches_desktop_menu_geometry():
    web = (ROOT / "Web_Arayuzu" / "web" / "app.js").read_text(encoding="utf-8")
    css = (ROOT / "Web_Arayuzu" / "web" / "desktop-parity.css").read_text(encoding="utf-8")
    web_start = web.index(
        'document.addEventListener("contextmenu", event => {',
        web.index("const p9ProjectState"),
    )
    web_end = web.index("function p9ProjectTransactionDetailDialog", web_start)
    web_menu = web[web_start:web_end]

    assert 'menu.classList.add("project-unit-context-menu", "open")' in web_menu
    assert 'menuRect = menu.getBoundingClientRect()' in web_menu
    assert 'innerHeight - menuRect.height - 8' in web_menu
    assert 'classList.remove("open", "project-unit-context-menu")' in web_menu
    assert 'border-radius:6px' in css
    assert 'padding:6px 20px' in css
    assert 'grid-template-columns:14px 18px auto' in css
    assert 'var(--surface-2)' in css

