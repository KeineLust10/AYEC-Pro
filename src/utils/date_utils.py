# -*- coding: utf-8 -*-

"""
Turkish Date Utilities
Helper functions for Turkish date formatting.
"""
from datetime import datetime

TURKISH_MONTHS = {
    1: "Ocak",
    2: "Şubat",
    3: "Mart",
    4: "Nisan",
    5: "Mayıs",
    6: "Haziran",
    7: "Temmuz",
    8: "Ağustos",
    9: "Eylül",
    10: "Ekim",
    11: "Kasım",
    12: "Aralık"
}

TURKISH_DAYS = {
    0: "Pazartesi",
    1: "Salı",
    2: "Çarşamba",
    3: "Perşembe",
    4: "Cuma",
    5: "Cumartesi",
    6: "Pazar"
}

def format_turkish_date(date_obj, format_type="full"):
    """
    Format date in Turkish.
    
    Args:
        date_obj: datetime object or string (YYYY-MM-DD)
        format_type: "full", "short", "month_year"
        
    Returns:
        Formatted Turkish date string
    """
    if isinstance(date_obj, str):
        raw = date_obj.strip()
        if " " in raw:
            raw = raw.split(" ")[0]
        date_obj = datetime.strptime(raw, "%Y-%m-%d")
    
    day = date_obj.day
    month = TURKISH_MONTHS[date_obj.month]
    year = date_obj.year
    
    if format_type == "full":
        return f"{day} {month} {year}"
    elif format_type == "short":
        return f"{day:02d}.{date_obj.month:02d}.{year}"
    elif format_type == "month_year":
        return f"{month} {year}"
    else:
        return f"{day} {month} {year}"

def get_turkish_month_name(month_number):
    """Get Turkish month name from number (1-12)."""
    return TURKISH_MONTHS.get(month_number, "")

def get_turkish_day_name(day_number):
    """Get Turkish day name from number (0=Monday, 6=Sunday)."""
    return TURKISH_DAYS.get(day_number, "")

def format_datetime_turkish(dt_obj):
    """Format datetime with Turkish month."""
    if isinstance(dt_obj, str):
        dt_obj = datetime.strptime(dt_obj, "%Y-%m-%d %H:%M:%S")
    
    day = dt_obj.day
    month = TURKISH_MONTHS[dt_obj.month]
    year = dt_obj.year
    time = dt_obj.strftime("%H:%M")
    
    return f"{day} {month} {year} {time}"
