"""Discover and safely operate controls exposed by the active ERP screen."""

import re
import unicodedata

from PyQt6.QtCore import QDate, QDateTime, QItemSelectionModel, QPoint, QTime, Qt
from PyQt6.QtGui import QAction, QValidator, QTextCursor
from PyQt6.QtWidgets import (
    QAbstractButton,
    QAbstractItemView,
    QAbstractSpinBox,
    QComboBox,
    QDateEdit,
    QDateTimeEdit,
    QDoubleSpinBox,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QRadioButton,
    QSlider,
    QSpinBox,
    QTextEdit,
    QTimeEdit,
    QTabWidget,
    QWidget,
)


def _normalize(value):
    text = unicodedata.normalize("NFKD", str(value or "").casefold())
    return "".join(char for char in text if not unicodedata.combining(char))


def _label_for(root, widget):
    parts = [widget.accessibleName(), widget.objectName(), widget.toolTip()]
    if isinstance(widget, QLineEdit):
        parts.append(widget.placeholderText())
    buddy_labels = []
    for label in root.findChildren(QLabel):
        try:
            if label.buddy() is widget:
                buddy_labels.append(label.text())
        except RuntimeError:
            continue
    inferred_label = None
    if not buddy_labels and isinstance(
        widget,
        (QLineEdit, QComboBox, QTextEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox, QSlider, QDateEdit, QTimeEdit, QDateTimeEdit),
    ):
        try:
            widget_pos = widget.mapTo(root, QPoint(0, 0))
            widget_rect = widget.rect()
            widget_left = widget_pos.x()
            widget_right = widget_left + widget_rect.width()
            widget_top = widget_pos.y()
            widget_bottom = widget_top + widget_rect.height()
            candidates = []
            for label in root.findChildren(QLabel):
                if not label.isVisible() or not label.text().strip():
                    continue
                label_pos = label.mapTo(root, QPoint(0, 0))
                label_rect = label.rect()
                left = label_pos.x()
                right = left + label_rect.width()
                top = label_pos.y()
                bottom = top + label_rect.height()
                vertical_overlap = min(widget_bottom, bottom) - max(widget_top, top)
                horizontal_overlap = min(widget_right, right) - max(widget_left, left)
                if bottom <= widget_top + 8:
                    vertical_gap = max(0, widget_top - bottom)
                    horizontal_gap = max(0, max(widget_left - right, left - widget_right))
                    if vertical_gap <= 72 and (horizontal_overlap > 0 or horizontal_gap <= 56):
                        candidates.append((vertical_gap + horizontal_gap * 2, label.text()))
                elif vertical_overlap > 0 and right <= widget_left + 8:
                    horizontal_gap = max(0, widget_left - right)
                    if horizontal_gap <= 120:
                        candidates.append((36 + horizontal_gap + abs(top - widget_top), label.text()))
            if candidates:
                inferred_label = min(candidates, key=lambda item: item[0])[1]
        except RuntimeError:
            inferred_label = None
    parts = buddy_labels + ([inferred_label] if inferred_label else []) + parts
    return " / ".join(dict.fromkeys(str(part).strip() for part in parts if str(part or "").strip()))


def label_for_control(root, widget):
    return _label_for(root, widget)


def snapshot_control(control):
    """Capture a reversible scalar state; sensitive text and side effects are excluded."""
    if isinstance(control, QRadioButton):
        group = control.group()
        if group is not None:
            checked = group.checkedButton()
            return ("radio", checked if isinstance(checked, QRadioButton) else None)
        parent = control.parentWidget()
        radios = [
            item for item in parent.findChildren(QRadioButton)
            if item.parentWidget() is parent
        ] if parent is not None else [control]
        checked = next((item for item in radios if item.isChecked()), None)
        return ("radio", checked)
    if isinstance(control, QLineEdit):
        if control.echoMode() != QLineEdit.EchoMode.Normal:
            return None
        return ("set", control.text())
    if isinstance(control, (QTextEdit, QPlainTextEdit)):
        return ("set", control.toPlainText())
    if isinstance(control, QComboBox):
        return ("select", control.currentText())
    if isinstance(control, QAbstractButton) and control.isCheckable():
        return ("toggle", bool(control.isChecked()))
    if isinstance(control, (QSpinBox, QDoubleSpinBox, QSlider)):
        return ("set", control.value())
    return None


