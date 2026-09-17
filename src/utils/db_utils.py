# -*- coding: utf-8 -*-

def sqlite_row_to_dict(row, description):
    """
    Converts a sqlite3.Row or a tuple to a dictionary using cursor description.
    
    Args:
        row: The row data from fetchone/fetchall.
        description: cursor.description containing column names.
        
    Returns:
        dict: A dictionary mapping column names to values.
    """
    if row is None:
        return {}
    
    # If it's already a dictionary-like object (some wrappers do this)
    if hasattr(row, 'keys') and callable(row.keys):
        return dict(row)
        
    # Standard sqlite3.Row or tuple
    return {description[i][0]: row[i] for i in range(len(description))}
