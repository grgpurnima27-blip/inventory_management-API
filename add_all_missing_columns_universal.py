# add_all_missing_columns_universal.py
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.db import connection
from django.apps import apps
from django.db import models

print("=" * 70)
print("UNIVERSAL MISSING COLUMN CHECKER AND FIXER")
print("=" * 70)

# Track what we find
tables_checked = 0
columns_added = 0
issues_found = []

for model in apps.get_models():
    table_name = model._meta.db_table
    tables_checked += 1
    
    print(f"\nChecking: {table_name}")
    
    # Get model fields with their types and defaults
    model_fields = {}
    for field in model._meta.get_fields():
        if field.name != 'id' and not field.auto_created:
            # Determine SQLite data type
            field_type = 'VARCHAR(255)'
            default_value = None
            
            if isinstance(field, models.CharField):
                max_length = getattr(field, 'max_length', 255)
                field_type = f'VARCHAR({max_length})'
            elif isinstance(field, models.TextField):
                field_type = 'TEXT'
            elif isinstance(field, models.IntegerField):
                field_type = 'INTEGER'
                default_value = getattr(field, 'default', 0)
            elif isinstance(field, models.PositiveIntegerField):
                field_type = 'INTEGER'
                default_value = getattr(field, 'default', 0)
            elif isinstance(field, models.DecimalField):
                max_digits = getattr(field, 'max_digits', 10)
                decimal_places = getattr(field, 'decimal_places', 2)
                field_type = f'DECIMAL({max_digits},{decimal_places})'
                default_value = getattr(field, 'default', 0)
            elif isinstance(field, models.BooleanField):
                field_type = 'BOOLEAN'
                default_value = getattr(field, 'default', 0)
            elif isinstance(field, models.DateTimeField):
                field_type = 'DATETIME'
            elif isinstance(field, models.DateField):
                field_type = 'DATE'
            elif isinstance(field, models.ForeignKey):
                field_type = 'INTEGER'
            elif isinstance(field, models.EmailField):
                max_length = getattr(field, 'max_length', 254)
                field_type = f'VARCHAR({max_length})'
            elif isinstance(field, models.URLField):
                max_length = getattr(field, 'max_length', 200)
                field_type = f'VARCHAR({max_length})'
            elif isinstance(field, models.FileField):
                max_length = getattr(field, 'max_length', 100)
                field_type = f'VARCHAR({max_length})'
            elif isinstance(field, models.ImageField):
                max_length = getattr(field, 'max_length', 100)
                field_type = f'VARCHAR({max_length})'
            elif isinstance(field, models.JSONField):
                field_type = 'TEXT'
            elif isinstance(field, models.SlugField):
                max_length = getattr(field, 'max_length', 50)
                field_type = f'VARCHAR({max_length})'
            
            model_fields[field.name] = {
                'type': field_type,
                'default': default_value,
                'null': getattr(field, 'null', False),
                'blank': getattr(field, 'blank', False),
            }
    
    # Get existing columns from database
    with connection.cursor() as cursor:
        try:
            cursor.execute(f"PRAGMA table_info({table_name})")
            db_columns = [col[1] for col in cursor.fetchall()]
        except:
            db_columns = []
            issues_found.append(f"Could not access table: {table_name}")
            continue
    
    # Find and add missing columns
    missing = []
    for field_name, field_info in model_fields.items():
        if field_name not in db_columns:
            missing.append(field_name)
    
    if missing:
        print(f"  Found {len(missing)} missing column(s):")
        for field_name in missing:
            print(f"    - {field_name}")
        
        # Add missing columns
        for field_name, field_info in model_fields.items():
            if field_name not in db_columns:
                col_type = field_info['type']
                default = field_info['default']
                
                # Build ALTER TABLE command
                alter_sql = f"ALTER TABLE {table_name} ADD COLUMN {field_name} {col_type}"
                if default is not None:
                    if isinstance(default, str):
                        alter_sql += f" DEFAULT '{default}'"
                    else:
                        alter_sql += f" DEFAULT {default}"
                
                try:
                    with connection.cursor() as cursor:
                        cursor.execute(alter_sql)
                    columns_added += 1
                    print(f"  ✅ Added: {field_name} ({col_type})")
                except Exception as e:
                    print(f"  ❌ Error adding {field_name}: {e}")
                    issues_found.append(f"Error adding {field_name} to {table_name}: {e}")
    else:
        print(f"  ✅ No missing columns found")

print("\n" + "=" * 70)
print("SUMMARY")
print("=" * 70)
print(f"Tables checked: {tables_checked}")
print(f"Columns added: {columns_added}")

if issues_found:
    print(f"\nIssues encountered ({len(issues_found)}):")
    for issue in issues_found:
        print(f"  - {issue}")
else:
    print("\n✅ No issues encountered. All tables are up to date!")

print("\n" + "=" * 70)