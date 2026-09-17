# AYEC Pro Development Tools

This directory contains utility scripts for development, debugging, database management, and maintenance.

## Directory Structure

```
tools/
├── database/       # Database maintenance, fixes, and migrations
├── debug/          # Debugging and diagnostic utilities
├── setup/          # Setup, generation, and initialization scripts
├── cleanup/        # Data cleanup and reset utilities
├── build/          # Build and compilation scripts
├── misc/           # Miscellaneous utilities
└── organize_scripts.py  # This organization script
```

## Usage

### Database Tools

Scripts for database maintenance, schema updates, and data fixes:

```bash
# Repair database
python tools/database/db_repair.py

# Check database integrity
python tools/database/check_db.py

# Audit database schema
python tools/database/audit_db.py

# Create currency tables
python tools/database/create_currency_tables.py

# Migration scripts
python tools/database/migrate_db_v2.py
python tools/database/migrate_users_table.py
```

### Debug Tools

Diagnostic and troubleshooting utilities:

```bash
# Debug database connections
python tools/debug/debug_db.py

# Find circular imports
python tools/debug/find_loops.py

# Find bad imports
python tools/debug/find_bad_imports.py

# Debug startup issues
python tools/debug/debug_startup.py

# List database tables
python tools/debug/list_tables.py

# Run diagnostics
python tools/debug/diag_db.py
```

### Setup Tools

Scripts for initial setup and data generation:

```bash
# Generate app icon
python tools/setup/generate_app_icon.py

# Generate mock data for testing
python tools/setup/generate_mock_data.py

# Generate full year test data
python tools/setup/generate_full_year_data.py

# Create license key
python tools/setup/keygen.py

# Setup fresh data
python tools/setup/setup_fresh_data.py
```

### Cleanup Tools

**WARNING**: These scripts can delete data. Use with caution!

```bash
# Force cleanup (removes corrupted data)
python tools/cleanup/ForceCleanup.py

# Nuclear reset (complete database reset)
python tools/cleanup/nuclear_reset.py

# Total wipe (removes all user data)
python tools/cleanup/total_wipe.py

# Final restore
python tools/cleanup/final_restore.py
```

### Build Tools

```bash
# Convert icon formats
python tools/build/convert_icon.py
```

## Important Notes

1. **Always backup** before running database or cleanup scripts
2. Most scripts require the virtual environment to be activated
3. Run from the project root directory
4. Some scripts may require administrator privileges

## Common Workflows

### Database Maintenance
```bash
# 1. Check database integrity
python tools/debug/debug_db.py

# 2. Repair if needed
python tools/database/db_repair.py

# 3. Audit schema
python tools/database/audit_db.py

# 4. Verify fix
python tools/database/verify_fix.py
```

### Fresh Setup
```bash
# 1. Clean existing data (optional)
python tools/cleanup/total_wipe.py

# 2. Initialize schema
python tools/database/init_db_schema.py

# 3. Generate test data
python tools/setup/generate_mock_data.py

# 4. Verify setup
python tools/database/verify_db.py
```

### Troubleshooting
```bash
# Check for issues
python tools/debug/run_full_diagnostics.py

# Find problematic imports
python tools/debug/find_bad_imports.py

# Debug startup
python tools/debug/debug_startup.py
```

## Adding New Scripts

When adding new utility scripts:

1. Place in the appropriate subdirectory
2. Add documentation to this README
3. Follow naming convention: `<action>_<target>.py`
4. Include docstrings with usage examples
5. Add error handling and logging
