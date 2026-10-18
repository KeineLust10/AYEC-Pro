"""Reference-driven notification composer for the Admin Management Console."""
import json
import re
from pathlib import Path

from PyQt6.QtCore import QThread, pyqtSignal, pyqtSlot, QUrl
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QMessageBox
from PyQt6.QtWebChannel import QWebChannel
from PyQt6.QtWebEngineCore import QWebEngineSettings
from PyQt6.QtWebEngineWidgets import QWebEngineView

import api_client
from toast import show_toast


ICON_FALLBACKS = {
    "info": "i", "warning": "!", "report": "!", "rocket_launch": ">",
    "build": "+", "campaign": ">", "category": "#", "group_add": "+",
    "edit_note": "*", "format_bold": "B", "format_italic": "I", "format_list_bulleted": "*",
    "code": "&lt;&gt;", "send": ">", "desktop_windows": "#", "history_edu": "o",
    "history_toggle_off": "o", "sync": "R", "bolt": "!", "bookmark_manager": "*",
    "cell_tower": "o", "check_circle": "v", "close": "x", "dashboard": "#",
    "database": "#", "domain": "#", "done": "v", "key": "K",
    "logout": ">", "notifications_active": "!", "person": "o", "progress_activity": "o",
    "receipt_long": "#", "restart_alt": "R", "rule": "v", "search": "?",
    "system_update_alt": "v", "terminal": ">", "tune": "=", "vpn_key": "K",
    "calendar_clock": "o", "backup": "#",
}


REFERENCE = Path("C:/Users/yedek/Desktop/Y\u00f6netim Konsolu Tasar\u0131m/Merkezi bildirim.html")


class _NotificationCanvas(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._view = None

    def set_view(self, view):
        self._view = view
        view.setParent(self)
        self._place_view()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._place_view()

    def _place_view(self):
        if self._view is None:
            return
        expanded = self.width() >= 761
        offset = 264 if expanded else 0
        self._view.setGeometry(-offset, 0, self.width() + offset, self.height())


class _SendThread(QThread):
    done = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, targets: list[str], title: str, body: str, icon: str, popup: bool):
        super().__init__()
        self._targets = targets
        self._title = title
        self._body = body
        self._icon = icon
        self._popup = popup

    def run(self):
        try:
            results = [
                api_client.send_notification(target, self._title, self._body, self._icon, self._popup)
                for target in self._targets
            ]
            self.done.emit({"results": results, "sent_to": sum(int(r.get("sent_to", 0) or 0) for r in results)})
        except Exception as exc:
            self.error.emit(str(exc))


class _FetchCompanies(QThread):
    done = pyqtSignal(list)

    def run(self):
        try:
            self.done.emit(api_client.companies())
        except Exception:
            self.done.emit([])