def restore_control(control, state):
    """Restore a captured scalar state after confirming the control is still live."""
    if not state:
        return False, "Bu kontrol icin guvenli geri alma bulunmuyor."
    operation, value = state
    if operation == "radio" and isinstance(control, QRadioButton):
        return apply_control(control, "radio_restore", value)
    if operation == "select" and isinstance(control, QComboBox) and control.isEditable() and not str(value or ""):
        control.setCurrentIndex(-1)
        if control.lineEdit() is not None:
            control.lineEdit().clear()
        return True, "Se\u00e7im alan\u0131n\u0131 geri ald\u0131m."
    return apply_control(control, operation, value, overwrite=True)


def _radio_group(control):
    group = control.group()
    if group is not None:
        return [item for item in group.buttons() if isinstance(item, QRadioButton)]
    parent = control.parentWidget()
    if parent is None:
        return [control]
    return [
        item for item in parent.findChildren(QRadioButton)
        if item.parentWidget() is parent
    ]


def describe_controls(root, limit=240, utterance=None):
    """Return model-safe descriptions and an in-process widget binding map."""
    descriptions = []
    bindings = {}
    if root is None:
        return descriptions, bindings
    widget_limit = max(1, limit - 20)

    for widget in root.findChildren(QWidget):
        try:
            if not widget.isVisible() or not widget.isEnabled():
                continue
            if isinstance(widget, QLineEdit):
                owner = widget.parentWidget()
                if isinstance(owner, (QComboBox, QAbstractSpinBox)):
                    continue
            label = _label_for(root, widget)
            if isinstance(widget, QAbstractButton):
                text = (
                    widget.text().replace("&", "").strip()
                    or widget.accessibleName().strip()
                    or widget.objectName().strip()
                    or widget.toolTip().strip()
                )
                if not text:
                    continue
                kind = "radio" if isinstance(widget, QRadioButton) else (
                    "check" if widget.isCheckable() else "button"
                )
                description = {"id": "c%d" % len(descriptions), "type": kind, "label": text}
                if label:
                    description["hint"] = label[:120]
                if kind in {"radio", "check"}:
                    description["checked"] = bool(widget.isChecked())
            elif isinstance(widget, QAbstractItemView):
                if isinstance(widget, QHeaderView):
                    continue
                model = widget.model()
                if model is None:
                    continue
                columns = [
                    str(model.headerData(i, Qt.Orientation.Horizontal, Qt.ItemDataRole.DisplayRole) or "")
                    for i in range(min(model.columnCount(), 12))
                ]
                description = {
                    "id": "c%d" % len(descriptions), "type": "table",
                    "label": label or widget.objectName() or "Kayit listesi",
                    "columns": [column for column in columns if column][:12],
                    "row_count": model.rowCount(),
                }
                if utterance and model.rowCount():
                    command_words = {
                        "ac", "acalim", "sec", "secin", "secelim", "ilerle",
                        "onayla", "goster", "goruntule", "detay", "kayit",
                        "servis", "cihaz", "musteri", "panel", "lutfen", "bana",
                        "icin", "ait", "bulunan", "olan", "listeden", "sonraki",
                    }
                    request_terms = {
                        token for token in re.findall(r"\w+", _normalize(utterance))
                        if len(token) > 2 and token not in command_words
                    }
                    candidates = []
                    for row in range(min(model.rowCount(), 1000)):
                        values = []
                        for column in range(min(model.columnCount(), 12)):
                            value = str(
                                model.data(model.index(row, column), Qt.ItemDataRole.DisplayRole) or ""
                            ).strip()
                            if value:
                                values.append(value[:100])
                        row_text = " | ".join(values)
                        normalized_row = _normalize(row_text)
                        overlap = sum(term in normalized_row for term in request_terms)
                        if row_text and (not request_terms or overlap):
                            candidates.append((overlap, row, values, row_text))
                    candidates.sort(key=lambda item: (-item[0], item[1]))
                    description["rows"] = [
                        {"index": row, "values": values, "match_text": row_text}
                        for _score, row, values, row_text in candidates[:12]
                    ]
            elif isinstance(widget, QComboBox):
                options = [widget.itemText(i) for i in range(min(widget.count(), 40))]
                normalized_utterance = _normalize(utterance) if utterance else ""
                if normalized_utterance:
                    for index in range(40, widget.count()):
                        option = widget.itemText(index)
                        normalized_option = _normalize(option)
                        if normalized_option and normalized_option in normalized_utterance:
                            options.append(option)
                            if len(options) >= 60:
                                break
                if not options:
                    continue
                description = {
                    "id": "c%d" % len(descriptions), "type": "combo",
                    "label": label or widget.objectName() or "Secim listesi",
                    "options": options,
                    "editable": widget.isEditable(),
                    "required": bool(widget.property("required")) or "*" in label,
                    "filled": bool(widget.currentText().strip()),
                }
            elif isinstance(widget, QLineEdit):
                description = {
                    "id": "c%d" % len(descriptions), "type": "text",
                    "label": label or "Metin alani",
                    "filled": bool(widget.text().strip()),
                    "required": bool(widget.property("required")) or "*" in label,
                }
            elif isinstance(widget, (QTextEdit, QPlainTextEdit)):
                value = widget.toPlainText()
                description = {
                    "id": "c%d" % len(descriptions), "type": "multiline",
                    "label": label or "Aciklama alani", "filled": bool(value.strip()),
                    "required": bool(widget.property("required")) or "*" in label,
                }
            elif isinstance(widget, (QSpinBox, QDoubleSpinBox, QSlider)):
                description = {
                    "id": "c%d" % len(descriptions), "type": "number",
                    "label": label or "Sayisal alan",
                    "minimum": widget.minimum(), "maximum": widget.maximum(),
                }
            elif isinstance(widget, QDateEdit):
                description = {"id": "c%d" % len(descriptions), "type": "date", "label": label or "Tarih"}
            elif isinstance(widget, QTimeEdit):
                description = {"id": "c%d" % len(descriptions), "type": "time", "label": label or "Saat"}
            elif isinstance(widget, QDateTimeEdit):
                description = {"id": "c%d" % len(descriptions), "type": "datetime", "label": label or "Tarih ve saat"}
            elif isinstance(widget, QTabWidget):
                tabs = [widget.tabText(i) for i in range(min(widget.count(), 30))]
                if not tabs:
                    continue
                description = {
                    "id": "c%d" % len(descriptions), "type": "tabs",
                    "label": label or "Sekmeler", "options": tabs,
                }
            else:
                continue
            control_id = description["id"]
            descriptions.append(description)
            bindings[control_id] = widget
            if len(descriptions) >= widget_limit:
                break
        except RuntimeError:
            continue

    for action in root.findChildren(QAction):
        try:
            label = action.text().replace("&", "").strip() or action.objectName().strip() or action.toolTip().strip()
            if not action.isVisible() or not action.isEnabled() or not label:
                continue
            control_id = "c%d" % len(descriptions)
            descriptions.append({
                "id": control_id,
                "type": "action",
                "label": label,
            })
            bindings[control_id] = action
            if len(descriptions) >= limit:
                break
        except RuntimeError:
            continue
    return descriptions, bindings


