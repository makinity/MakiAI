"""
MakiAI — Login Page
Handles two scenarios:
  1. First launch — user creates a password (setup mode)
  2. Returning launch — user enters existing password (login mode)

On successful auth, calls the on_success callback to navigate to MainPage.
Follows MakiSync brand colors and modern glassmorphic card design.
"""

from typing import Callable

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QFrame, QSizePolicy,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QColor

from services.auth.auth_service import AuthService
from services.settings.settings_service import SettingsService


class LoginPage(QWidget):
    """
    Login / first-launch setup page.

    First launch: shows "Welcome — Create a password" setup form.
    Returning: shows "Welcome back — Enter your password" login form.
    """

    def __init__(
        self,
        auth: AuthService,
        settings: SettingsService,
        on_success: Callable[[], None],
    ):
        super().__init__()
        self.auth = auth
        self.settings = settings
        self.on_success = on_success

        self._build_ui()
        self._detect_mode()

    # ─── UI Build ─────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        """Construct the full login page layout."""
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # ── Card container ────────────────────────────────────────────────────
        card = QFrame()
        card.setFixedWidth(440)
        card.setObjectName("loginCard")
        card.setStyleSheet("""
            QFrame#loginCard {
                background-color: #0d1527;
                border: 1px solid rgba(140, 171, 214, 0.18);
                border-radius: 16px;
            }
        """)

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(48, 48, 48, 48)
        card_layout.setSpacing(20)
        card_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # ── Logo / Name ───────────────────────────────────────────────────────
        logo_label = QLabel("◈")
        logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo_label.setStyleSheet("color: #3b82f6; font-size: 42px; font-weight: bold; margin-bottom: 2px;")

        app_name_label = QLabel("MakiAI")
        app_name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        app_name_label.setStyleSheet("""
            color: #ffffff;
            font-size: 26px;
            font-weight: 800;
            letter-spacing: 3px;
        """)

        # ── Subtitle (changes per mode) ───────────────────────────────────────
        self.subtitle_label = QLabel()
        self.subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.subtitle_label.setWordWrap(True)
        self.subtitle_label.setStyleSheet("color: #94a3b8; font-size: 13px; margin-bottom: 6px;")

        # ── Confirm password field (setup mode only) ──────────────────────────
        self.confirm_field = QLineEdit()
        self.confirm_field.setPlaceholderText("Confirm password")
        self.confirm_field.setEchoMode(QLineEdit.EchoMode.Password)
        self.confirm_field.setFixedHeight(48)
        self.confirm_field.setStyleSheet(self._input_style())

        # ── Password field ────────────────────────────────────────────────────
        self.password_field = QLineEdit()
        self.password_field.setPlaceholderText("Password")
        self.password_field.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_field.setFixedHeight(48)
        self.password_field.setStyleSheet(self._input_style())
        self.password_field.returnPressed.connect(self._handle_submit)

        # ── Error message ─────────────────────────────────────────────────────
        self.error_label = QLabel("")
        self.error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.error_label.setStyleSheet("color: #ef4444; font-size: 12px; font-weight: 500;")
        self.error_label.setVisible(False)

        # ── Submit button ─────────────────────────────────────────────────────
        self.submit_btn = QPushButton()
        self.submit_btn.setFixedHeight(48)
        self.submit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.submit_btn.setStyleSheet(self._button_style())
        self.submit_btn.clicked.connect(self._handle_submit)

        # ── Assemble card ─────────────────────────────────────────────────────
        card_layout.addWidget(logo_label)
        card_layout.addWidget(app_name_label)
        card_layout.addWidget(self.subtitle_label)
        card_layout.addSpacing(8)
        card_layout.addWidget(self.confirm_field)
        card_layout.addWidget(self.password_field)
        card_layout.addWidget(self.error_label)
        card_layout.addSpacing(4)
        card_layout.addWidget(self.submit_btn)

        root_layout.addWidget(card)

    # ─── Mode Detection ───────────────────────────────────────────────────────

    def _detect_mode(self) -> None:
        """Switch UI text between setup mode and login mode."""
        if self.auth.is_first_launch():
            self._set_setup_mode()
        else:
            self._set_login_mode()

    def _set_setup_mode(self) -> None:
        """Configure UI for first-launch password creation."""
        self.subtitle_label.setText(
            "Welcome. Create a password to secure your assistant."
        )
        self.password_field.setPlaceholderText("Create a password")
        self.confirm_field.setVisible(True)
        self.submit_btn.setText("Create Password")
        self._mode = "setup"

    def _set_login_mode(self) -> None:
        """Configure UI for returning user login."""
        self.subtitle_label.setText("Welcome back, Mark.")
        self.password_field.setPlaceholderText("Enter your password")
        self.confirm_field.setVisible(False)
        self.submit_btn.setText("Unlock")
        self._mode = "login"

    # ─── Form Submission ──────────────────────────────────────────────────────

    def _handle_submit(self) -> None:
        """Handle the submit button or Enter key press."""
        self._clear_error()

        if self._mode == "setup":
            self._handle_setup()
        else:
            self._handle_login()

    def _handle_setup(self) -> None:
        """Validate and save password during first-launch setup."""
        password = self.password_field.text()
        confirm = self.confirm_field.text()

        if len(password) < 6:
            self._show_error("Password must be at least 6 characters.")
            return

        if password != confirm:
            self._show_error("Passwords do not match.")
            return

        success = self.auth.setup_password(password)
        if success:
            print("[LoginPage] Password created — logging in.")
            self.on_success()
        else:
            self._show_error("Failed to save password. Try again.")

    def _handle_login(self) -> None:
        """Verify password and proceed on success."""
        password = self.password_field.text()

        if not password:
            self._show_error("Please enter your password.")
            return

        if self.auth.login(password):
            print("[LoginPage] Login success.")
            self.on_success()
        else:
            self._show_error("Incorrect password. Try again.")
            self.password_field.clear()
            self.password_field.setFocus()

    # ─── Helpers ──────────────────────────────────────────────────────────────

    def _show_error(self, message: str) -> None:
        self.error_label.setText(message)
        self.error_label.setVisible(True)

    def _clear_error(self) -> None:
        self.error_label.setText("")
        self.error_label.setVisible(False)

    def reset(self) -> None:
        """
        Reset the page state for when the user returns after logout.
        """
        self.password_field.clear()
        self.confirm_field.clear()
        self._clear_error()
        self._detect_mode()
        self.password_field.setFocus()

    # ─── Styles ───────────────────────────────────────────────────────────────

    def _input_style(self) -> str:
        return """
            QLineEdit {
                background-color: #101726;
                color: #f8fafc;
                border: 1px solid rgba(140, 171, 214, 0.18);
                border-radius: 10px;
                padding: 0 16px;
                font-size: 14px;
            }
            QLineEdit:focus {
                border: 1px solid #3b82f6;
                background-color: #0f172a;
                color: #ffffff;
            }
            QLineEdit::placeholder {
                color: #475569;
            }
        """

    def _button_style(self) -> str:
        return """
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #2563eb, stop:1 #3b82f6);
                color: #ffffff;
                border: none;
                border-radius: 10px;
                font-size: 14px;
                font-weight: 700;
                letter-spacing: 0.5px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #3b82f6, stop:1 #60a5fa);
            }
            QPushButton:pressed {
                background: #1d4ed8;
            }
        """