class NotificationsPage(QWidget):
    def __init__(self):
        super().__init__()
        self._companies: list[dict] = []
        self._thread = None
        self._ready = False
        self._build_ui()
        self._load_companies()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self._canvas = _NotificationCanvas(self)
        layout.addWidget(self._canvas, 1)
        self._view = QWebEngineView(self._canvas)
        self._canvas.set_view(self._view)
        self._view.setObjectName("adminNotificationReference")
        settings = self._view.settings()
        settings.setDefaultTextEncoding("UTF-8")
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
        self._channel = QWebChannel(self._view.page())
        self._channel.registerObject("notifications", self)
        self._view.page().setWebChannel(self._channel)
        self._view.loadFinished.connect(self._on_loaded)
        source = REFERENCE.read_text(encoding="utf-8")
        source = re.sub(
            r'(<span\b(?=[^>]*\bmaterial-symbols-outlined\b)[^>]*>)\s*([^<]+?)\s*(</span>)',
            lambda match: match.group(1) + ICON_FALLBACKS.get(match.group(2).strip(), match.group(2)) + match.group(3),
            source,
        )
        head_match = re.search(r"<head\b[^>]*>(.*?)</head>", source, re.IGNORECASE | re.DOTALL)
        main_match = re.search(r"<main\b([^>]*)>(.*?)</main>", source, re.IGNORECASE | re.DOTALL)
        if not head_match or not main_match:
            raise RuntimeError("Notification reference is missing its head or main content")
        main_attrs = re.sub(r"\bpt-14\b", "", main_match.group(1))
        head = head_match.group(1) + '<script src="qrc:///qtwebchannel/qwebchannel.js"></script>'
        html = '<!doctype html><html lang="tr" class="dark"><head>%s</head><body class="bg-background font-body-default text-on-surface"><main%s>%s</main></body></html>' % (
            head, main_attrs, main_match.group(2)
        )
        self._view.setHtml(html, QUrl.fromLocalFile(str(REFERENCE.parent) + "/"))

    def _load_companies(self):
        self._company_thread = _FetchCompanies()
        self._thread = self._company_thread
        self._company_thread.done.connect(self._populate_companies)
        self._company_thread.start()

    def _populate_companies(self, companies: list):
        self._companies = [company for company in (companies or []) if company.get("active", 1)]
        if self._ready:
            self._bind_companies()

    def _on_loaded(self, ok: bool):
        if not ok:
            self._show_status("Tasarim referansi yuklenemedi.", False)
            return
        self._ready = True
        bootstrap = r"""
          (() => {
            const style=document.createElement('style');
            style.textContent='html,body{margin:0!important;min-height:100%;width:100%;font-family:"Plus Jakarta Sans","Segoe UI",Arial,sans-serif!important} body{background:#0e1321;color:#dee2f6} main{width:calc(100% - 288px)!important;margin-left:288px!important;padding-top:0!important} @media(max-width:760px){main{width:100%!important;margin-left:0!important;padding-top:0!important}} .font-display,.font-headline-lg,.font-headline-md,.font-body-default{font-family:"Plus Jakarta Sans","Segoe UI",Arial,sans-serif!important} .font-label-code,.font-badge-status{font-family:"JetBrains Mono","Segoe UI",Arial,monospace!important} .material-symbols-outlined{font-family:"Segoe UI Symbol","Segoe UI",Arial,sans-serif!important;font-variant-ligatures:none} #admin-notify-status{display:none;font:600 12px "Segoe UI",Arial,sans-serif;margin-top:8px;min-height:18px;color:#4edea3}';
            document.head.appendChild(style);
            const iconMap={info:'i',warning:'!',report:'!',rocket_launch:'>',build:'+',campaign:'>',category:'#',group_add:'+',edit_note:'*',format_bold:'B',format_italic:'I',format_list_bulleted:'*',code:'<>',send:'>',desktop_windows:'#',history_edu:'o',history_toggle_off:'o',sync:'R',bolt:'!',bookmark_manager:'*',cell_tower:'o',check_circle:'v',close:'x',dashboard:'#',database:'#',domain:'#',done:'v',key:'K',logout:'>',notifications_active:'!',person:'o',progress_activity:'o',receipt_long:'#',restart_alt:'R',rule:'v',search:'?',system_update_alt:'v',terminal:'>',tune:'=',vpn_key:'K',calendar_clock:'o',backup:'#'};
            const normalizeIcon=icon=>{const key=icon.textContent.trim();if(iconMap[key])icon.textContent=iconMap[key]};
            const normalizeIcons=root=>{if(root?.matches?.('.material-symbols-outlined'))normalizeIcon(root);root?.querySelectorAll?.('.material-symbols-outlined').forEach(normalizeIcon)};
            normalizeIcons(document);
            new MutationObserver(changes=>changes.forEach(change=>{if(change.type==='characterData'){normalizeIcons(change.target.parentElement);return}change.addedNodes.forEach(node=>{if(node.nodeType===1)normalizeIcons(node)})})).observe(document.body,{childList:true,characterData:true,subtree:true});
            const form=document.getElementById('broadcast-form');
            if(form&&!document.getElementById('admin-notify-status')){const status=document.createElement('div');status.id='admin-notify-status';form.appendChild(status)}
            document.querySelectorAll('[data-target="pilot"],[data-target="operator"]').forEach(b=>{b.disabled=true;b.title='Bu hedef grubu gonderim API tarafinda desteklenmiyor'});
            const test=document.getElementById('btn-test-send'); if(test){test.disabled=true;test.title='Test uc noktasi gonderimi API tarafinda desteklenmiyor'}
            document.querySelectorAll('button').forEach(b=>{if(b.textContent.includes('Planla (Cron)')){b.disabled=true;b.title='Planlama API tarafinda sunulmuyor'}});
            const send=document.getElementById('btn-broadcast-now');
            if(send){send.addEventListener('click',e=>{e.preventDefault();e.stopImmediatePropagation();
              const title=document.getElementById('push-title')?.value.trim()||'';
              const body=document.getElementById('push-body')?.value.trim()||'';
              const audience=document.querySelector('.audience-pill.bg-primary-container')?.dataset.target||'selected';
              const targets=audience==='all'?['all']:Array.from(document.querySelectorAll('.firm-checkbox:checked')).map(c=>c.dataset.id).filter(Boolean);
              const type=document.querySelector('.type-pill.ring-2')?.dataset.type||'info';
              const icons={info:'info',warning:'warning',danger:'error',update:'success',maintenance:'info'};
              const popup=!!document.getElementById('toggle-modal')?.checked;
              const confirm=!!document.getElementById('toggle-confirm')?.checked;
              if(!title||!body){window.notifyStatus('Baslik ve icerik bos birakilamaz.',false);return}
              if(!targets.length){window.notifyStatus('En az bir firma secin.',false);return}
              window.notificationsBridge.sendFromReference(JSON.stringify(targets),title,body,icons[type]||'info',popup,confirm);
            },true)}
            const bridgeScript=document.createElement('script');bridgeScript.src='qrc:///qtwebchannel/qwebchannel.js';bridgeScript.onload=()=>new QWebChannel(qt.webChannelTransport,channel=>{window.notificationsBridge=channel.objects.notifications;window.notifyStatus=(text,success)=>{if(window.notificationsBridge)window.notificationsBridge.showStatus(text,success)};window.notifyReady=true;});document.head.appendChild(bridgeScript);
          })();
        """
        self._view.page().runJavaScript(bootstrap)
        self._bind_companies()

    def _bind_companies(self):
        if not self._ready:
            return
        payload = json.dumps(self._companies, ensure_ascii=True)
        script = """(() => { const data=%s; const host=document.getElementById('firm-chips-container'); if(!host)return; host.replaceChildren();
          data.forEach((company,index)=>{const label=document.createElement('label');label.className=index<2?'cursor-pointer inline-flex items-center gap-2 px-3 py-1.5 rounded-lg bg-primary/20 text-primary font-label-code text-body-sm shadow-sm transition-all hover:bg-primary/25':'cursor-pointer inline-flex items-center gap-2 px-3 py-1.5 rounded-lg bg-surface-container-high text-on-surface-variant font-label-code text-body-sm transition-all hover:text-on-surface hover:bg-surface-bright';
            const box=document.createElement('input');box.type='checkbox';box.className='firm-checkbox accent-primary h-3.5 w-3.5 rounded';box.dataset.id=String(company.id||'');box.dataset.firm=String(company.company_name||'');box.checked=index<2;
            box.addEventListener('change',()=>{const count=host.querySelectorAll('.firm-checkbox:checked').length;const summary=document.getElementById('target-summary');if(summary)summary.textContent=count+' Firma Secili'});
            const name=document.createElement('span');name.textContent=String(company.company_name||'');const dot=document.createElement('span');dot.className='w-1.5 h-1.5 rounded-full bg-outline';label.append(box,name,dot);host.append(label);
          });
          const summary=document.getElementById('target-summary');if(summary)summary.textContent=data.length?Math.min(data.length,2)+' Firma Secili':'Firma verisi kullanilamiyor';
        })();""" % payload
        self._view.page().runJavaScript(script)

    def _show_status(self, message: str, success: bool):
        show_toast(self, message, "success" if success else "error")

    @pyqtSlot(str, bool)
    def showStatus(self, message: str, success: bool):
        self._show_status(message, success)

    @pyqtSlot(str, str, str, str, bool, bool)
    def sendFromReference(self, targets_json: str, title: str, body: str, icon: str, popup: bool, confirm: bool):
        try:
            targets = json.loads(targets_json)
        except (TypeError, ValueError):
            self._show_status("Firma secimi okunamadi.", False)
            return
        if not isinstance(targets, list) or not targets or not title.strip() or not body.strip():
            self._show_status("Firma, baslik ve icerik zorunludur.", False)
            return
        if confirm and QMessageBox.question(
            self, "Yayini Onayla", "Secilen firmalara bildirim gonderilsin mi?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        ) != QMessageBox.StandardButton.Yes:
            self._show_status("Gonderim iptal edildi.", False)
            return
        self._show_status("Bildirim kuyruga ekleniyor...", True)
        self._thread = _SendThread([str(target) for target in targets], title.strip(), body.strip(), icon, popup)
        self._thread.done.connect(lambda result: self._show_status(
            "Bildirim API tarafindan kabul edildi.", True
        ))
        self._thread.error.connect(lambda error: self._show_status("Gonderim basarisiz: " + error, False))
        self._thread.start()