def action_needs_confirmation(control, root=None):
    try:
        if isinstance(control, QLineEdit) and control.echoMode() != QLineEdit.EchoMode.Normal:
            return True
        if isinstance(control, (QAbstractButton, QAction)):
            labels = [control.text()]
        elif isinstance(control, QWidget):
            labels = [control.accessibleName(), control.objectName(), control.toolTip()]
        else:
            labels = []
        if root is not None:
            labels.append(_label_for(root, control))
    except RuntimeError:
        return True
    words = (
        "kaydet", "ekle", "olustur", "sil", "gonder", "odeme", "ode",
        "aktar", "senkron", "onayla", "tamamla", "fatura kes", "stok dus",
        "arsivle", "iade", "kabul", "yetki", "lisans", "etkinlestir",
        "etkin", "devre disi", "kapat", "iptal et", "fiyat", "tutar",
        "aktif", "pasif", "toplu", "bulk", "enable", "disable",
        "tahsilat", "iskonto", "stok", "delete", "save", "send", "pay",
        "transfer", "approve", "submit", "create", "add", "close",
    )
    normalized = _normalize(" ".join(str(label or "") for label in labels))
    if any(word in normalized for word in words):
        return True
    if isinstance(control, QAction) or (
        isinstance(control, QAbstractButton) and not control.isCheckable()
    ):
        tokens = set(normalized.split())
        safe_exact = {
            "ac", "oku", "ara", "bul", "yenile", "onceki", "sonraki",
            "ileri", "geri", "search", "view", "open", "refresh", "back",
            "next", "previous",
        }
        safe_prefixes = (
            "goruntule", "goster", "filtrele", "sirala", "detay", "listele",
            "onizle", "filter", "sort", "details", "preview",
        )
        if tokens.intersection(safe_exact) or any(
            token.startswith(action) for token in tokens for action in safe_prefixes
        ):
            return False
        return True
    return False


