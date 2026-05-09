import importlib
import sys
import traceback

sys.path.insert(0, '')

mod = importlib.import_module('tests.unit.test_activity_retention')
names = [
    'test_retention_counts_active_users_only',
    'test_retention_no_users',
    'test_retention_clamped'
]

for n in names:
    try:
        getattr(mod, n)()
        print(n + ' OK')
    except Exception:
        traceback.print_exc()
        sys.exit(1)

print('ALL OK')
