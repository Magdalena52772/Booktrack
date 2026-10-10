"""Uruchamia deweloperską webówkę BookTrack."""

import os
import sys


DEFAULT_ADDRESS = "127.0.0.1:8000"


def main():
    """Wykonuje brakujące migracje i uruchamia standardowy serwer Django."""
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")

    import django
    from django.core.management import call_command, execute_from_command_line
    from django.db import DEFAULT_DB_ALIAS, connections
    from django.db.migrations.executor import MigrationExecutor

    django.setup()
    connection = connections[DEFAULT_DB_ALIAS]
    migration_executor = MigrationExecutor(connection)
    migration_plan = migration_executor.migration_plan(
        migration_executor.loader.graph.leaf_nodes()
    )

    if migration_plan:
        print("Wykryto niezaaplikowane migracje. Aktualizuję bazę Django...")
        call_command("migrate", interactive=False)
    else:
        print("Migracje Django są aktualne — pomijam migrację.")

    server_arguments = sys.argv[1:] or [DEFAULT_ADDRESS]
    address = next(
        (argument for argument in server_arguments if not argument.startswith("-")),
        DEFAULT_ADDRESS,
    )
    print(f"BookTrack web działa pod adresem: http://{address}/")
    print("Aby zatrzymać serwer, naciśnij Ctrl+C.")

    # Uruchamiamy właściwe polecenie Django, aby autoreloader działał standardowo.
    execute_from_command_line(["manage.py", "runserver", *server_arguments])


if __name__ == "__main__":
    main()
