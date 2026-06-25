"""loaddata 後重設 PostgreSQL 序列，避免後續新增資料 PK 衝突。"""
import os
import sys

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "website_configs.settings")
django.setup()

from django.apps import apps
from django.db import connection


def reset_sequences() -> int:
    reset_count = 0
    with connection.cursor() as cursor:
        for model in apps.get_models():
            if not model._meta.managed:
                continue
            pk_field = model._meta.pk
            if pk_field is None or not getattr(pk_field, "auto_created", False):
                continue
            table = model._meta.db_table
            column = pk_field.column
            cursor.execute(f'SELECT COALESCE(MAX("{column}"), 0) FROM "{table}"')
            max_val = cursor.fetchone()[0]
            cursor.execute("SELECT pg_get_serial_sequence(%s, %s)", [table, column])
            seq = cursor.fetchone()[0]
            if not seq:
                continue
            if max_val:
                cursor.execute("SELECT setval(%s, %s, true)", [seq, max_val])
            else:
                cursor.execute("SELECT setval(%s, 1, false)", [seq])
            reset_count += 1
    return reset_count


if __name__ == "__main__":
    count = reset_sequences()
    print(f"已重設 {count} 個序列")
    sys.exit(0)
