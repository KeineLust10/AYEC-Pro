# AYEC Pro Architecture Documentation

## System Overview

AYEC Pro is a desktop ERP application built with Python, featuring a PyQt6 frontend and optional FastAPI backend for web services.

```
┌─────────────────────────────────────────────────────────────┐
│                      User Interface                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │  PyQt6 GUI  │  │  Web View   │  │  Notification System│  │
│  │  (Desktop)  │  │  (Embedded) │  │  (Toast/SMS/Email)  │  │
│  └──────┬──────┘  └──────┬──────┘  └──────────┬──────────┘  │
└─────────┼────────────────┼────────────────────┼─────────────┘
          │                │                    │
          └────────────────┴────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                   Application Layer                         │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              Business Logic (Services)              │   │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌─────────┐ │   │
│  │  │  Device  │ │ Customer │ │  Finance │ │  Stock  │ │   │
│  │  │ Service  │ │   CRM    │ │Accounting│ │  Mgmt   │ │   │
│  │  └──────────┘ └──────────┘ └──────────┘ └─────────┘ │   │
│  └────────────────────────┬────────────────────────────┘   │
└───────────────────────────┼─────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────┐
│                    Data Access Layer                        │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                  Database Class                     │   │
│  │         (Mixins: Settings, Customer, etc.)          │   │
│  └────────────────────────┬────────────────────────────┘   │
│                           │                                  │
│  ┌────────────────────────▼────────────────────────────┐   │
│  │                 SQLite Database                     │   │
│  │          (Local file: ayecpro.db)                   │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
          │
          │  Web API Layer (Optional)
          ▼
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI Backend                          │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────────────┐  │
│  │  Auth    │ │Customers │ │ Services │ │   Dashboard    │  │
│  │ Router   │ │ Router   │ │  Router  │ │    Router      │  │
│  └──────────┘ └──────────┘ └──────────┘ └────────────────┘  │
│                    JWT Authentication                        │
└─────────────────────────────────────────────────────────────┘
```

## Layer Details

### 1. Presentation Layer

#### PyQt6 Desktop UI
- **Location**: `src/ui/`
- **Components**:
  - `widgets/` - Reusable UI components
  - `pages/` - Main application pages
  - `dialogs/` - Modal dialogs and popups
  - `modern_login_window.py` - Authentication UI
  - `main_window.py` - Primary application window

#### Key UI Features
- Custom theme engine with light/dark modes
- Toast notification system
- Kanban board for service tracking
- PDF preview and generation
- Pattern lock for security

### 2. Business Logic Layer

#### Services
- **Location**: `src/services/`
- Encapsulates business rules and workflows
- Coordinates between UI and database
- Handles complex operations (e.g., service workflow)

#### Managers
- **Location**: `src/utils/`
- Singleton pattern for cross-cutting concerns
- Examples:
  - `auth_manager.py` - Authentication state
  - `theme_manager.py` - UI theming
  - `finance_manager.py` - Financial calculations
  - `license_manager.py` - License validation

### 3. Data Access Layer

#### Database Architecture (Current)

**Issue**: The current implementation uses multiple inheritance with 26+ mixins:

```python
class Database(
    SettingsMixin, BankMixin, RemindersMixin, 
    # ... 20+ more mixins
):
    pass
```

**Problems**:
- Tight coupling between domains
- Difficult to test (large inheritance chain)
- No clear separation of concerns
- Methods scattered across many files

#### Planned Refactor: Repository Pattern

```
src/
└── repositories/
    ├── base_repository.py      # Abstract base
    ├── customer_repository.py  # Customer operations
    ├── device_repository.py    # Device/service operations
    ├── finance_repository.py   # Accounting operations
    ├── stock_repository.py     # Inventory operations
    └── unit_of_work.py         # Transaction management
```

**Benefits**:
- Clear separation of concerns
- Easier unit testing with mocking
- Transaction management
- Reduced coupling

#### Database Schema

**Location**: `src/db/schema.py`

