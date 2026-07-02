# fix_reserved_keyword_columns.py
import sqlite3

print("=" * 60)
print("FIXING RESERVED KEYWORD COLUMNS")
print("=" * 60)

conn = sqlite3.connect('db.sqlite3')
cursor = conn.cursor()

# Fix the "order" columns (reserved keyword)
fixes = [
    ('orders_orderitem', 'order'),
    ('payment_payment', 'order'),
    ('payment_payout', 'order'),
]

for table, column in fixes:
    try:
        # Check if column exists
        cursor.execute(f"PRAGMA table_info({table})")
        existing = [col[1] for col in cursor.fetchall()]
        
        if column not in existing:
            print(f"Adding: {table}.{column} (INTEGER)")
            # Use double quotes to escape the reserved keyword
            cursor.execute(f'ALTER TABLE {table} ADD COLUMN "{column}" INTEGER')
            print(f"  ✅ Added {table}.{column}")
        else:
            print(f"  {table}.{column} already exists")
    except Exception as e:
        print(f"  ❌ Error: {e}")

conn.commit()

# Verify
print("\n" + "=" * 60)
print("VERIFICATION")
print("=" * 60)

for table, column in fixes:
    cursor.execute(f"PRAGMA table_info({table})")
    columns = [col[1] for col in cursor.fetchall()]
    if column in columns:
        print(f"✅ {table}.{column} exists")
    else:
        print(f"❌ {table}.{column} still missing")

conn.close()

print("\n" + "=" * 60)
print("Done!")
print("=" * 60)