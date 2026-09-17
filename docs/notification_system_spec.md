# Context Preparation for Claude
# Purpose: Implement Central Notification System

## 1. Database Schema Changes (`src/db/mixins/notification_mixin.py`)
Create a new file `src/db/mixins/notification_mixin.py` and add it to `Database` class in `src/database.py`.

### Table: `notifications`
```sql
CREATE TABLE IF NOT EXISTS notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category TEXT, -- 'Finance', 'Stock', 'Technical', 'System'
    title TEXT,
    content TEXT,
    link_id TEXT, -- formatted link e.g. "stock:123", "loan:45", "customer:99"
    status TEXT DEFAULT 'unread', -- 'unread', 'read', 'archived'
    priority TEXT DEFAULT 'normal', -- 'normal', 'high', 'critical'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    read_at TIMESTAMP
);
```

### Methods needed in `NotificationMixin`:
- `add_notification(category, title, content, link_id, priority='normal')`
- `get_notifications(status='unread', limit=50)`: Returns items ordered by priority (critical first) then date.
- `get_notification_history(search_query='', limit=100)`: For the History tab.
- `mark_notification_read(id)`
- `archive_notification(id)`
- `get_unread_count()`: For the bell badge.

## 2. UI Components (`src/ui/components/notification_center.py`)
Create a new file `src/ui/components/notification_center.py` implementing:

### Classes:
1.  **`NotificationBell(QWidget)`**:
    -   Icon: Bell.
    -   Badge: Red circle with white number (hidden if 0).
    -   Signal: `clicked()`.
    -   Method: `update_badge(count)`.

2.  **`NotificationPanel(QFrame)`** (The Dropdown):
    -   Style: Floating shadow panel (setWindowFlags(Qt.Popup) or similar overlay logic).
    -   Layout:
        -   **Header**: Title and "Mark All Read" button.
        -   **Tabs**: QTabWidget ("Aktif", "Geçmiş").
        -   **Content**:
            -   *Tab 1 (Active)*: QScrollArea VList of `NotificationCard`.
            -   *Tab 2 (History)*: Search Bar + QScrollArea.
    -   **`NotificationCard(QFrame)`**:
        -   Left Border Color: Red (Finance), Orange (Stock), Blue (Tech), Gray (System).
        -   Icon: Corresponding to category.
        -   Title (Bold) & Content (Wrap).
        -   Action Button: "Hızlı Git" (Parses `link_id` and emits signal to open relevant page).

## 3. Integration Logic
### `ModernDesktopApp.py`:
-   **Startup Check**:
    -   In `__init__` or `delayed_init`:
        -   Call `db.check_critical_stock()` -> Generate 'Stock' notifications.
        -   Call `db.get_overdue_installments()` -> Generate 'Finance' notifications.
        -   **Popup**: If critical alerts exist, show `CriticalAlertPopup` (new dialog).
-   **Header Integration**:
    -   Add `self.notification_bell` to `top_header` layout.
    -   Connect bell click to `self.notification_panel.show_at(pos)`.
-   **Timer**:
    -   Every 5-10 mins, re-run checks (background thread or simple timer) to update badge.

## 4. Specific Category Colors & Icons
-   **Finance**: Color `#EF4444` (Red), Icon: `fa5-credit-card` or similar.
-   **Stock**: Color `#F59E0B` (Orange), Icon: `fa5-box-open`.
-   **Technical**: Color `#3B82F6` (Blue), Icon: `fa5-wrench`.
-   **System**: Color `#6B7280` (Gray), Icon: `fa5-server`.

## 5. Critical Alert Popup
Create `src/ui/dialogs/critical_alert_dialog.py`:
-   Shown ONLY if there are 'critical' unread notifications on login.
-   Simple clean list of "Acil Durumlar".
-   "Tamam, Anlaşıldı" button to close.
