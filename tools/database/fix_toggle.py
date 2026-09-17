with open("src/ui/widgets/animated_toggle.py", "r", encoding="utf-8") as f:
    text = f.read()

target = "self.setCursor(Qt.CursorShape.PointingHandCursor)"
repl = target + "\n        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)\n        self.setStyleSheet('AnimatedToggle { background: transparent; border: none; } AnimatedToggle::indicator { width: 0; height: 0; border: none; background: transparent; }')"

if target in text:
    if "WA_StyledBackground" not in text:
        text = text.replace(target, repl)
        with open("src/ui/widgets/animated_toggle.py", "w", encoding="utf-8") as f:
            f.write(text)
        print("SUCCESS")
    else:
        print("ALREADY APPLIED")
else:
    print("NOT FOUND")