def apply_control(control, operation, value=None, overwrite=False):
    """Apply a validated operation to one current Qt control."""
    if control is None or not control.isEnabled() or not control.isVisible():
        return False, "Bu kontrol art\u0131k eri\u015filebilir de\u011fil."
    try:
        if operation == "click" and isinstance(control, (QAbstractButton, QAction)):
            control.trigger() if isinstance(control, QAction) else control.click()
            return True, "D\u00fc\u011fmeye bast\u0131m; kayd\u0131n tamamland\u0131\u011f\u0131n\u0131 aray\u00fczden do\u011frulayam\u0131yorum."
        if operation == "set" and isinstance(control, (QLineEdit, QTextEdit, QPlainTextEdit)):
            current = control.text() if isinstance(control, QLineEdit) else control.toPlainText()
            if current.strip() and not overwrite:
                return False, "Alan dolu; de\u011fi\u015ftirmeden \u00f6nce a\u00e7\u0131k\u00e7a onaylaman\u0131z gerekiyor."
            if isinstance(control, QLineEdit):
                validator = control.validator()
                if validator is not None:
                    candidate = str(value or "")
                    state, _candidate, _position = validator.validate(candidate, len(candidate))
                    if state != QValidator.State.Acceptable:
                        return False, "De\u011fer bu alan\u0131n giri\u015f do\u011frulamas\u0131na uymuyor."
                control.setText(str(value or ""))
            else:
                control.setPlainText(str(value or ""))
            return True, "Alan\u0131 doldurdum."
        if operation in {"clear", "delete_word", "cursor_start", "cursor_end", "insert"} and isinstance(
            control, (QLineEdit, QTextEdit, QPlainTextEdit)
        ):
            if operation == "clear":
                control.clear()
                return True, "Metin alanini temizledim."
            if isinstance(control, QLineEdit):
                if operation == "cursor_start":
                    control.setCursorPosition(0)
                elif operation == "cursor_end":
                    control.setCursorPosition(len(control.text()))
                elif operation == "insert":
                    if "\n" in str(value or ""):
                        return False, "Yeni satir eklemek icin cok satirli bir alan secin."
                    control.insert(str(value or ""))
                else:
                    position = control.cursorPosition()
                    text = control.text()
                    start = position
                    while start > 0 and text[start - 1].isspace():
                        start -= 1
                    while start > 0 and not text[start - 1].isspace():
                        start -= 1
                    control.setSelection(start, position - start)
                    control.insert("")
            else:
                cursor = control.textCursor()
                if operation == "cursor_start":
                    cursor.movePosition(QTextCursor.MoveOperation.Start)
                elif operation == "cursor_end":
                    cursor.movePosition(QTextCursor.MoveOperation.End)
                elif operation == "insert":
                    cursor.insertText(str(value or ""))
                else:
                    cursor.movePosition(QTextCursor.MoveOperation.PreviousWord, QTextCursor.MoveMode.KeepAnchor)
                    cursor.removeSelectedText()
                control.setTextCursor(cursor)
            return True, "Metin alanini guncelledim."
        if operation == "select" and isinstance(control, QComboBox):
            target = _normalize(value)
            for index in range(control.count()):
                if _normalize(control.itemText(index)) == target:
                    control.setCurrentIndex(index)
                    return True, "Se\u00e7imi yapt\u0131m."
            return False, "\u0130stenen se\u00e7enek listede bulunamad\u0131."
        if operation == "clear" and isinstance(control, QComboBox):
            if control.isEditable():
                control.setCurrentIndex(-1)
                if control.lineEdit() is not None:
                    control.lineEdit().clear()
            elif control.count():
                control.setCurrentIndex(0)
            else:
                control.setCurrentIndex(-1)
            return True, "Se\u00e7im alan\u0131n\u0131 temizledim."
        if operation == "select" and isinstance(control, QTabWidget):
            target = _normalize(value)
            for index in range(control.count()):
                if _normalize(control.tabText(index)) == target:
                    control.setCurrentIndex(index)
                    return True, "Sekmeyi a\u00e7t\u0131m."
            return False, "\u0130stenen sekme bulunamad\u0131."
        if operation == "select" and isinstance(control, QAbstractItemView):
            model = control.model()
            query = _normalize(value)
            if model is None or not query:
                return False, "Aranacak kayit adini belirtin."
            query_text = " ".join(re.findall(r"\w+", query))
            exact = []
            partial = []
            for row in range(min(model.rowCount(), 500)):
                values = [
                    _normalize(model.data(model.index(row, column), Qt.ItemDataRole.DisplayRole))
                    for column in range(min(model.columnCount(), 20))
                ]
                row_text = _normalize(" ".join(value for value in values if value))
                row_words = " ".join(re.findall(r"\w+", row_text))
                if query in values or query_text == row_words:
                    exact.append(row)
                elif query_text and query_text in row_words or any(query in item for item in values if item):
                    partial.append(row)
            matches = exact or partial
            if len(matches) != 1:
                if matches:
                    return False, "Birden fazla kayit eslesti; daha belirgin bir ad soyleyin."
                return False, "Bu listede soylediginiz kaydi bulamadim."
            index = model.index(matches[0], 0)
            control.setCurrentIndex(index)
            selection = control.selectionModel()
            selection.select(
                index,
                QItemSelectionModel.SelectionFlag.ClearAndSelect | QItemSelectionModel.SelectionFlag.Rows,
            )
            control.setFocus(Qt.FocusReason.OtherFocusReason)
            control.scrollTo(index)
            return True, "Kaydi listede buldum ve secili hale getirdim."
        if operation == "toggle" and isinstance(control, QAbstractButton) and control.isCheckable():
            if isinstance(control, QRadioButton) and not bool(value):
                return False, "Bir radio secenegini kapatmak yerine diger secenegi secin."
            control.setChecked(bool(value))
            return True, "Se\u00e7imi g\u00fcncelledim."
        if operation == "radio_restore" and isinstance(control, QRadioButton):
            if value is None:
                if control.isChecked():
                    control.setAutoExclusive(False)
                    control.setChecked(False)
                    control.setAutoExclusive(True)
                return True, "Onceki radyo secimini geri yukledim."
            if value not in _radio_group(control) or not value.isEnabled() or not value.isVisible():
                return False, "Onceki radio secenegi artik kullanilabilir degil."
            value.setChecked(True)
            return True, "Onceki radyo secimini geri yukledim."
        if operation == "set" and isinstance(control, (QSpinBox, QDoubleSpinBox, QSlider)):
            number = float(value)
            if number < control.minimum() or number > control.maximum():
                return False, "De\u011fer alan\u0131n izin verilen aral\u0131\u011f\u0131n\u0131n d\u0131\u015f\u0131nda."
            control.setValue(int(number) if isinstance(control, (QSpinBox, QSlider)) else number)
            return True, "Say\u0131sal alan\u0131 g\u00fcncelledim."
        if operation == "set" and isinstance(control, QDateEdit):
            parsed = QDate.fromString(str(value), "yyyy-MM-dd")
            if parsed.isValid():
                control.setDate(parsed)
                return True, "Tarihi g\u00fcncelledim."
        if operation == "set" and isinstance(control, QTimeEdit):
            parsed = QTime.fromString(str(value), "HH:mm")
            if parsed.isValid():
                control.setTime(parsed)
                return True, "Saati g\u00fcncelledim."
        if operation == "set" and isinstance(control, QDateTimeEdit):
            parsed = QDateTime.fromString(str(value), "yyyy-MM-dd HH:mm")
            if parsed.isValid():
                control.setDateTime(parsed)
                return True, "Tarih ve saati g\u00fcncelledim."
        return False, "Bu kontrol t\u00fcr\u00fc i\u00e7in desteklenen bir i\u015flem bulunmuyor."
    except (TypeError, ValueError, RuntimeError):
        return False, "Kontrol de\u011feri uygulanamad\u0131; l\u00fctfen de\u011feri tekrar s\u00f6yleyin."


