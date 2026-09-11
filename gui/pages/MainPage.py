"""
MakiAI — Main Page
The heart of the MakiAI interface.
Modern UI/UX aligned with MakiSync brand identity and dark glassmorphic styling.

Contains:
  - Top bar: MakiSync branding, status pill badge, settings/logout, window controls
  - Center: Animation HUD (idle/listening/thinking/speaking states) with wake hint
  - Right: Chat log (conversation history with sleek cards)
  - Bottom: Transcription bar (real-time STT text + manual text input)
"""

from typing import Callable

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QScrollArea, QTextEdit,
    QLineEdit, QSizePolicy, QSpacerItem,
)
from PyQt6.QtCore import Qt, QSize, pyqtSlot, pyqtSignal
from PyQt6.QtGui import QFont, QColor

from core.orchestrator import Orchestrator
from core.state_manager import StateManager, AppState
from services.auth.auth_service import AuthService
from services.settings.settings_service import SettingsService
from gui.components.AnimationWidget import AnimationWidget
from gui.components.StatusIndicator import StatusIndicator


# State brand colors
STATE_COLORS = {
    AppState.IDLE:      "#0a0f1a",
    AppState.LISTENING: "#0d2238",
    AppState.THINKING:  "#241d0e",
    AppState.SPEAKING:  "#0d1d36",
}

STATE_LABELS = {
    AppState.IDLE:      "Idle",
    AppState.LISTENING: "Listening...",
    AppState.THINKING:  "Thinking...",
    AppState.SPEAKING:  "Speaking...",
}

STATE_COLORS_TEXT = {
    AppState.IDLE:      "#64748b",
    AppState.LISTENING: "#38bdf8",
    AppState.THINKING:  "#fbbf24",
    AppState.SPEAKING:  "#3b82f6",
}


