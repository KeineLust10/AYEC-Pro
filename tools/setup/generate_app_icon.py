import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QPainter, QColor, QLinearGradient, QRadialGradient, QBrush, QPen, QPainterPath, QPixmap
from PyQt6.QtCore import Qt, QPointF, QRectF

def generate_icon():
    app = QApplication(sys.argv)
    
    # Create a high-res pixmap
    size = 512
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)
    
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    
    # --- Background Glow ---
    center = QPointF(size/2, size/2)
    glow = QRadialGradient(center, size/2)
    glow.setColorAt(0, QColor(52, 152, 219, 40)) # Soft blue
    glow.setColorAt(1, Qt.transparent)
    painter.setBrush(QBrush(glow))
    painter.setPen(Qt.NoPen)
    painter.drawRect(0, 0, size, size)
    
    # --- Cloud Shape ---
    path = QPainterPath()
    # Drawing a stylized modern cloud
    # Base rectangles/circles
    path.addRoundedRect(QRectF(size*0.2, size*0.45, size*0.6, size*0.3), 40, 40)
    path.addEllipse(QRectF(size*0.3, size*0.3, size*0.25, size*0.25))
    path.addEllipse(QRectF(size*0.45, size*0.2, size*0.35, size*0.35))
    
    # Gradient for cloud
    grad = QLinearGradient(0, size*0.2, 0, size*0.75)
    grad.setColorAt(0, QColor(52, 152, 219))  # Light Blue
    grad.setColorAt(1, QColor(41, 128, 185))  # Deep Blue
    
    painter.setBrush(QBrush(grad))
    painter.setPen(Qt.NoPen)
    painter.drawPath(path)
    
    # --- Inner Glow/Reflection ---
    inner_path = QPainterPath()
    inner_path.addEllipse(QRectF(size*0.48, size*0.25, size*0.3, size*0.1))
    painter.setBrush(QBrush(QColor(255, 255, 255, 60)))
    painter.drawPath(inner_path)
    
    # --- Center Symbol (Integrated Gear/Bulut Pulse) ---
    symbol_center = QPointF(size*0.5, size*0.5)
    
    # Outer Ring
    painter.setBrush(Qt.NoBrush)
    pen = QPen(QColor(241, 196, 15, 200)) # gold
    pen.setWidth(12)
    painter.setPen(pen)
    painter.drawEllipse(symbol_center, size*0.12, size*0.12)
    
    # Inner Cross/Bolt
    pen.setWidth(8)
    pen.setCapStyle(Qt.RoundCap)
    painter.setPen(pen)
    painter.drawLine(QPointF(size*0.45, size*0.5), QPointF(size*0.55, size*0.5))
    painter.drawLine(QPointF(size*0.5, size*0.45), QPointF(size*0.5, size*0.55))
    
    painter.end()
    
    # Ensure directory exists
    import os
    if not os.path.exists('assets'):
        os.makedirs('assets')
        
    pixmap.save("assets/app_icon.png")
    
    # Try to convert to ICO for Windows EXE using PIL
    try:
        from PIL import Image
        img = Image.open("assets/app_icon.png")
        img.save("assets/app_icon.ico", format='ICO', sizes=[(16,16), (32,32), (48,48), (64,64), (128,128), (256,256)])
        print("ICO generated successfully: assets/app_icon.ico")
    except Exception as e:
        print(f"ICO generation failed: {e}")
        
    print("Icon generated successfully: assets/app_icon.png")

if __name__ == "__main__":
    generate_icon()