def move_focus(root, forward=True):
    from PyQt6.QtWidgets import QApplication

    if root is None:
        return False, "Odaklan\u0131lacak bir ekran yok."
    current = QApplication.focusWidget()
    if current is None or (current is not root and not root.isAncestorOf(current)):
        current = root
    chain = []
    seen = {id(current)}
    candidate = current
    for _index in range(1000):
        candidate = candidate.nextInFocusChain()
        if candidate is None or id(candidate) in seen:
            break
        seen.add(id(candidate))
        if (candidate is root or root.isAncestorOf(candidate)) and candidate.isVisible() and candidate.isEnabled():
            if candidate.focusPolicy() != Qt.FocusPolicy.NoFocus:
                chain.append(candidate)
    if not chain:
        return False, "Bu ekranda odaklanabilir bir alan bulamad\u0131m."
    if forward:
        target = chain[0]
    else:
        target = chain[-1]
    target.setFocus(Qt.FocusReason.OtherFocusReason)
    label = _label_for(root, target) or target.objectName() or "sonraki alan"
    return True, str(label) + " alan\u0131na odakland\u0131m."


def append_dictation(root, text):
    from PyQt6.QtWidgets import QApplication

    widget = QApplication.focusWidget()
    if widget is None or (widget is not root and not root.isAncestorOf(widget)):
        return False, "\u00d6nce yaz\u0131lacak metin alan\u0131na odaklan\u0131n."
    text = str(text or "").strip()
    if not text:
        return False, "Dikte edilecek metin alg\u0131lanmad\u0131."
    if isinstance(widget, QLineEdit):
        widget.setCursorPosition(len(widget.text()))
        if widget.text().strip():
            widget.insert(" ")
        widget.insert(text)
        return True, "Metni alana ekledim."
    if isinstance(widget, (QTextEdit, QPlainTextEdit)):
        if widget.toPlainText().strip():
            widget.moveCursor(QTextCursor.MoveOperation.End)
            widget.insertPlainText("\n")
        widget.insertPlainText(text)
        return True, "Metni a\u00e7\u0131klama alan\u0131na ekledim."
    return False, "Odaklanan kontrol bir metin alan\u0131 de\u011fil."


