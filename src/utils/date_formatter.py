# -*- coding: utf-8 -*-

"""
Date Formatter Utility
Provides centralized date formatting based on user settings.
"""

from datetime import datetime
from src.utils.logger import logger

def format_date(dt, db, include_time=False):
    """
    Formats a date or datetime object/string according to the 'date_format' setting in the database.
    
    Args:
        dt: datetime, date object or string (YYYY-MM-DD or YYYY-MM-DD HH:MM:SS)
        db: Database instance to fetch settings
        include_time: Whether to include HH:MM if available
        
    Returns:
        Formatted date string
    """
    if not dt:
        return "—"
        
    # Convert string to datetime if necessary
    if isinstance(dt, str):
        try:
            if ' ' in dt:
                dt = datetime.strptime(dt, "%Y-%m-%d %H:%M:%S")
            else:
                dt = datetime.strptime(dt, "%Y-%m-%d")
        except Exception:
            try:
                # Try fallback for Turkish format if stored that way
                dt = datetime.strptime(dt, "%d.%m.%Y")
            except Exception:
                return dt # Return as is if all fails

    try:
        # Fetch setting
        # Default: GG.AA.YYYY (31.12.2025)
        raw_fmt = db.get_setting('date_format', 'GG.AA.YYYY (31.12.2025)')
        
        # Mapping setting to strftime format
        if "AA/GG/YYYY" in raw_fmt:
            fmt = "%m/%d/%Y"
        elif "YYYY-AA-GG" in raw_fmt:
            fmt = "%Y-%m-%d"
        elif "Uzun Tarih" in raw_fmt or "Mart" in raw_fmt:
            # Long format (e.g., 5 Mart 2026)
            # We need to handle Turkish month names manually or use locale
            # Using locale might be tricky across OS, so let's do a manual map for reliability
            months = {
                1: "Ocak", 2: "Şubat", 3: "Mart", 4: "Nisan", 5: "Mayıs", 6: "Haziran",
                7: "Temmuz", 8: "Ağustos", 9: "Eylül", 10: "Ekim", 11: "Kasım", 12: "Aralık"
            }
            date_str = f"{dt.day} {months.get(dt.month)} {dt.year}"
            if include_time:
                date_str += f" {dt.strftime('%H:%M')}"
            return date_str
        else:
            # Default: GG.AA.YYYY
            fmt = "%d.%m.%Y"
            
        res = dt.strftime(fmt)
        if include_time:
            res += f" {dt.strftime('%H:%M')}"
        return res
        
    except Exception as e:
        logger.error(f"Date formatting error: {e}")
        return dt.strftime("%d.%m.%Y") # Fallback
