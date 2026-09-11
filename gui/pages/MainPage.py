"""
MakiAI — Main Page
The heart of the MakiAI interface.

This is the interactive HUD that Mark sees after logging in.
Contains:
  - Center: Animation widget (idle/listening/thinking/speaking states)
  - Bottom: Transcription bar (real-time STT text)
  - Right: Chat log (conversation history)
  - Top bar: Status indicator + window controls

Phase 1: Shell layout with placeholder animation states.
Phase 5: Lottie animations will replace the placeholder.
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


# Animation placeholder colors per state (replaced by Lottie in Phase 5)
STATE_COLORS = {
    AppState.IDLE:      "#1a1a2e",
    AppState.LISTENING: "#0d2b1e",
    AppState.THINKING:  "#1e1a0d",
    AppState.SPEAKING:  "#0d1a2e",
}

STATE_LABELS = {
    AppState.IDLE:      "Idle",
    AppState.LISTENING: "Listening...",
    AppState.THINKING:  "Thinking...",
    AppState.SPEAKING:  "Speaking...",
}

STATE_COLORS_TEXT = {
    AppState.IDLE:      "#4a4a6a",
    AppState.LISTENING: "#00ff88",
    AppState.THINKING:  "#ffcc00",
    AppState.SPEAKING:  "#00d4ff",
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
        bar.setFixedHeight(52)
        bar.setObjectName("topBar")
        bar.setStyleSheet("""
            QFrame#topBar {
                background-color: #0d0d1a;
                border-bottom: 1px solid #1e1e3a;
            }
        """)

        layout = QHBoxLayout(bar)
        layout.setContentsMargins(20, 0, 16, 0)
        layout.setSpacing(12)

        # Logo + name
        logo = QLabel("◈")
        logo.setStyleSheet("color: #00d4ff; font-size: 18px;")

        name = QLabel("MakiAI")
        name.setStyleSheet("""
            color: #ffffff;
            font-size: 15px;
            font-weight: bold;
            letter-spacing: 3px;
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
            btn.setFixedSize(32, 32)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet("""
                QPushButton {
                    background: transparent;
                    color: #6b7280;
                    border: none;
                    font-size: 13px;
                    border-radius: 4px;
                }
                QPushButton:hover { background: #1e1e3a; color: #ffffff; }
            """)

        close_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #6b7280;
                border: none;
                font-size: 13px;
                border-radius: 4px;
            }
            QPushButton:hover { background: #ef4444; color: #ffffff; }
        """)

        minimize_btn.clicked.connect(self.window().showMinimized)
        maximize_btn.clicked.connect(self._toggle_maximize)
        close_btn.clicked.connect(self.window().close)

        # Settings + logout buttons
        settings_btn = QPushButton("⚙")
        logout_btn = QPushButton("↩ Logout")

        for btn in [settings_btn, logout_btn]:
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setFixedHeight(30)
            btn.setStyleSheet("""
                QPushButton {
                    background: transparent;
                    color: #6b7280;
                    border: 1px solid #2a2a4a;
                    border-radius: 6px;
                    padding: 0 10px;
                    font-size: 12px;
                }
                QPushButton:hover { color: #ffffff; border-color: #00d4ff; }
            """)

        logout_btn.clicked.connect(self._handle_logout)
        settings_btn.clicked.connect(self.on_open_settings)

        layout.addWidget(logo)
        layout.addWidget(name)
        layout.addSpacing(16)
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
        Animation is centered with generous padding.
        """
        frame = QFrame()
        frame.setObjectName("animationArea")
        frame.setStyleSheet("QFrame#animationArea { background-color: #08080f; }")

        layout = QVBoxLayout(frame)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(12)

        # AnimationWidget — full Lottie rendering
        self.animation_widget = AnimationWidget()
        self.animation_widget.setFixedSize(320, 320)

        # Hint text
        hint = QLabel('Say  "Hey Maki"  to wake me up')
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hint.setStyleSheet("""
            color: #1e1e3a;
            font-size: 11px;
            letter-spacing: 2px;
        """)

        layout.addStretch()
        layout.addWidget(self.animation_widget, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(hint, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addStretch()

        return frame

    def _build_divider(self) -> QFrame:
        """Thin vertical divider between animation and chat log."""
        divider = QFrame()
        divider.setFixedWidth(1)
        divider.setStyleSheet("background-color: #1e1e3a;")
        return divider

    def _build_chat_log(self) -> QFrame:
        """Right panel — scrollable conversation history."""
        panel = QFrame()
        panel.setObjectName("chatPanel")
        panel.setStyleSheet("""
            QFrame#chatPanel {
                background-color: #0a0a12;
            }
        """)

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header
        header = QLabel("  CONVERSATION")
        header.setFixedHeight(44)
        header.setStyleSheet("""
            color: #2a2a5a;
            font-size: 10px;
            letter-spacing: 3px;
            font-weight: bold;
            border-bottom: 1px solid #12122a;
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
                background: #0a0a12;
                width: 4px;
                border-radius: 2px;
            }
            QScrollBar::handle:vertical {
                background: #1e1e3a;
                border-radius: 2px;
            }
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical { height: 0px; }
        """)

        self.chat_container = QWidget()
        self.chat_layout = QVBoxLayout(self.chat_container)
        self.chat_layout.setContentsMargins(16, 16, 16, 24)
        self.chat_layout.setSpacing(10)
        self.chat_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Empty state
        self.empty_chat_label = QLabel("No conversation yet.\nSay 'Hey Maki' to begin.")
        self.empty_chat_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_chat_label.setStyleSheet("""
            color: #1e1e3a;
            font-size: 12px;
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
        bar.setFixedHeight(68)
        bar.setObjectName("transcriptionBar")
        bar.setStyleSheet("""
            QFrame#transcriptionBar {
                background-color: #08080f;
                border-top: 1px solid #12122a;
            }
        """)

        layout = QHBoxLayout(bar)
        layout.setContentsMargins(24, 0, 24, 0)
        layout.setSpacing(12)

        # Mic icon
        mic_icon = QLabel("🎙")
        mic_icon.setFixedSize(28, 28)
        mic_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        mic_icon.setStyleSheet("font-size: 16px;")

        # Text input
        self.transcription_input = QLineEdit()
        self.transcription_input.setPlaceholderText(
            'Type a command or say "Hey Maki" ...'
        )
        self.transcription_input.setFixedHeight(42)
        self.transcription_input.setStyleSheet("""
            QLineEdit {
                background-color: #10101e;
                color: #c0c0d0;
                border: 1px solid #1a1a32;
                border-radius: 21px;
                padding: 0 20px;
                font-size: 13px;
            }
            QLineEdit:focus {
                border: 1px solid #00d4ff;
                background-color: #12122a;
                color: #e0e0f0;
            }
            QLineEdit::placeholder {
                color: #2a2a4a;
            }
        """)
        self.transcription_input.returnPressed.connect(self._handle_text_command)

        # Send button
        send_btn = QPushButton("➤")
        send_btn.setFixedSize(42, 42)
        send_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        send_btn.setStyleSheet("""
            QPushButton {
                background-color: #00d4ff;
                color: #08080f;
                border: none;
                border-radius: 21px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #00bcee; }
            QPushButton:pressed { background-color: #00a0cc; }
        """)
        send_btn.clicked.connect(self._handle_text_command)

        layout.addWidget(mic_icon)
        layout.addWidget(self.transcription_input, stretch=1)
        layout.addWidget(send_btn)

        return bar

    # ─── State Updates ────────────────────────────────────────────────────────

    @pyqtSlot(object)
    def _on_state_change(self, new_state: AppState) -> None:
        """
        Called by StateManager whenever the app state changes.
        AnimationWidget handles its own rendering.
        StatusIndicator handles its own badge update.
        This hook is kept for any future MainPage-level state reactions.
        """
        pass  # AnimationWidget and StatusIndicator handle their own updates

    def update_transcription(self, text: str) -> None:
        """
        Display live transcription text in the input bar.
        Called by the STT service during Phase 2.

        Args:
            text: The transcribed text string.
        """
        self.transcription_input.setText(text)

    # ─── Chat Log ─────────────────────────────────────────────────────────────

    def add_message(self, role: str, text: str) -> None:
        """
        Append a message to the conversation log.

        Args:
            role: 'user' or 'maki'
            text: The message content.
        """
        # Remove empty state label on first message
        if self.empty_chat_label.isVisible():
            self.empty_chat_label.setVisible(False)

        bubble = self._make_bubble(role, text)
        self.chat_layout.addWidget(bubble)

        # Auto-scroll to bottom
        self._chat_scroll.verticalScrollBar().setValue(
            self._chat_scroll.verticalScrollBar().maximum()
        )

    def _make_bubble(self, role: str, text: str) -> QFrame:
        """Create a chat bubble widget for user or Maki messages."""
        import re
        # Clean markdown for display too
        display_text = re.sub(r'\*{1,3}(.*?)\*{1,3}', r'\1', text)
        display_text = re.sub(r'`([^`]+)`', r'\1', display_text)

        bubble = QFrame()
        layout = QVBoxLayout(bubble)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(4)

        role_label = QLabel("You" if role == "user" else "Maki")
        role_label.setStyleSheet(
            f"color: {'#00d4ff' if role == 'maki' else '#6b7280'}; "
            f"font-size: 11px; font-weight: bold; letter-spacing: 1px;"
        )

        msg_label = QLabel(display_text)
        msg_label.setWordWrap(True)
        msg_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        msg_label.setStyleSheet("color: #e0e0e0; font-size: 13px; line-height: 1.6; border: none;")
        msg_label.setMinimumWidth(200)
        msg_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        layout.addWidget(role_label)
        layout.addWidget(msg_label)

        bubble.setStyleSheet(f"""
            QFrame {{
                background-color: {'#0d1a2e' if role == 'maki' else '#1a1a2e'};
                border-radius: 10px;
                border-left: 2px solid {'#00d4ff' if role == 'maki' else '#2a2a4a'};
            }}
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

        # Run in a thread so the GUI doesn't freeze during Gemini call
        import threading
        def run():
            response = self.orchestrator.handle_command(text)
            if response:
                # Update chat log on main thread
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
        """
        Show a low-confidence transcription confirmation prompt.
        Displays the heard text and asks Mark to confirm or correct it.

        Args:
            text: The low-confidence transcription to confirm.
        """
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
        """
        Called when MainPage becomes the active page.
        Greet the user and set focus to the input bar.
        """
        self.add_message("maki", f"Hello sir. I'm online and ready. Say \"Hey Maki\" or type a command below.")
        self.transcription_input.setFocus()
