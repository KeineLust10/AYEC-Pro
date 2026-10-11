"""Read-only exports of recorded audit events, without invented telemetry."""

import csv

from PyQt6.QtGui import QFont, QPdfWriter, QTextDocument
from PyQt6.QtWidgets import QApplication


AUDIT_EXPORT_COLUMNS = ("ID", "User", "Table", "Action", "Details", "Timestamp")


def export_audit_csv(path, records):
    def safe_cell(value):
        text = str(value if value is not None else "")
        return "'" + text if text.startswith(("=", "+", "-", "@", "\t", "\r")) else text

    with open(path, "w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(AUDIT_EXPORT_COLUMNS)
        writer.writerows([safe_cell(value) for value in record] for record in records)


def audit_event_text(record):
    return "AYEC Pro - Kayitli Audit Olayi\n\n" + "\n\n".join(
        f"{title}: {value if value is not None else ''}"
        for title, value in zip(AUDIT_EXPORT_COLUMNS, record)
    ) + "\n\nBu rapor kayitli verileri icerir. Kriptografik dogrulama iddiasi tasimaz."


def export_audit_event_pdf(path, record):
    writer = QPdfWriter(str(path))
    writer.setTitle("AYEC Pro - Audit Olay Raporu")
    writer.setCreator("AYEC Pro")
    writer.setResolution(96)
    document = QTextDocument()
    document.setDefaultFont(QFont(QApplication.font().family(), 10))
    document.setPlainText(audit_event_text(record))
    document.print(writer)
    del writer
