# -*- coding: utf-8 -*-
"""
DashboardActionsMixin - Mod\u00fcler Dashboard Orkestrat\u00f6r\u00fc
------------------------------------------------------------
Bu s\u0131n\u0131f, a\u015fa\u011f\u0131daki uzmanla\u015fm\u0131\u015f mixin'lerden i\u015flevselli\u011fi devral\u0131r:

- DashboardBaseMixin    \u2192 Temel yard\u0131mc\u0131 metotlar ve refresh_data
- DashboardDataMixin    \u2192 Tablo doldurma, status tiles, h\u00fccre yard\u0131mc\u0131lar\u0131
- DashboardDialogMixin  \u2192 Dialog y\u00f6netimi (Servis, M\u00fc\u015fteri, Teknisyen Paneli)
- DashboardFuncMixin    \u2192 Fonksiyonel i\u015flemler (durum, silme, \u00f6deme, SMS)
- DashboardUIMixin      \u2192 UI bile\u015fenleri (sa\u011f t\u0131k men\u00fcs\u00fc, filtre butonlar\u0131)
"""

from src.ui.pages._dashboard_base_mixin import DashboardBaseMixin
from src.ui.pages._dashboard_data_mixin import DashboardDataMixin
from src.ui.pages._dashboard_dialog_mixin import DashboardDialogMixin
from src.ui.pages._dashboard_func_mixin import DashboardFuncMixin
from src.ui.pages._dashboard_ui_mixin import DashboardUIMixin


class DashboardActionsMixin(
    DashboardBaseMixin,
    DashboardDataMixin,
    DashboardDialogMixin,
    DashboardFuncMixin,
    DashboardUIMixin,
):
    """
    Dashboard i\u015flevselli\u011fini tek bir mixin \u00fczerinden sunan orkestrat\u00f6r s\u0131n\u0131f.
    Geriye d\u00f6n\u00fck tam uyumluluk sa\u011flanm\u0131\u015ft\u0131r; t\u00fcm orjinal metodlar korunmaktad\u0131r.
    """
    pass
