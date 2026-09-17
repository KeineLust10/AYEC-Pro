# Lessons & Self-Improvement

## Rules & Patterns
_Add new rules here after corrections._

## Recurring Mistakes to Avoid
- **PyQt GC Crash**: Never pass an anonymous widget (e.g., `QLineEdit()`) to `registerField` in `QWizardPage` without assigning it to `self` or adding it to a layout first. Python GC will destroy it, causing a C++ segfault.
- **Dark/Light Mode Contrast**: Always explicitly set `color` when forcing `background-color`. Implicit text color inheritance often leads to white-on-white text in mixed theme environments.
- **QTreeWidget Checkboxes**: Standard QCheckBox styles don't apply to QTreeWidget items. You must style `QTreeWidget::indicator` pseudo-element separately, especially if overriding the base QTreeWidget style.
- **Refresh After Dialog**: When using `dialog.exec()`, always ensure you commit db changes and re-fetch data immediately after, as signals might be delayed or disconnected.
- **Editable QComboBox Click**: To make an editable `QComboBox` open popup on click (not just arrow), install an `eventFilter` on its `lineEdit()` to trap `MouseButtonPress`. Do not rely on overriding `mousePressEvent` instance method as it can get messy.
- **Database Wrapper Methods**: Do not assume helper methods like `execute_query` exist on the `Database` class unless verified. Use `self.db.cursor.execute()` for raw queries to be safe.
- **Schema Before Insert**: Ensure table creation and schema upgrades run before inserts that use extended columns.
- **Finance Detail Items Source**: When finansal satırlar için ürün kalemleri gösterilecekse, bunları sonradan tahmin etmeye çalışmak yerine satış anında açıklamaya satır satır yaz veya ayrı bir detay tablosuna kayıt et; dialog tarafında sadece bu veriyi oku.
- **Download Link Routing**: Hızlı bağlantı indirme linklerini eklerken, linklerin sunucuda gerçek bir route veya static mount ile servis edildiğini doğrula; kök path'e dosya koymak yetmez.
- **Cache Temizliği Kapsamı**: Kullanıcı aksiyonuna bağlı tetiklenen temizliği, istenen tek seferlik genel temizliğe dönüştürmeden ekleme.