def focused_text_control(root):
    from PyQt6.QtWidgets import QApplication

    widget = QApplication.focusWidget()
    if widget is None or (widget is not root and not root.isAncestorOf(widget)):
        return None
    if isinstance(widget, (QLineEdit, QTextEdit, QPlainTextEdit)):
        return widget
    return None


def read_active_field(root):
    from PyQt6.QtWidgets import QApplication

    widget = QApplication.focusWidget()
    if widget is None or (widget is not root and not root.isAncestorOf(widget)):
        return "\u015eu anda se\u00e7ili bir alan yok."
    if isinstance(widget, QLineEdit):
        if widget.echoMode() != QLineEdit.EchoMode.Normal:
            return "Bu g\u00fcvenli bir parola alan\u0131d\u0131r; i\u00e7eri\u011fini sesli okumuyorum."
        return widget.text() or "Bu alan bo\u015f."
    if isinstance(widget, (QTextEdit, QPlainTextEdit)):
        return widget.toPlainText() or "Bu alan bo\u015f."
    if isinstance(widget, QComboBox):
        return widget.currentText() or "Se\u00e7im yap\u0131lmam\u0131\u015f."
    if isinstance(widget, QDateEdit):
        return widget.date().toString("yyyy-MM-dd")
    if isinstance(widget, QTimeEdit):
        return widget.time().toString("HH:mm")
    if isinstance(widget, QDateTimeEdit):
        return widget.dateTime().toString("yyyy-MM-dd HH:mm")
    if isinstance(widget, QAbstractSpinBox):
        return widget.text()
    if isinstance(widget, QSlider):
        return str(widget.value())
    if isinstance(widget, QAbstractButton) and widget.isCheckable():
        state = "se\u00e7ili" if widget.isChecked() else "se\u00e7ili de\u011fil"
        return (widget.text() or "Se\u00e7enek") + ": " + state
    if isinstance(widget, QAbstractItemView):
        index = widget.currentIndex()
        model = widget.model()
        if model is None or not index.isValid():
            return "Listede secili bir kayit yok."
        row = index.row()
        values = []
        for column in range(min(model.columnCount(), 12)):
            value = str(model.data(model.index(row, column), Qt.ItemDataRole.DisplayRole) or "").strip()
            if value:
                header = str(model.headerData(column, Qt.Orientation.Horizontal, Qt.ItemDataRole.DisplayRole) or "").strip()
                values.append((header + ": " if header else "") + value)
        return ". ".join(values) if values else "Secili kayit bos."
    return _label_for(root, widget) or "Se\u00e7ili kontrol\u00fcn okunabilir bir de\u011feri yok."


def read_screen(root, limit=24):
    if root is None:
        return "Okunacak bir ekran yok."
    parts = []
    for widget in root.findChildren(QWidget):
        try:
            if not widget.isVisible() or not widget.isEnabled():
                continue
            if isinstance(widget, QLabel) and widget.text().strip():
                parts.append(widget.text().strip())
            elif isinstance(widget, QAbstractButton) and widget.text().strip():
                parts.append(widget.text().replace("&", "").strip())
            elif isinstance(widget, QTabWidget):
                parts.extend(widget.tabText(i).strip() for i in range(widget.count()) if widget.tabText(i).strip())
            if len(parts) >= limit:
                break
        except RuntimeError:
            continue
    if type(root).__name__ == "StockImportPreviewDialog":
        for view in root.findChildren(QAbstractItemView):
            try:
                model = view.model()
                if model is None or model.rowCount() < 1:
                    continue
                samples = []
                for row in range(min(model.rowCount(), 5)):
                    cells = []
                    for column in range(min(model.columnCount(), 8)):
                        value = str(
                            model.data(model.index(row, column), Qt.ItemDataRole.DisplayRole) or ""
                        ).strip()
                        if value:
                            header = str(
                                model.headerData(
                                    column, Qt.Orientation.Horizontal,
                                    Qt.ItemDataRole.DisplayRole,
                                ) or ""
                            ).strip()
                            cells.append((header + ": " if header else "") + value[:80])
                    if cells:
                        samples.append("Satir " + str(row + 1) + ": " + ", ".join(cells))
                if samples:
                    parts.append(
                        "OCR onizlemesi toplam " + str(model.rowCount()) +
                        " satir. Ilk satirlardan ornek: " + ". ".join(samples)
                    )
                break
            except RuntimeError:
                continue
    unique = list(dict.fromkeys(parts))[:limit]
    return ". ".join(unique) if unique else "Bu ekranda okunabilir bir ba\u015fl\u0131k yok."


