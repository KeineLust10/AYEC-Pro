import ast
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIALOG_DIR = ROOT.parent / "src" / "ui" / "dialogs"
OUT_JSON = ROOT / "web" / "dialogs.generated.json"
_UNRESOLVED = object()

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
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.USub, ast.UAdd)):
        value = literal(node.operand)
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return -value if isinstance(node.op, ast.USub) else value
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


def option_literal(node):
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.USub, ast.UAdd)):
        operand = node.operand
        if isinstance(operand, ast.Constant) and isinstance(operand.value, (int, float)) and not isinstance(operand.value, bool):
            return -operand.value if isinstance(node.op, ast.USub) else operand.value
    return None


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
        self._class_constants = {}

    def visit_ClassDef(self, node):
        bases = [call_name(base) for base in node.bases]
        self.classes.append({"name": node.name, "bases": bases, "line": node.lineno})
        previous_constants = self._class_constants
        self._class_constants = {}
        for statement in node.body:
            if isinstance(statement, ast.Assign):
                value = self._static_value(statement.value, {})
                if value is _UNRESOLVED:
                    continue
                for target in statement.targets:
                    if isinstance(target, ast.Name):
                        self._class_constants[target.id] = value
        self.generic_visit(node)
        self._class_constants = previous_constants

    def visit_Call(self, node):
        name = call_name(node)
        if name == "setWindowTitle" and node.args:
            self.titles.append({"text": clean_label(literal(node.args[0])), "line": node.lineno})
        self._capture_connection(node)
        self._capture_combo_options(node)
        self._capture_combo_editable(node)
        self._capture_placeholder(node)
        self._capture_radio_group(node)
        self.generic_visit(node)

    def visit_For(self, node):
        values = self._static_value(node.iter, {})
        targets = node.target.elts if isinstance(node.target, ast.Tuple) else [node.target]
        if isinstance(values, (list, tuple)):
            for value in values:
                parts = value if isinstance(value, (list, tuple)) else [value]
                environment = {
                    target.id: part
                    for target, part in zip(targets, parts)
                    if isinstance(target, ast.Name)
                }
                for statement in node.body:
                    for child in ast.walk(statement):
                        if isinstance(child, ast.Call):
                            self._capture_combo_options(child, environment)
        self.generic_visit(node)

    def _static_value(self, node, environment):
        if isinstance(node, ast.Constant):
            return node.value
        if isinstance(node, ast.Name):
            return environment.get(node.id, _UNRESOLVED)
        if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) and node.value.id == "self":
            return self._class_constants.get(node.attr, _UNRESOLVED)
        if isinstance(node, (ast.List, ast.Tuple)):
            values = [self._static_value(item, environment) for item in node.elts]
            if all(value is not _UNRESOLVED for value in values):
                return tuple(values) if isinstance(node, ast.Tuple) else values
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.USub, ast.UAdd)):
            value = self._static_value(node.operand, environment)
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                return -value if isinstance(node.op, ast.USub) else value
        return _UNRESOLVED

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

    def finalize_radio_groups(self):
        radio_groups = {}
        for field in self.fields:
            if field.get("group"):
                radio_groups.setdefault(field["group"], []).append(field)
        for fields in radio_groups.values():
            selected = next((field for field in fields if field.get("group_checked")), fields[0])
            for field in fields:
                field["group_checked"] = field is selected

    def _capture_radio_group(self, node):
        if call_name(node) != "addButton" or not isinstance(node.func, ast.Attribute) or not node.args:
            return
        group_name = target_name(node.func.value)
        if self._assignments.get(group_name, {}).get("type") != "QButtonGroup":
            return
        button_name = target_name(node.args[0])
        field = next((item for item in self.fields if item["name"] == button_name and item["kind"] == "radio"), None)
        if field is None:
            return
        field["group"] = group_name
        if len(node.args) > 1:
            group_value = self._static_value(node.args[1], {})
            if group_value is not _UNRESOLVED:
                field["group_value"] = group_value

    def _capture_placeholder(self, node):
        if call_name(node) != "setPlaceholderText" or not isinstance(node.func, ast.Attribute) or not node.args:
            return
        receiver = node.func.value
        if isinstance(receiver, ast.Call) and call_name(receiver) == "lineEdit" and isinstance(receiver.func, ast.Attribute):
            receiver = receiver.func.value
        owner = target_name(receiver)
        field = next((item for item in self.fields if item["name"] == owner), None)
        if field is None:
            return
        value = self._static_value(node.args[0], {})
        if isinstance(value, str):
            field["placeholder"] = value

    def _capture_combo_editable(self, node):
        if call_name(node) != "setEditable" or not isinstance(node.func, ast.Attribute) or not node.args:
            return
        owner = target_name(node.func.value)
        if self._assignments.get(owner, {}).get("type") != "QComboBox":
            return
        field = next((item for item in self.fields if item["name"] == owner), None)
        if field is None:
            return
        value = self._static_value(node.args[0], {})
        if isinstance(value, bool):
            field["editable"] = value

    def _capture_combo_options(self, node, environment=None):
        name = call_name(node)
        if name not in {"addItem", "addItems"} or not isinstance(node.func, ast.Attribute):
            return
        owner = target_name(node.func.value)
        assignment = self._assignments.get(owner, {})
        if assignment.get("type") != "QComboBox" or not node.args:
            return
        field = next((item for item in self.fields if item["name"] == owner), None)
        if field is None:
            return
        environment = environment or {}
        values = []
        if name == "addItems":
            items = self._static_value(node.args[0], environment)
            if isinstance(items, (list, tuple)):
                values = list(items)
        else:
            label = self._static_value(node.args[0], environment)
            if label is not _UNRESOLVED:
                value = self._static_value(node.args[1], environment) if len(node.args) > 1 else _UNRESOLVED
                values = [{"label": label, "value": value}] if value is not _UNRESOLVED else [label]
        if values:
            options = field.setdefault("options", [])
            for value in values:
                if value not in options:
                    options.append(value)

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
            "file": str(path.relative_to(ROOT.parent)).replace("\\", "/"),
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
    visitor.finalize_radio_groups()
    buttons = merge_button_connections(visitor.buttons, visitor.connections)
    title = next((item["text"] for item in visitor.titles if item["text"]), None)
    if not title:
        cls = next((c["name"] for c in visitor.classes if "Dialog" in c["name"]), None)
        title = cls or path.stem.replace("_", " ").title()
    return {
        "file": str(path.relative_to(ROOT.parent)).replace("\\", "/"),
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
        "source": str(DIALOG_DIR.relative_to(ROOT.parent)).replace("\\", "/"),
        "generated_at": "static",
        "dialog_count": len(dialogs),
        "button_count": sum(d["counts"]["buttons"] for d in dialogs),
        "field_count": sum(d["counts"]["fields"] for d in dialogs),
        "connection_count": sum(d["counts"]["connections"] for d in dialogs),
    }
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(
        json.dumps({"summary": summary, "dialogs": dialogs}, ensure_ascii=True, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()