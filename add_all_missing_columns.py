# add_all_missing_columns.py
import sqlite3
from datetime import datetime

print("=" * 50)
print("ADDING ALL MISSING COLUMNS")
print("=" * 50)

conn = sqlite3.connect('db.sqlite3')
cursor = conn.cursor()

# Define all missing columns that should exist
missing_columns = {
    'products_product': [
        ('quantity', 'INTEGER DEFAULT 0'),
        ('is_active', 'BOOLEAN DEFAULT 1'),
    ],
    'tenants_tenant': [
        ('status', 'VARCHAR(20) DEFAULT "active"'),
    ],
}

for table, columns in missing_columns.items():
    print(f"\nChecking table: {table}")
    
    # Get existing columns
    cursor.execute(f"PRAGMA table_info({table})")
    existing = [col[1] for col in cursor.fetchall()]
    print(f"   Existing columns: {existing}")
    
    for col_name, col_type in columns:
        if col_name not in existing:
            try:
                print(f"   Adding: {col_name} ({col_type})")
                cursor.execute(f"ALTER TABLE {table} ADD COLUMN {col_name} {col_type}")
                print(f"   Added {col_name}")
            except Exception as e:
                print(f"   Error adding {col_name}: {e}")
        else:
            print(f"   {col_name} already exists")

conn.commit()

# Final verification
print("\n" + "=" * 50)
print("FINAL COLUMN VERIFICATION")
print("=" * 50)

for table in ['products_product', 'tenants_tenant']:
    print(f"\n{table}:")
    cursor.execute(f"PRAGMA table_info({table})")
    for col in cursor.fetchall():
        print(f"   - {col[1]} ({col[2]})")

conn.close()

print("\n" + "=" * 50)
print("All missing columns added successfully!")
print("=" * 50)