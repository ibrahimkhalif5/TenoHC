#!/usr/bin/env python
"""
TenoHMS Desktop Launcher
Starts the Django server and opens the browser automatically.
"""
import os
import sys
import socket
import threading
import time
import webbrowser
import traceback


def main():
    # ── Paths ──────────────────────────────────────────────
    if getattr(sys, 'frozen', False):
        BUNDLE_DIR = sys._MEIPASS
        EXE_DIR = os.path.dirname(sys.executable)
    else:
        BUNDLE_DIR = os.path.dirname(os.path.abspath(__file__))
        EXE_DIR = BUNDLE_DIR

    os.environ["TENOHMS_BUNDLE_DIR"] = BUNDLE_DIR
    os.environ["TENOHMS_DATA_DIR"] = EXE_DIR
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tenohms.settings.desktop")

    # ── Django init ────────────────────────────────────────
    try:
        import django
        django.setup()
    except Exception as e:
        print(f"Error initializing Django:\n{traceback.format_exc()}")
        input("Press Enter to exit...")
        sys.exit(1)

    # ── Migrate ────────────────────────────────────────────
    from django.core.management import call_command
    try:
        call_command("migrate", "--run-syncdb", verbosity=0)
        print("  Database ready.")
    except Exception as e:
        print(f"  Migration warning: {e}")

    # ── Create admin user if needed ────────────────────────
    from django.contrib.auth import get_user_model
    User = get_user_model()
    if not User.objects.exists():
        try:
            admin_user = User.objects.create_superuser(
                username="hassan",
                email="hassan@tenohms.local",
                password="admin123",
                first_name="Hassan",
                last_name="Adan",
            )
            admin_user.role = "ADMIN"
            admin_user.save()
            print("  Default admin created — username: hassan  password: admin123")
        except Exception as e:
            print(f"  Admin creation warning: {e}")

    # ── Seed master data (always, commands use get_or_create) ──
    seed_commands = [
        "seed_wards",
        "seed_lab_tests",
        "seed_lab_templates",
        "seed_medicines",
        "seed_radiology_services",
    ]
    for cmd in seed_commands:
        try:
            call_command(cmd, verbosity=0)
            print(f"  Seeded: {cmd}")
        except Exception as e:
            print(f"  Seed warning ({cmd}): {e}")

    # ── Find port ──────────────────────────────────────────
    port = 8000
    for p in range(8000, 9000):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", p))
                port = p
                break
            except OSError:
                continue

    url = f"http://127.0.0.1:{port}"

    print("=" * 50)
    print("  TenoHMS - Hospital Management System")
    print("=" * 50)
    print(f"  Starting server at: {url}")
    print(f"  Close this window to stop the server.")
    print("=" * 50)

    # ── Open browser ───────────────────────────────────────
    def open_browser():
        time.sleep(2)
        webbrowser.open(url)

    threading.Thread(target=open_browser, daemon=True).start()

    # ── Run server ─────────────────────────────────────────
    from django.core.management import execute_from_command_line
    sys.argv = ["manage.py", "runserver", f"127.0.0.1:{port}", "--noreload"]
    try:
        execute_from_command_line(sys.argv)
    except KeyboardInterrupt:
        print("\nServer stopped.")
    except Exception as e:
        print(f"\nServer error:\n{traceback.format_exc()}")
        input("Press Enter to exit...")


if __name__ == "__main__":
    main()