def scroll_screen(root, forward=True):
    from PyQt6.QtWidgets import QAbstractScrollArea

    if root is None:
        return False, "Kayd\u0131r\u0131lacak bir ekran yok."
    for area in root.findChildren(QAbstractScrollArea):
        if not area.isVisible() or not area.isEnabled():
            continue
        bar = area.verticalScrollBar()
        delta = max(40, int(bar.pageStep() * 0.7))
        bar.setValue(bar.value() + (delta if forward else -delta))
        return True, "Ekran\u0131 a\u015fa\u011f\u0131 kayd\u0131rd\u0131m." if forward else "Ekran\u0131 yukar\u0131 kayd\u0131rd\u0131m."
    return False, "Bu ekranda kayd\u0131r\u0131labilir bir b\u00f6l\u00fcm bulamad\u0131m."


def move_item_selection(root, forward=True):
    if root is None:
        return False, "Kayit listesi bulunamadi."
    from PyQt6.QtWidgets import QApplication

    focused = QApplication.focusWidget()
    views = [view for view in root.findChildren(QAbstractItemView) if view.isVisible() and view.isEnabled()]
    view = focused if isinstance(focused, QAbstractItemView) else (views[0] if views else None)
    if view is None or view.model() is None or view.model().rowCount() < 1:
        return False, "Bu ekranda gezilebilir bir kayit listesi yok."
    row = view.currentIndex().row()
    row = min(view.model().rowCount() - 1, row + 1) if forward else max(0, row - 1)
    index = view.model().index(row, 0)
    view.setCurrentIndex(index)
    view.selectionModel().select(
        index,
        QItemSelectionModel.SelectionFlag.ClearAndSelect | QItemSelectionModel.SelectionFlag.Rows,
    )
    view.setFocus(Qt.FocusReason.OtherFocusReason)
    view.scrollTo(index)
    return True, read_active_field(root)


def activate_selected_item(root):
    if root is None:
        return False, "Acik ekran bulunamadi."
    from PyQt6.QtTest import QTest
    from PyQt6.QtWidgets import QApplication

    focused = QApplication.focusWidget()
    views = [view for view in root.findChildren(QAbstractItemView) if view.isVisible() and view.isEnabled()]
    view = focused if isinstance(focused, QAbstractItemView) else (views[0] if views else None)
    if view is None or not view.currentIndex().isValid():
        return False, "Once acmak istediginiz kaydi listeden secin."
    view.setFocus(Qt.FocusReason.OtherFocusReason)
    QTest.keyClick(view, Qt.Key.Key_Return)
    return True, "Secili kaydi actim."


def table_row_open_handler_available(view):
    if not isinstance(view, QAbstractItemView):
        return False
    if hasattr(view, "cellDoubleClicked") and view.receivers(view.cellDoubleClicked):
        return True
    if hasattr(view, "itemDoubleClicked") and view.receivers(view.itemDoubleClicked):
        return True
    baseline_receivers = 1 if hasattr(view, "itemDoubleClicked") else 0
    return view.receivers(view.doubleClicked) > baseline_receivers


def activate_table_row(view):
    """Open the selected table row through its normal double-click handlers."""
    if (
        not isinstance(view, QAbstractItemView)
        or not view.isVisible()
        or not view.isEnabled()
        or not view.currentIndex().isValid()
    ):
        return False
    index = view.currentIndex()
    dispatched = False
    if hasattr(view, "cellDoubleClicked") and view.receivers(view.cellDoubleClicked):
        view.cellDoubleClicked.emit(index.row(), index.column())
        dispatched = True
    if hasattr(view, "itemDoubleClicked") and view.receivers(view.itemDoubleClicked):
        item = view.item(index.row(), index.column()) if hasattr(view, "item") else None
        if item is not None:
            view.itemDoubleClicked.emit(item)
            dispatched = True
    baseline_receivers = 1 if hasattr(view, "itemDoubleClicked") else 0
    if view.receivers(view.doubleClicked) > baseline_receivers:
        view.doubleClicked.emit(index)
        dispatched = True
    return dispatched


