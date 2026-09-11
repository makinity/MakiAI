"""
MakiAI — Settings Page
Full settings UI — API keys, voice ID, wake word, toggles.
All changes apply immediately without restarting the app.

Sections:
  - AI Provider (Groq key, Gemini key)
  - Voice Output (ElevenLabs key, voice ID)
  - Voice Input (wake word)
  - Preferences (TTS fallback, always-on listening, show transcription)
  - Export conversation log
  - Logout
"""

import json
from pathlib import Path
from typing import Callable

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QLineEdit, QFrame, QScrollArea,
    QCheckBox, QSizePolicy, QSpacerItem, QFileDialog,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

from services.settings.settings_service import SettingsService


class SettingsPage(QWidget):
    """
    Settings page for MakiAI.
    Allows changing all config without editing .env manually.
    Changes apply immediately — hot-swapped into running services.
    """

    # Emitted when settings are saved — MainWindow reconnects services
    settings_saved = pyqtSignal(dict)

    def __init__(
        self,
        settings: SettingsService,
        on_back: Callable[[], None],
        on_logout: Callable[[], None],
    ):
        super().__init__()
        self.settings = settings
        self.on_back = on_back
        self.on_logout = on_logout

        self._build_ui()
        self._load_current_values()

    # ─── UI Build ─────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._build_top_bar())

        # Scrollable content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("""
            QScrollArea { border: none; background: #0a0a0f; }
            QWidget { background: #0a0a0f; }
            QScrollBar:vertical {
                background: #0a0a0f; width: 4px; border-radius: 2px;
            }
            QScrollBar::handle:vertical {
                background: #1e1e3a; border-radius: 2px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
        """)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(40, 32, 40, 40)
        content_layout.setSpacing(24)
        content_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Page title
        title = QLabel("Settings")
        title.setStyleSheet("color: #ffffff; font-size: 22px; font-weight: bold; letter-spacing: 2px;")
        content_layout.addWidget(title)

        subtitle = QLabel("Changes apply immediately — no restart needed.")
        subtitle.setStyleSheet("color: #4a4a6a; font-size: 12px; margin-bottom: 8px;")
        content_layout.addWidget(subtitle)

        # ── Sections ──────────────────────────────────────────────────────────
        content_layout.addWidget(self._build_section(
            "🤖  AI Provider",
            [
                ("Groq API Key", "GROQ_API_KEY", "gsk_...", True),
                ("Gemini API Key (fallback)", "GEMINI_API_KEY", "AQ... or AIza...", True),
            ]
        ))

        content_layout.addWidget(self._build_section(
            "🔊  Voice Output (ElevenLabs)",
            [
                ("ElevenLabs API Key", "ELEVENLABS_API_KEY", "sk_...", True),
                ("Voice ID", "ELEVENLABS_VOICE_ID", "e.g. pNInz6obpgDQGcFmaJgB", False),
            ]
        ))

        content_layout.addWidget(self._build_section(
            "🎙️  Voice Input",
            [
                ("Wake Word", "WAKE_WORD", "e.g. Hey Maki", False),
            ]
        ))

        content_layout.addWidget(self._build_section(
            "📁  Paths",
            [
                ("Knowledge Base Path", "KB_PATH", r"C:\Knowledge-Base", False),
            ]
        ))

        content_layout.addWidget(self._build_toggles_section())
        content_layout.addWidget(self._build_export_section())
        content_layout.addWidget(self._build_danger_section())

        scroll.setWidget(content)
        root.addWidget(scroll, stretch=1)

        # Save button bar
        root.addWidget(self._build_save_bar())

    def _build_top_bar(self) -> QFrame:
        bar = QFrame()
        bar.setFixedHeight(52)
        bar.setObjectName("settingsTopBar")
        bar.setStyleSheet("""
            QFrame#settingsTopBar {
                background-color: #0d0d1a;
                border-bottom: 1px solid #1e1e3a;
            }
        """)

        layout = QHBoxLayout(bar)
        layout.setContentsMargins(20, 0, 16, 0)

        back_btn = QPushButton("← Back")
        back_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        back_btn.setFixedHeight(32)
        back_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #00d4ff;
                border: 1px solid #1e1e3a;
                border-radius: 6px;
                padding: 0 16px;
                font-size: 13px;
            }
            QPushButton:hover { border-color: #00d4ff; }
        """)
        back_btn.clicked.connect(self.on_back)

        title = QLabel("⚙  Settings")
        title.setStyleSheet("color: #ffffff; font-size: 14px; font-weight: bold; letter-spacing: 2px;")

        spacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        layout.addWidget(back_btn)
        layout.addSpacing(16)
        layout.addWidget(title)
        layout.addItem(spacer)

        return bar

    def _build_section(self, title: str, fields: list[tuple]) -> QFrame:
        """
        Build a settings section with labeled input fields.

        Args:
            title:  Section header text.
            fields: List of (label, env_key, placeholder, is_password) tuples.
        """
        section = QFrame()
        section.setStyleSheet("""
            QFrame {
                background-color: #0d0d1a;
                border: 1px solid #1a1a2e;
                border-radius: 10px;
            }
        """)

        layout = QVBoxLayout(section)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        # Section title
        title_label = QLabel(title)
        title_label.setStyleSheet("color: #00d4ff; font-size: 13px; font-weight: bold; letter-spacing: 1px; border: none;")
        layout.addWidget(title_label)

        # Divider
        divider = QFrame()
        divider.setFixedHeight(1)
        divider.setStyleSheet("background-color: #1a1a2e; border: none;")
        layout.addWidget(divider)

        # Fields
        for label_text, env_key, placeholder, is_password in fields:
            row = QVBoxLayout()
            row.setSpacing(6)

            label = QLabel(label_text)
            label.setStyleSheet("color: #8888aa; font-size: 12px; border: none;")

            field = QLineEdit()
            field.setPlaceholderText(placeholder)
            field.setFixedHeight(42)
            field.setObjectName(env_key)  # Store env key as object name
            if is_password:
                field.setEchoMode(QLineEdit.EchoMode.Password)

            # Show/hide toggle for password fields
            if is_password:
                field_row = QHBoxLayout()
                field_row.setSpacing(8)
                field.setStyleSheet(self._input_style())

                show_btn = QPushButton("👁")
                show_btn.setFixedSize(42, 42)
                show_btn.setCursor(Qt.CursorShape.PointingHandCursor)
                show_btn.setCheckable(True)
                show_btn.setStyleSheet("""
                    QPushButton {
                        background: #1a1a2e; color: #4a4a6a;
                        border: 1px solid #2a2a4a; border-radius: 6px;
                        font-size: 16px;
                    }
                    QPushButton:hover { color: #ffffff; }
                    QPushButton:checked { color: #00d4ff; }
                """)
                show_btn.clicked.connect(lambda checked, f=field: f.setEchoMode(
                    QLineEdit.EchoMode.Normal if checked else QLineEdit.EchoMode.Password
                ))

                field_row.addWidget(field)
                field_row.addWidget(show_btn)

                row.addWidget(label)
                row.addLayout(field_row)
            else:
                field.setStyleSheet(self._input_style())
                row.addWidget(label)
                row.addWidget(field)

            layout.addLayout(row)

        return section

    def _build_toggles_section(self) -> QFrame:
        """Build the toggles/preferences section."""
        section = QFrame()
        section.setStyleSheet("""
            QFrame {
                background-color: #0d0d1a;
                border: 1px solid #1a1a2e;
                border-radius: 10px;
            }
        """)

        layout = QVBoxLayout(section)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        title = QLabel("⚙️  Preferences")
        title.setStyleSheet("color: #00d4ff; font-size: 13px; font-weight: bold; letter-spacing: 1px; border: none;")
        layout.addWidget(title)

        divider = QFrame()
        divider.setFixedHeight(1)
        divider.setStyleSheet("background-color: #1a1a2e; border: none;")
        layout.addWidget(divider)

        toggles = [
            ("tts_fallback",        "Use Edge TTS as fallback when ElevenLabs quota runs out"),
            ("always_on_listening", "Always-on voice listening (requires wake word)"),
            ("show_transcription",  "Show real-time transcription in the input bar"),
        ]

        self._toggles: dict[str, QCheckBox] = {}
        for key, description in toggles:
            cb = QCheckBox(description)
            cb.setObjectName(key)
            cb.setStyleSheet("""
                QCheckBox {
                    color: #c0c0d0;
                    font-size: 13px;
                    border: none;
                    spacing: 10px;
                }
                QCheckBox::indicator {
                    width: 18px; height: 18px;
                    border: 1px solid #2a2a4a;
                    border-radius: 4px;
                    background: #1a1a2e;
                }
                QCheckBox::indicator:checked {
                    background: #00d4ff;
                    border-color: #00d4ff;
                }
                QCheckBox:hover { color: #ffffff; }
            """)
            self._toggles[key] = cb
            layout.addWidget(cb)

        return section

    def _build_export_section(self) -> QFrame:
        """Build the export conversation log section."""
        section = QFrame()
        section.setStyleSheet("""
            QFrame {
                background-color: #0d0d1a;
                border: 1px solid #1a1a2e;
                border-radius: 10px;
            }
        """)

        layout = QVBoxLayout(section)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        title = QLabel("📋  Conversation Log")
        title.setStyleSheet("color: #00d4ff; font-size: 13px; font-weight: bold; letter-spacing: 1px; border: none;")

        desc = QLabel("Export your full conversation history to a text or markdown file.")
        desc.setStyleSheet("color: #6b7280; font-size: 12px; border: none;")
        desc.setWordWrap(True)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        export_txt_btn = QPushButton("Export as .txt")
        export_md_btn = QPushButton("Export as .md")

        for btn in [export_txt_btn, export_md_btn]:
            btn.setFixedHeight(38)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet("""
                QPushButton {
                    background: #1a1a2e;
                    color: #c0c0d0;
                    border: 1px solid #2a2a4a;
                    border-radius: 6px;
                    padding: 0 16px;
                    font-size: 12px;
                }
                QPushButton:hover { color: #ffffff; border-color: #00d4ff; }
            """)

        export_txt_btn.clicked.connect(lambda: self._export_log("txt"))
        export_md_btn.clicked.connect(lambda: self._export_log("md"))

        self._export_status = QLabel("")
        self._export_status.setStyleSheet("color: #00ff88; font-size: 12px; border: none;")

        btn_row.addWidget(export_txt_btn)
        btn_row.addWidget(export_md_btn)
        btn_row.addStretch()

        layout.addWidget(title)
        layout.addWidget(desc)
        layout.addLayout(btn_row)
        layout.addWidget(self._export_status)

        return section

    def _build_danger_section(self) -> QFrame:
        """Build the danger zone section (logout)."""
        section = QFrame()
        section.setStyleSheet("""
            QFrame {
                background-color: #0d0d1a;
                border: 1px solid #2a1a1a;
                border-radius: 10px;
            }
        """)

        layout = QHBoxLayout(section)
        layout.setContentsMargins(24, 16, 24, 16)

        label = QLabel("Log out of MakiAI")
        label.setStyleSheet("color: #6b7280; font-size: 13px; border: none;")

        logout_btn = QPushButton("↩  Logout")
        logout_btn.setFixedHeight(38)
        logout_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        logout_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #ef4444;
                border: 1px solid #ef4444;
                border-radius: 6px;
                padding: 0 20px;
                font-size: 13px;
            }
            QPushButton:hover { background: #ef4444; color: #ffffff; }
        """)
        logout_btn.clicked.connect(self.on_logout)

        layout.addWidget(label, stretch=1)
        layout.addWidget(logout_btn)

        return section

    def _build_save_bar(self) -> QFrame:
        """Bottom save bar."""
        bar = QFrame()
        bar.setFixedHeight(64)
        bar.setObjectName("saveBar")
        bar.setStyleSheet("""
            QFrame#saveBar {
                background-color: #0d0d1a;
                border-top: 1px solid #1e1e3a;
            }
        """)

        layout = QHBoxLayout(bar)
        layout.setContentsMargins(40, 0, 40, 0)

        self._save_status = QLabel("")
        self._save_status.setStyleSheet("color: #00ff88; font-size: 12px;")

        spacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        save_btn = QPushButton("Save Settings")
        save_btn.setFixedSize(160, 42)
        save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #00d4ff;
                color: #0a0a0f;
                border: none;
                border-radius: 8px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #00bcee; }
            QPushButton:pressed { background-color: #00a0cc; }
        """)
        save_btn.clicked.connect(self._save)

        layout.addWidget(self._save_status)
        layout.addItem(spacer)
        layout.addWidget(save_btn)

        return bar

    # ─── Load / Save ──────────────────────────────────────────────────────────

    def _load_current_values(self) -> None:
        """Populate all fields with current values from settings."""
        # ENV fields — find by objectName
        env_keys = [
            "GROQ_API_KEY", "GEMINI_API_KEY",
            "ELEVENLABS_API_KEY", "ELEVENLABS_VOICE_ID",
            "WAKE_WORD", "KB_PATH",
        ]
        for key in env_keys:
            field = self.findChild(QLineEdit, key)
            if field:
                field.setText(self.settings.get_env(key))

        # Toggles
        for key, cb in self._toggles.items():
            cb.setChecked(bool(self.settings.get(key, True)))

    def _save(self) -> None:
        """Save all settings and emit settings_saved signal."""
        changed = {}

        # Save ENV fields
        env_keys = [
            "GROQ_API_KEY", "GEMINI_API_KEY",
            "ELEVENLABS_API_KEY", "ELEVENLABS_VOICE_ID",
            "WAKE_WORD", "KB_PATH",
        ]
        for key in env_keys:
            field = self.findChild(QLineEdit, key)
            if field:
                value = field.text().strip()
                if value:
                    self.settings.set_env(key, value)
                    changed[key] = value

        # Save toggles
        for key, cb in self._toggles.items():
            self.settings.set(key, cb.isChecked())
            changed[key] = cb.isChecked()

        self._save_status.setText("✓ Settings saved successfully.")
        print(f"[SettingsPage] Saved: {list(changed.keys())}")

        # Notify MainWindow to hot-swap services
        self.settings_saved.emit(changed)

    # ─── Export ───────────────────────────────────────────────────────────────

    def _export_log(self, fmt: str) -> None:
        """Export conversation log to .txt or .md file."""
        log_file = Path(__file__).resolve().parents[2] / "data" / "logs" / "conversation_log.json"

        if not log_file.exists():
            self._export_status.setText("No conversation log found.")
            return

        try:
            data = json.loads(log_file.read_text(encoding="utf-8"))
            sessions = data.get("sessions", [])

            if not sessions:
                self._export_status.setText("Conversation log is empty.")
                return

            # Build export content
            lines = []
            if fmt == "md":
                lines.append("# MakiAI Conversation Log\n")
            else:
                lines.append("MakiAI Conversation Log\n" + "=" * 40 + "\n")

            for session in sessions:
                date = session.get("date", "Unknown date")
                lines.append(f"\n{'## ' if fmt == 'md' else '--- '}Session: {date}\n")
                for msg in session.get("messages", []):
                    role = "You" if msg.get("role") == "user" else "Maki"
                    text = msg.get("text", "")
                    ts = msg.get("timestamp", "")[:16].replace("T", " ")
                    if fmt == "md":
                        lines.append(f"**{role}** _{ts}_\n{text}\n")
                    else:
                        lines.append(f"[{ts}] {role}: {text}\n")

            content = "\n".join(lines)

            # Ask user where to save
            default_name = f"maki_conversation.{fmt}"
            path, _ = QFileDialog.getSaveFileName(
                self,
                "Export Conversation Log",
                str(Path.home() / "Documents" / default_name),
                f"{'Markdown' if fmt == 'md' else 'Text'} Files (*.{fmt})",
            )

            if path:
                Path(path).write_text(content, encoding="utf-8")
                self._export_status.setText(f"✓ Exported to {Path(path).name}")
                print(f"[SettingsPage] Log exported to: {path}")

        except Exception as e:
            self._export_status.setText(f"Export failed: {e}")
            print(f"[SettingsPage] Export error: {e}")

    # ─── Styles ───────────────────────────────────────────────────────────────

    def _input_style(self) -> str:
        return """
            QLineEdit {
                background-color: #1a1a2e;
                color: #e0e0e0;
                border: 1px solid #2a2a4a;
                border-radius: 8px;
                padding: 0 16px;
                font-size: 13px;
            }
            QLineEdit:focus {
                border: 1px solid #00d4ff;
                background-color: #1e1e38;
            }
        """
