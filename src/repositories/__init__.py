"""
Repository Pattern Implementation for AYEC Pro

This package contains repository classes that abstract database operations
for each domain entity. The Repository pattern provides:
- Separation of concerns between business logic and data access
- Testability through dependency injection
- Centralized query logic
- Transaction management via Unit of Work

Migration Status:
- [x] CustomerRepository - Complete
- [x] DeviceRepository - Complete
- [x] AccountingRepository - Complete
- [x] StockRepository - Complete
- [x] ServiceRepository - Complete
- [x] PersonnelRepository - Complete
"""

from .base_repository import BaseRepository, RepositoryError, RecordNotFoundError, DuplicateRecordError
from .unit_of_work import UnitOfWork, transaction
from .customer_repository import CustomerRepository
from .device_repository import DeviceRepository
from .accounting_repository import AccountingRepository
from .stock_repository import StockRepository
from .service_repository import ServiceRepository
from .personnel_repository import PersonnelRepository

__all__ = [
    'BaseRepository',
    'RepositoryError',
    'RecordNotFoundError',
    'DuplicateRecordError',
    'UnitOfWork',
    'transaction',
    'CustomerRepository',
    'DeviceRepository',
    'AccountingRepository',
    'StockRepository',
    'ServiceRepository',
    'PersonnelRepository',
]