Key tables:
- `devices` - Service/repair tracking
- `customers` - Customer CRM data
- `accounting` - Financial transactions
- `parts` - Inventory/stock management
- `personnel` - Employee records
- `users` - Authentication
- `settings` - Application configuration

### 4. External Integrations

#### Telegram Bot
- **Location**: `src/bot/`
- Mobile notifications and approvals
- Real-time status updates

#### E-Invoice
- **Location**: `src/api/einvoice_client.py`
- Turkish Revenue Administration integration
- XML generation and submission

#### AI Services
- **Location**: `src/ai/`
- Financial intelligence and predictions
- Natural language processing

## Data Flow Examples

### Service Creation Flow

```
User Input (UI)
    ↓
ServiceWizard validates data
    ↓
Service.create() business logic
    ↓
Database.insert_device() + insert_service()
    ↓
Commit transaction
    ↓
Send notifications (Telegram, Email)
    ↓
Update UI with success
```

### Financial Transaction Flow

```
User creates transaction
    ↓
FinanceManager.validate()
    ↓
Calculate currency conversion
    ↓
Database.insert_accounting()
    ↓
Update customer balance
    ↓
Generate PDF receipt
    ↓
Log audit trail
```

## Key Design Patterns

### 1. Singleton Pattern
Used for managers that should have global state:
- `AuthManager` - Current user session
- `ThemeManager` - Active theme
- `Database` - Single database connection

### 2. Mixin Pattern (Current)
Database operations grouped by domain:
- Each mixin handles one domain
- Combined into Database class
- **Being refactored** to Repository pattern

### 3. Observer Pattern
- Toast notification system
- Theme change events
- Settings updates

### 4. Factory Pattern
- PDF generator factory
- Dialog factory for different types
- Widget factory for dynamic UI

### 5. Strategy Pattern
- Payment method strategies
- Export format strategies (PDF, Excel)
- Notification channels (Email, SMS, Telegram)

## Security Architecture

### Authentication Flow
```
Login Request
    ↓
Password + Salt → bcrypt hash
    ↓
Compare with stored hash
    ↓
Generate JWT token
    ↓
Store in secure httpOnly cookie
```

### Authorization
- Role-based access control (RBAC)
- Permission groups for features
- Row-level security for multi-tenant data

### Data Protection
- SQLite database encrypted at rest (planned)
- Sensitive fields encrypted in database
- Passwords never stored in plain text

## Performance Considerations

### Current Optimizations
- Database indexes on frequently queried columns
- Lazy loading for large datasets
- Image caching for UI assets

### Planned Improvements
- Connection pooling for database
- Query result caching
- Async operations for I/O
- Pagination for large tables

## Testing Strategy

### Unit Tests
- Repository methods (after refactor)
- Service business logic
- Utility functions

### Integration Tests
- Database operations
- API endpoints
- External service integrations

### UI Tests
- PyQt6 Test framework
- Screenshot comparison
- User workflow automation

## Migration Strategy

### From Current to Repository Pattern

1. **Phase 1**: Create repository interfaces
2. **Phase 2**: Implement repositories alongside mixins
3. **Phase 3**: Migrate one domain at a time
4. **Phase 4**: Remove mixins once all migrated
5. **Phase 5**: Add Alembic migrations

### Database Migrations

**Current**: Ad-hoc schema updates in `_initialize_full_schema()`

**Planned**: Alembic migration system
```
alembic/
├── versions/
│   ├── 001_initial_schema.py
│   ├── 002_add_currency_support.py
│   └── 003_add_project_management.py
└── env.py
```

## Technology Decisions

### Why PyQt6?
- Native desktop performance
- Rich widget ecosystem
- Excellent Windows integration
- PDF generation support

### Why SQLite?
- Zero configuration
- Single-file database
- Good performance for single-user app
- Easy backup/restore

### Why FastAPI?
- Modern Python async framework
- Automatic API documentation
- Type validation with Pydantic
- Easy integration with PyQt6

### Future Considerations
- PostgreSQL for multi-user deployments
- Redis for caching layer
- Docker for deployment
- Electron for web-based UI option
