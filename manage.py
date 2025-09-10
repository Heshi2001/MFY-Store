#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys


def main():
    """Run administrative tasks."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dmart.settings')
    
    try:
        import django
        from django.core.management import execute_from_command_line, call_command

        # Setup Django
        django.setup()

        # Run migrations automatically on startup
        try:
            call_command('migrate', interactive=False)
            print("Database migration applied successfully.")
        except Exception as e:
            print(f"Migration failed: {e}")
            
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc

    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
