# -*- coding: utf-8 -*-

from src.ui.dialogs.customer_360_dialog import Customer360Dialog


class AutomotiveCustomer360Dialog(Customer360Dialog):
    """Otomotiv sektoru icin ayri giris sinifi."""

    def __init__(self, db, customer_id, customer_name, parent=None, sector_manager=None):
        super().__init__(
            db,
            customer_id,
            customer_name,
            parent=parent,
            sector_manager=sector_manager,
            sector_override="otomotiv",
        )