def search_screen(root, query):
    if root is None or not str(query or "").strip():
        return False, "Aranacak metni soyleyin."
    candidates = []
    for field in root.findChildren(QLineEdit):
        if not field.isVisible() or not field.isEnabled() or field.isReadOnly():
            continue
        label = _normalize(_label_for(root, field))
        if any(word in label for word in ("ara", "search", "bul", "filtre")):
            candidates.append(field)
    if not candidates:
        return False, "Bu ekranda sesle kullanilabilir bir arama alani bulamadim."
    if len(candidates) > 1:
        ranked = [
            field for field in candidates
            if any(word in _normalize(_label_for(root, field)) for word in ("ara", "search"))
        ]
        candidates = ranked or candidates
    if len(candidates) != 1:
        return False, "Birden fazla arama alani var. Hangi bolumde arayayim?"
    field = candidates[0]
    field.setFocus(Qt.FocusReason.OtherFocusReason)
    field.setText(str(query).strip())
    field.returnPressed.emit()
    return True, "Aramayi baslattim."


def read_form_feedback(root, limit=8):
    if root is None:
        return "Kontrol edilecek bir form yok."
    markers = (
        "zorunlu", "gecersiz", "hata", "uyari", "eksik", "uygun degil",
        "invalid", "required", "error", "must be",
    )
    feedback = []
    for label in root.findChildren(QLabel):
        if not label.isVisible():
            continue
        value = label.text().strip()
        if value and any(marker in _normalize(value) for marker in markers):
            feedback.append(value)
    for field in root.findChildren(QLineEdit):
        if not field.isVisible() or not field.isEnabled() or not field.text().strip():
            continue
        validator = field.validator()
        if validator is None:
            continue
        state, _value, _position = validator.validate(field.text(), field.cursorPosition())
        if state != QValidator.State.Acceptable:
            feedback.append((_label_for(root, field) or "Metin alani") + ": deger dogrulamadan gecmedi.")
    unique = list(dict.fromkeys(feedback))[:limit]
    return ". ".join(unique) if unique else "Gorunen bir form dogrulama hatasi yok."


def confirmation_summary(root, control, operation, value=None, limit=5):
    """Build a spoken confirmation summary without exposing password contents."""
    label = _label_for(root, control) if root is not None and control is not None else ""
    parts = []
    if label:
        parts.append("Kontrol: " + label[:80])
    protected_target = (
        isinstance(control, QLineEdit)
        and control.echoMode() != QLineEdit.EchoMode.Normal
    )
    if operation == "set" and value is not None and not protected_target:
        parts.append("Yazilacak deger: " + str(value)[:100])
    elif operation == "set" and protected_target:
        parts.append("Parola alanina deger girilecek")
    if root is None:
        return ". ".join(parts)
    for view in root.findChildren(QAbstractItemView):
        if len(parts) >= limit:
            break
        if not view.isVisible() or not view.currentIndex().isValid():
            continue
        summary = read_active_field_for_view(view)
        if summary:
            parts.append("Secili kayit: " + summary[:140])
            break
    fields = [field for field in root.findChildren(QLineEdit) if field.isVisible() and field.text().strip()]
    for field in fields:
        if field.echoMode() == QLineEdit.EchoMode.Normal:
            continue
        parts.append((_label_for(root, field) or "Parola alani") + ": dolu parola alani")
        if len(parts) >= limit:
            return ". ".join(parts[:limit])
    for field in fields:
        if len(parts) >= limit:
            break
        if field.echoMode() != QLineEdit.EchoMode.Normal or field.objectName().startswith("qt_"):
            continue
        name = _label_for(root, field) or "Metin alani"
        parts.append(name + ": " + field.text().strip()[:100])
    if len(parts) < limit:
        for combo in root.findChildren(QComboBox):
            if not combo.isVisible() or not combo.currentText().strip():
                continue
            parts.append((_label_for(root, combo) or "Secim") + ": " + combo.currentText()[:80])
            if len(parts) >= limit:
                break
    if len(parts) < limit:
        for number in root.findChildren(QAbstractSpinBox):
            if not number.isVisible() or not isinstance(number, (QSpinBox, QDoubleSpinBox)):
                continue
            parts.append((_label_for(root, number) or "Sayisal alan") + ": " + number.text()[:40])
            if len(parts) >= limit:
                break
    return ". ".join(parts[:limit])


def read_active_field_for_view(view):
    model = view.model()
    index = view.currentIndex()
    if model is None or not index.isValid():
        return ""
    row = index.row()
    values = []
    for column in range(min(model.columnCount(), 8)):
        raw = str(model.data(model.index(row, column), Qt.ItemDataRole.DisplayRole) or "").strip()
        if raw:
            header = str(model.headerData(column, Qt.Orientation.Horizontal, Qt.ItemDataRole.DisplayRole) or "").strip()
            values.append((header + ": " if header else "") + raw)
    return ", ".join(values)
