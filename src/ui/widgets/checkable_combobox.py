
from PyQt6.QtWidgets import QComboBox, QStyledItemDelegate
from PyQt6.QtGui import QStandardItem, QPalette, QFontMetrics, QAction, QFont
from PyQt6.QtCore import Qt, QEvent

class CheckableComboBox(QComboBox):
    def __init__(self, parent=None):
        super(CheckableComboBox, self).__init__(parent)
        self.setEditable(True)
        self.lineEdit().setReadOnly(True)
        self.closeOnLineEditClick = False
        
        # Use StandardItemModel for checkable items
        from PyQt6.QtGui import QStandardItemModel
        self.setModel(QStandardItemModel(self))
        
        # Install event filter on view to catch clicks
        self.view().viewport().installEventFilter(self)
        self.lineEdit().installEventFilter(self)
        self.view().setAlternatingRowColors(True)

    def addItem(self, text, data=None):
        item = QStandardItem(text)
        item.setData(data)
        item.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
        item.setData(Qt.CheckState.Unchecked, Qt.ItemDataRole.CheckStateRole)
        self.model().appendRow(item)

    def eventFilter(self, widget, event):
        if widget == self.lineEdit():
             if event.type() == QEvent.Type.MouseButtonRelease:
                self.showPopup()
                return True
        elif widget == self.view().viewport():
             if event.type() == QEvent.Type.MouseButtonRelease:
                idx = self.view().indexAt(event.pos())
                if idx.isValid(): # Check strict validity
                    item = self.model().item(idx.row())
                    
                    if item.checkState() == Qt.CheckState.Checked:
                        item.setCheckState(Qt.CheckState.Unchecked)
                    else:
                        item.setCheckState(Qt.CheckState.Checked)
                    
                    self.updateText()
                    return True
        return super().eventFilter(widget, event)

    def showPopup(self):
        super().showPopup()
    
    def hidePopup(self):
        super().hidePopup()

    def updateText(self):
        items = []
        for i in range(self.model().rowCount()):
            if self.model().item(i).checkState() == Qt.CheckState.Checked:
                items.append(self.model().item(i).text())
        self.lineEdit().setText(", ".join(items))
        # Trigger signal that text changed if needed, or custom signal

    def getCheckedItems(self):
        items = []
        for i in range(self.model().rowCount()):
            item = self.model().item(i)
            if item.checkState() == Qt.CheckState.Checked:
                items.append((item.text(), item.data()))
        return items

    def clearChecks(self):
        """Keep items, clear only checked state and display text."""
        for i in range(self.model().rowCount()):
            item = self.model().item(i)
            if item.checkState() == Qt.CheckState.Checked:
                item.setCheckState(Qt.CheckState.Unchecked)
        self.lineEdit().clear()

    def clear(self):
        super().clear()
        self.lineEdit().clear()

