import sys
from PyQt6.QtWidgets import QApplication
from src.ui.widgets.animated_toggle import AnimatedToggle

app = QApplication(sys.argv)
app.setStyleSheet("QCheckBox { color: red; }")
try:
    toggle = AnimatedToggle()
    toggle.show()
    app.processEvents()
    
    # Save a screenshot to see if it's drawn
    pixmap = toggle.grab()
    pixmap.save("toggle_preview.png")
    
    # Is it empty? (mostly transparent/background)
    image = pixmap.toImage()
    colors = set()
    for x in range(image.width()):
        for y in range(image.height()):
            colors.add(image.pixelColor(x, y).name())
    
    print(f"Colors in painted widget: {colors}")
except Exception as e:
    import traceback
    traceback.print_exc()
