from types import SimpleNamespace

from src.ui.widgets.page_layout_editor import PageLayoutEditorWidget


def _editor(sections):
    sidebar = SimpleNamespace(
        layout_editor_sections=sections,
        _get_allowed_pages=lambda: None,
    )
    main_window = SimpleNamespace(app_sidebar=SimpleNamespace(side_menu=sidebar))
    return SimpleNamespace(
        db=None,
        main_window=main_window,
        _is_page_enabled_by_module=lambda _page_id: True,
    )


def test_interface_editor_uses_the_active_sidebar_items_and_names():
    sections = [
        (
            "SERVIS OPERASYON",
            [
                ("Servis Yönetimi", "wrench", [("Genel Bakış", 40), ("Durum Paneli", 43)]),
                ("Teklif Oluştur", "offer", [("Tüm Teklifler & Geçmiş", 313), ("Teklif Analiz Raporları", 314)], 150),
            ],
        )
    ]

    groups = PageLayoutEditorWidget._visible_groups(_editor(sections))

    assert groups == [(
        "SERVIS OPERASYON",
        [
            (40, "Genel Bakış"),
            (43, "Durum Paneli"),
            (150, "Teklif Oluştur"),
            (313, "Tüm Teklifler & Geçmiş"),
            (314, "Teklif Analiz Raporları"),
        ],
    )]


def test_interface_editor_keeps_the_automotive_sidebar_items():
    sections = [(
        "SERVIS OPERASYON",
        [("Servis Yönetimi", "wrench", [("Araç Bakım Takibi", 210), ("Yedek Parça", 60)])],
    )]

    groups = PageLayoutEditorWidget._visible_groups(_editor(sections))

    assert groups == [("SERVIS OPERASYON", [(210, "Araç Bakım Takibi"), (60, "Yedek Parça")])]
