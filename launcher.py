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


def get_base_dir():
    """Return the base directory whether running as script or frozen exe."""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def get_resource_dir():
    """Return where templates/static/media live."""
    if getattr(sys, 'frozen', False):
        return os.path.join(sys._MEIPASS, '_internal')
    return os.path.dirname(os.path.abspath(__file__))


BASE_DIR = get_base_dir()
RESOURCE_DIR = get_resource_dir()


def find_free_port(start=8000, end=9000):
    """Find an available port."""
    for port in range(start, end):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    return 8000


def open_browser(url, delay=2):
    """Open the browser after a short delay."""
    time.sleep(delay)
    webbrowser.open(url)


def main():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tenohms.settings.desktop")

    # Set paths for bundled or development mode
    if getattr(sys, 'frozen', False):
        os.environ["TENOHMS_BASE_DIR"] = RESOURCE_DIR
    else:
        os.environ["TENOHMS_BASE_DIR"] = BASE_DIR

    try:
        import django
        django.setup()
    except Exception as e:
        print(f"Error initializing Django: {e}")
        input("Press Enter to exit...")
        sys.exit(1)

    # Ensure database exists
    from django.core.management import call_command
    try:
        call_command("migrate", "--run-syncdb", verbosity=0)
    except Exception:
        pass

    port = find_free_port()
    url = f"http://127.0.0.1:{port}"

    print("=" * 50)
    print("  TenoHMS - Hospital Management System")
    print("=" * 50)
    print(f"  Starting server at: {url}")
    print(f"  Close this window to stop the server.")
    print("=" * 50)

    # Open browser in a thread
    browser_thread = threading.Thread(target=open_browser, args=(url,), daemon=True)
    browser_thread.start()

    # Run Django server
    from django.core.management import execute_from_command_line
    sys.argv = ["manage.py", "runserver", f"127.0.0.1:{port}", "--noreload"]
    try:
        execute_from_command_line(sys.argv)
    except KeyboardInterrupt:
        print("\nServer stopped.")


if __name__ == "__main__":
    main()
