"""
MakiAI — Entry Point
Launches the PyQt6 application and shows the main window.

Run with:
    python main.py
"""

import sys
import os
import threading
import traceback
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QFont

from gui.main_window import MainWindow


def handle_exception(exc_type, exc_value, exc_traceback):
    """Global exception handler — log crashes without closing the app."""
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    print("\n[MakiAI] Unhandled exception:")
    traceback.print_exception(exc_type, exc_value, exc_traceback)


def handle_thread_exception(args):
    """Catch exceptions in background threads."""
    if args.exc_type == SystemExit:
        return
    print(f"\n[MakiAI] Thread '{args.thread.name}' crashed:")
    traceback.print_exception(args.exc_type, args.exc_value, args.exc_traceback)


def main() -> None:
    """Bootstrap and launch the MakiAI desktop application."""
    sys.excepthook = handle_exception
    threading.excepthook = handle_thread_exception

    # Suppress HuggingFace symlink warning on Windows
    os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"

    app = QApplication(sys.argv)
    app.setApplicationName("MakiAI")
    app.setApplicationVersion("1.0.0")

    font = QFont("Segoe UI", 10)
    app.setFont(font)

    window = MainWindow()
    window.resize(1100, 700)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