class MainPage(QWidget):
    """
    Primary interactive UI page for MakiAI.
    """

    # Signals for thread-safe GUI updates from background threads
    add_message_signal = pyqtSignal(str, str)
    update_transcription_signal = pyqtSignal(str)

    def __init__(
        self,
        orchestrator: Orchestrator,
        state_manager: StateManager,
        settings: SettingsService,
        auth: AuthService,
        on_logout: Callable[[], None],
        on_open_settings: Callable[[], None] | None = None,
    ):
        super().__init__()
        self.orchestrator = orchestrator
        self.state_manager = state_manager
        self.settings = settings
        self.auth = auth
        self.on_logout = on_logout
        self.on_open_settings = on_open_settings or (lambda: None)

        self._build_ui()

        # Wire AnimationWidget and StatusIndicator to state changes
        self.state_manager.on_state_change(self.animation_widget.set_state)
        self.state_manager.on_state_change(self.status_badge.set_state)
        self.state_manager.on_state_change(self._on_state_change)

        # Connect thread-safe signals
        self.add_message_signal.connect(self.add_message)
        self.update_transcription_signal.connect(self.update_transcription)

    # ─── UI Build ─────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        """Construct the full main page layout."""
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._build_top_bar())
        root.addWidget(self._build_body(), stretch=1)
        root.addWidget(self._build_transcription_bar())

    def _build_top_bar(self) -> QFrame:
        """Top bar: logo, app name, status badge, window controls."""
        bar = QFrame()
        bar.setFixedHeight(54)
        bar.setObjectName("topBar")
        bar.setStyleSheet("""
            QFrame#topBar {
                background-color: #0d1527;
                border-bottom: 1px solid rgba(140, 171, 214, 0.12);
            }
        """)

        layout = QHBoxLayout(bar)
        layout.setContentsMargins(20, 0, 16, 0)
        layout.setSpacing(12)

        # Logo + name
        logo = QLabel("◈")
        logo.setStyleSheet("color: #3b82f6; font-size: 20px; font-weight: bold;")

        name = QLabel("MakiAI")
        name.setStyleSheet("""
            color: #f8fafc;
            font-size: 15px;
            font-weight: 700;
            letter-spacing: 2px;
        """)

        # Status indicator badge
        self.status_badge = StatusIndicator()

        # Spacer
        spacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        # Window controls
        minimize_btn = QPushButton("─")
        maximize_btn = QPushButton("□")
        close_btn = QPushButton("✕")

        for btn in [minimize_btn, maximize_btn, close_btn]:
            btn.setFixedSize(30, 30)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet("""
                QPushButton {
                    background: transparent;
                    color: #94a3b8;
                    border: none;
                    font-size: 12px;
                    border-radius: 6px;
                }
                QPushButton:hover {
                    background: rgba(140, 171, 214, 0.12);
                    color: #f8fafc;
                }
            """)

        close_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #94a3b8;
                border: none;
                font-size: 12px;
                border-radius: 6px;
            }
            QPushButton:hover {
                background: #ef4444;
                color: #ffffff;
            }
        """)

        minimize_btn.clicked.connect(self.window().showMinimized)
        maximize_btn.clicked.connect(self._toggle_maximize)
        close_btn.clicked.connect(self.window().close)

        # Settings + logout buttons
        settings_btn = QPushButton("⚙  Settings")
        logout_btn = QPushButton("↩  Logout")

        for btn in [settings_btn, logout_btn]:
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setFixedHeight(30)
            btn.setStyleSheet("""
                QPushButton {
                    background: rgba(16, 23, 38, 0.7);
                    color: #94a3b8;
                    border: 1px solid rgba(140, 171, 214, 0.18);
                    border-radius: 6px;
                    padding: 0 12px;
                    font-size: 12px;
                    font-weight: 500;
                }
                QPushButton:hover {
                    color: #f8fafc;
                    border-color: #3b82f6;
                    background: rgba(59, 130, 246, 0.12);
                }
            """)

        logout_btn.clicked.connect(self._handle_logout)
        settings_btn.clicked.connect(self.on_open_settings)

        layout.addWidget(logo)
        layout.addWidget(name)
        layout.addSpacing(12)
        layout.addWidget(self.status_badge)
        layout.addItem(spacer)
        layout.addWidget(settings_btn)
        layout.addWidget(logout_btn)
        layout.addSpacing(8)
        layout.addWidget(minimize_btn)
        layout.addWidget(maximize_btn)
        layout.addWidget(close_btn)

        return bar

    def _build_body(self) -> QWidget:
        """Body: animation area (left/center) + chat log (right)."""
        body = QWidget()
        layout = QHBoxLayout(body)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        layout.addWidget(self._build_animation_area(), stretch=3)
        layout.addWidget(self._build_divider())
        layout.addWidget(self._build_chat_log(), stretch=2)

        return body

    def _build_animation_area(self) -> QFrame:
        """
        Center stage — AnimationWidget with Lottie animations.
        """
        frame = QFrame()
        frame.setObjectName("animationArea")
        frame.setStyleSheet("QFrame#animationArea { background-color: #0a0f1a; }")

        layout = QVBoxLayout(frame)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(16)

        # AnimationWidget
        self.animation_widget = AnimationWidget()
        self.animation_widget.setFixedSize(320, 320)

        # Hint pill
        hint_pill = QFrame()
        hint_pill.setStyleSheet("""
            QFrame {
                background-color: rgba(15, 23, 42, 0.6);
                border: 1px solid rgba(140, 171, 214, 0.12);
                border-radius: 14px;
                padding: 4px 14px;
            }
        """)
        hint_layout = QHBoxLayout(hint_pill)
        hint_layout.setContentsMargins(12, 4, 12, 4)
        hint_layout.setSpacing(6)

        hint_sparkle = QLabel("✦")
        hint_sparkle.setStyleSheet("color: #3b82f6; font-size: 11px; border: none; background: transparent;")

        hint_text = QLabel('Say  "Hey Maki"  to wake me up')
        hint_text.setStyleSheet("""
            color: #64748b;
            font-size: 12px;
            letter-spacing: 1px;
            border: none;
            background: transparent;
            font-weight: 500;
        """)

        hint_layout.addWidget(hint_sparkle)
        hint_layout.addWidget(hint_text)

        layout.addStretch()
        layout.addWidget(self.animation_widget, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(hint_pill, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addStretch()

        return frame

    def _build_divider(self) -> QFrame:
        """Thin vertical divider between animation and chat log."""
        divider = QFrame()
        divider.setFixedWidth(1)
        divider.setStyleSheet("background-color: rgba(140, 171, 214, 0.12);")
        return divider

    def _build_chat_log(self) -> QFrame:
        """Right panel — scrollable conversation history."""
        panel = QFrame()
        panel.setObjectName("chatPanel")
        panel.setStyleSheet("""
            QFrame#chatPanel {
                background-color: #0c1322;
            }
        """)

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header
        header = QLabel("  CONVERSATION")
        header.setFixedHeight(46)
        header.setStyleSheet("""
            color: #64748b;
            font-size: 11px;
            letter-spacing: 2px;
            font-weight: 700;
            border-bottom: 1px solid rgba(140, 171, 214, 0.10);
            padding-left: 20px;
        """)

        # Scrollable chat area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("""
            QScrollArea { border: none; background: transparent; }
            QWidget { background: transparent; }
            QScrollBar:vertical {
                background: #0c1322;
                width: 5px;
                border-radius: 2px;
            }
            QScrollBar::handle:vertical {
                background: #1e293b;
                border-radius: 2px;
            }
            QScrollBar::handle:vertical:hover {
                background: #3b82f6;
            }
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical { height: 0px; }
        """)

        self.chat_container = QWidget()
        self.chat_layout = QVBoxLayout(self.chat_container)
        self.chat_layout.setContentsMargins(16, 16, 16, 24)
        self.chat_layout.setSpacing(12)
        self.chat_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Empty state
        self.empty_chat_label = QLabel("No conversation yet.\nSay 'Hey Maki' to begin.")
        self.empty_chat_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_chat_label.setStyleSheet("""
            color: #475569;
            font-size: 13px;
            line-height: 1.8;
            margin-top: 40px;
        """)
        self.chat_layout.addWidget(self.empty_chat_label)

        scroll.setWidget(self.chat_container)
        self._chat_scroll = scroll

        layout.addWidget(header)
        layout.addWidget(scroll, stretch=1)

        return panel

    def _build_transcription_bar(self) -> QFrame:
        """Bottom bar — real-time transcription + manual text input."""
        bar = QFrame()
        bar.setFixedHeight(72)
        bar.setObjectName("transcriptionBar")
        bar.setStyleSheet("""
            QFrame#transcriptionBar {
                background-color: #0d1527;
                border-top: 1px solid rgba(140, 171, 214, 0.12);
            }
        """)

        layout = QHBoxLayout(bar)
        layout.setContentsMargins(24, 0, 24, 0)
        layout.setSpacing(12)

        # Mic indicator pill
        mic_pill = QFrame()
        mic_pill.setFixedSize(38, 38)
        mic_pill.setStyleSheet("""
            QFrame {
                background-color: rgba(59, 130, 246, 0.12);
                border: 1px solid rgba(59, 130, 246, 0.25);
                border-radius: 19px;
            }
        """)
        mic_layout = QVBoxLayout(mic_pill)
        mic_layout.setContentsMargins(0, 0, 0, 0)
        mic_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        mic_icon = QLabel("🎙")
        mic_icon.setStyleSheet("font-size: 16px; border: none; background: transparent;")
        mic_layout.addWidget(mic_icon, alignment=Qt.AlignmentFlag.AlignCenter)

        # Text input
        self.transcription_input = QLineEdit()
        self.transcription_input.setPlaceholderText(
            'Type a command or say "Hey Maki" ...'
        )
        self.transcription_input.setFixedHeight(44)
        self.transcription_input.setStyleSheet("""
            QLineEdit {
                background-color: #101726;
                color: #f8fafc;
                border: 1px solid rgba(140, 171, 214, 0.18);
                border-radius: 22px;
                padding: 0 20px;
                font-size: 13px;
            }
            QLineEdit:focus {
                border: 1px solid #3b82f6;
                background-color: #0f172a;
                color: #ffffff;
            }
            QLineEdit::placeholder {
                color: #475569;
            }
        """)
        self.transcription_input.returnPressed.connect(self._handle_text_command)

        # Send button
        send_btn = QPushButton("➤")
        send_btn.setFixedSize(44, 44)
        send_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        send_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #2563eb, stop:1 #3b82f6);
                color: #ffffff;
                border: none;
                border-radius: 22px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #3b82f6, stop:1 #60a5fa);
            }
            QPushButton:pressed {
                background: #1d4ed8;
            }
        """)
        send_btn.clicked.connect(self._handle_text_command)

        layout.addWidget(mic_pill)
        layout.addWidget(self.transcription_input, stretch=1)
        layout.addWidget(send_btn)

        return bar

    # ─── State Updates ────────────────────────────────────────────────────────

    @pyqtSlot(object)
    def _on_state_change(self, new_state: AppState) -> None:
        """Hook for future MainPage-level state reactions."""
        pass

    def update_transcription(self, text: str) -> None:
        """Display live transcription text in the input bar."""
        self.transcription_input.setText(text)

    # ─── Chat Log ─────────────────────────────────────────────────────────────

    def add_message(self, role: str, text: str) -> None:
        """Append a message to the conversation log."""
        if self.empty_chat_label.isVisible():
            self.empty_chat_label.setVisible(False)

        bubble = self._make_bubble(role, text)
        self.chat_layout.addWidget(bubble)

        # Auto-scroll to bottom
        self._chat_scroll.verticalScrollBar().setValue(
            self._chat_scroll.verticalScrollBar().maximum()
        )

    def _make_bubble(self, role: str, text: str) -> QFrame:
        """Create a chat bubble card for user or Maki messages."""
        import re
        display_text = re.sub(r'\*{1,3}(.*?)\*{1,3}', r'\1', text)
        display_text = re.sub(r'`([^`]+)`', r'\1', display_text)

        bubble = QFrame()
        layout = QVBoxLayout(bubble)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(6)

        is_maki = (role == "maki")

        role_label = QLabel("You" if role == "user" else "Maki")
        role_label.setStyleSheet(
            f"color: {'#38bdf8' if is_maki else '#94a3b8'}; "
            f"font-size: 11px; font-weight: 700; letter-spacing: 0.5px; border: none;"
        )

        msg_label = QLabel(display_text)
        msg_label.setWordWrap(True)
        msg_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        msg_label.setStyleSheet("color: #f1f5f9; font-size: 13px; line-height: 1.6; border: none;")
        msg_label.setMinimumWidth(200)
        msg_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        layout.addWidget(role_label)
        layout.addWidget(msg_label)

        if is_maki:
            bubble.setStyleSheet("""
                QFrame {
                    background-color: #0f172a;
                    border-radius: 10px;
                    border: 1px solid rgba(59, 130, 246, 0.25);
                    border-left: 3px solid #3b82f6;
                }
            """)
        else:
            bubble.setStyleSheet("""
                QFrame {
                    background-color: #1e293b;
                    border-radius: 10px;
                    border: 1px solid rgba(140, 171, 214, 0.14);
                }
            """)

        return bubble

    # ─── Commands ─────────────────────────────────────────────────────────────

    def _handle_text_command(self) -> None:
        """Handle manual text input from the transcription bar."""
        text = self.transcription_input.text().strip()
        if not text:
            return

        self.transcription_input.clear()
        self.add_message("user", text)

        import threading
        def run():
            response = self.orchestrator.handle_command(text)
            if response:
                from PyQt6.QtCore import QMetaObject, Qt, Q_ARG
                QMetaObject.invokeMethod(
                    self, "_add_maki_message",
                    Qt.ConnectionType.QueuedConnection,
                    Q_ARG(str, response),
                )

        threading.Thread(target=run, daemon=True).start()

    @pyqtSlot(str)
    def _add_maki_message(self, text: str) -> None:
        """Thread-safe slot to add Maki's response to the chat log."""
        self.add_message("maki", text)

    def _handle_logout(self) -> None:
        """Trigger logout — returns to LoginPage."""
        self.on_logout()

    def _toggle_maximize(self) -> None:
        """Toggle between maximized and normal window state."""
        win = self.window()
        if win.isMaximized():
            win.showNormal()
        else:
            win.showMaximized()

    def show_confirmation(self, text: str) -> None:
        """Show a low-confidence transcription confirmation prompt."""
        self.state_manager.set_state(AppState.IDLE)
        self.add_message(
            "maki",
            f'I heard: "{text}"\n\nDid I get that right? You can confirm by retyping it below, or just say it again.'
        )
        self.transcription_input.setText(text)
        self.transcription_input.setFocus()
        self.transcription_input.selectAll()

    # ─── Lifecycle ────────────────────────────────────────────────────────────

    def on_enter(self) -> None:
        """Called when MainPage becomes the active page."""
        self.add_message("maki", "Hello sir. I'm online and ready. Say \"Hey Maki\" or type a command below.")
        self.transcription_input.setFocus()
