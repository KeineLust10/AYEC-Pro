import streamlit as st
import pandas as pd
import sqlite3

ROOT = Path(__file__).resolve().parents[1]
DIALOG_DIR = ROOT / "src" / "ui" / "dialogs"
OUT_JSON = ROOT / "web_interface" / "static" / "dialogs.generated.json"

WIDGET_TYPES = {
    "QLineEdit": "text",
    "QTextEdit": "textarea",
    "QPlainTextEdit": "textarea",
    "QComboBox": "select",
    "QSpinBox": "number",
    "QDoubleSpinBox": "decimal",
    "QDateEdit": "date",
    "QTimeEdit": "time",
    "QDateTimeEdit": "datetime",
    "QCheckBox": "checkbox",
    "QRadioButton": "radio",
    "QTableWidget": "table",
    "QListWidget": "list",
    "QLabel": "label",
}

BUTTON_TYPES = {"QPushButton", "QToolButton"}
SIGNALS = {
    "clicked",
    "triggered",
    "currentTextChanged",
    "valueChanged",
    "textChanged",
    "stateChanged",
    "toggled",
    "accepted",
    "rejected",
}


def literal(node):
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.JoinedStr):
        parts = []
        for value in node.values:
            if isinstance(value, ast.Constant):
                parts.append(str(value.value))
            else:
                parts.append("{}")
        return "".join(parts)
    return None


def call_name(node):
    if isinstance(node, ast.Call):
        return call_name(node.func)
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return ""


def target_name(node):
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        base = target_name(node.value)
        return f"{base}.{node.attr}" if base else node.attr
    if isinstance(node, ast.Subscript):
        return target_name(node.value)
    if isinstance(node, ast.Tuple):
        return ", ".join(target_name(elt) for elt in node.elts)
    return ""


def callback_name(node):
    if isinstance(node, ast.Lambda):
        return ast.unparse(node) if hasattr(ast, "unparse") else "lambda"
    if isinstance(node, ast.Attribute):
        return target_name(node)
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Call):
        return call_name(node)
    return ast.unparse(node) if hasattr(ast, "unparse") else type(node).__name__


def clean_label(value, fallback=""):
    if value is None:
        return fallback
    text = str(value).strip()
    text = re.sub(r"\s+", " ", text)
    return text or fallback


class DialogVisitor(ast.NodeVisitor):
    def __init__(self, source_path):
        self.source_path = source_path
        self.classes = []
        self.buttons = []
        self.fields = []
        self.connections = []
        self.titles = []
        self._assignments = {}

    def visit_ClassDef(self, node):
        bases = [call_name(base) for base in node.bases]
        self.classes.append({"name": node.name, "bases": bases, "line": node.lineno})
        self.generic_visit(node)

    def visit_Call(self, node):
        name = call_name(node)
        if name == "setWindowTitle" and node.args:
            self.titles.append({"text": clean_label(literal(node.args[0])), "line": node.lineno})
        self._capture_connection(node)
        self.generic_visit(node)

    def visit_Assign(self, node):
        value = node.value
        if isinstance(value, ast.Call):
            ctor = call_name(value)
            for target in node.targets:
                name = target_name(target)
                self._assignments[name] = {"type": ctor, "line": node.lineno}
                if ctor in BUTTON_TYPES:
                    label = clean_label(literal(value.args[0]) if value.args else None, name)
                    self.buttons.append({"name": name, "label": label, "widget": ctor, "line": node.lineno})
                elif ctor in WIDGET_TYPES:
                    label = self._label_from_name(name)
                    default = literal(value.args[0]) if value.args else None
                    self.fields.append({
                        "name": name,
                        "label": label,
                        "widget": ctor,
                        "kind": WIDGET_TYPES[ctor],
                        "default": default,
                        "line": node.lineno,
                    })
        self.generic_visit(node)

    def visit_AnnAssign(self, node):
        if isinstance(node.value, ast.Call):
            ctor = call_name(node.value)
            name = target_name(node.target)
            self._assignments[name] = {"type": ctor, "line": node.lineno}
        self.generic_visit(node)

    def _capture_connection(self, node):
        func = node.func
        if not isinstance(func, ast.Attribute) or func.attr != "connect":
            return
        signal_node = func.value
        if not isinstance(signal_node, ast.Attribute) or signal_node.attr not in SIGNALS:
            return
        owner = target_name(signal_node.value)
        cb = callback_name(node.args[0]) if node.args else ""
        self.connections.append({
            "owner": owner,
            "signal": signal_node.attr,
            "callback": cb,
            "line": node.lineno,
        })

    def _label_from_name(self, name):
        name = name.split(".")[-1]
        name = re.sub(r"^(self_?|inp_|txt_|cmb_|combo_|spin_|date_|chk_|rb_|btn_)", "", name)
        return name.replace("_", " ").strip().title() or name


def merge_button_connections(buttons, connections):
    by_name = {button["name"]: button for button in buttons}
    for button in buttons:
        button["connections"] = []
    for conn in connections:
        if conn["signal"] != "clicked":
            continue
        owner = conn["owner"]
        if owner in by_name:
            by_name[owner]["connections"].append(conn)
            continue
        owner_tail = owner.split(".")[-1]
        for name, button in by_name.items():
            if name.split(".")[-1] == owner_tail:
                button["connections"].append(conn)
    return buttons


def parse_file(path):
    text = path.read_text(encoding="utf-8", errors="replace")
    try:
        tree = ast.parse(text, filename=str(path))
    except SyntaxError as exc:
        return {
            "file": str(path.relative_to(ROOT)).replace("\\", "/"),
            "key": path.stem,
            "error": str(exc),
            "classes": [],
            "title": path.stem.replace("_", " ").title(),
            "buttons": [],
            "fields": [],
            "connections": [],
            "counts": {"buttons": 0, "fields": 0, "connections": 0},
        }
    visitor = DialogVisitor(path)
    visitor.visit(tree)
    buttons = merge_button_connections(visitor.buttons, visitor.connections)
    title = next((item["text"] for item in visitor.titles if item["text"]), None)
    if not title:
        cls = next((c["name"] for c in visitor.classes if "Dialog" in c["name"]), None)
        title = cls or path.stem.replace("_", " ").title()
    return {
        "file": str(path.relative_to(ROOT)).replace("\\", "/"),
        "key": path.stem,
        "title": title,
        "classes": visitor.classes,
        "buttons": buttons,
        "fields": visitor.fields,
        "connections": visitor.connections,
        "counts": {
            "buttons": len(buttons),
            "fields": len(visitor.fields),
            "connections": len(visitor.connections),
        },
    }


def main():
    dialogs = [
        parse_file(path)
        for path in sorted(DIALOG_DIR.glob("*.py"))
        if path.name != "__init__.py"
    ]
    summary = {
        "source": str(DIALOG_DIR.relative_to(ROOT)).replace("\\", "/"),
        "generated_at": "static",
        "dialog_count": len(dialogs),
        "button_count": sum(d["counts"]["buttons"] for d in dialogs),
        "field_count": sum(d["counts"]["fields"] for d in dialogs),
        "connection_count": sum(d["counts"]["connections"] for d in dialogs),
    }
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(
        json.dumps({"summary": summary, "dialogs": dialogs}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()