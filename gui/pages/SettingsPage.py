"""
MakiAI — Settings Page
Full settings UI — API keys, voice ID, wake word, toggles.
All changes apply immediately without restarting the app.
Follows MakiSync brand colors and dark glassmorphic styling.

Sections:
  - AI Provider (Groq key, Gemini key)
  - Voice Output (ElevenLabs key, voice ID)
  - Voice Input (wake word)
  - Paths (Knowledge Base Path)
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
            QScrollArea { border: none; background: #0a0f1a; }
            QWidget { background: #0a0f1a; }
            QScrollBar:vertical {
                background: #0a0f1a; width: 5px; border-radius: 2px;
            }
            QScrollBar::handle:vertical {
                background: #1e293b; border-radius: 2px;
            }
            QScrollBar::handle:vertical:hover {
                background: #3b82f6;
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
        title.setStyleSheet("color: #ffffff; font-size: 22px; font-weight: bold; letter-spacing: 1px;")
        content_layout.addWidget(title)

        subtitle = QLabel("Changes apply immediately — no restart needed.")
        subtitle.setStyleSheet("color: #64748b; font-size: 12px; margin-bottom: 8px;")
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
        bar.setFixedHeight(54)
        bar.setObjectName("settingsTopBar")
        bar.setStyleSheet("""
            QFrame#settingsTopBar {
                background-color: #0d1527;
                border-bottom: 1px solid rgba(140, 171, 214, 0.12);
            }
        """)

        layout = QHBoxLayout(bar)
        layout.setContentsMargins(20, 0, 16, 0)

        back_btn = QPushButton("← Back")
        back_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        back_btn.setFixedHeight(32)
        back_btn.setStyleSheet("""
            QPushButton {
                background: rgba(16, 23, 38, 0.7);
                color: #38bdf8;
                border: 1px solid rgba(56, 189, 248, 0.3);
                border-radius: 6px;
                padding: 0 16px;
                font-size: 12px;
                font-weight: 600;
            }
            QPushButton:hover {
                border-color: #38bdf8;
                background: rgba(56, 189, 248, 0.12);
                color: #ffffff;
            }
        """)
        back_btn.clicked.connect(self.on_back)

        title = QLabel("⚙  Settings")
        title.setStyleSheet("color: #f8fafc; font-size: 14px; font-weight: 700; letter-spacing: 1px;")

        spacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        layout.addWidget(back_btn)
        layout.addSpacing(16)
        layout.addWidget(title)
        layout.addItem(spacer)

        return bar

    def _build_section(self, title: str, fields: list[tuple]) -> QFrame:
        """
        Build a settings section with labeled input fields.
        """
        section = QFrame()
        section.setStyleSheet("""
            QFrame {
                background-color: #0d1527;
                border: 1px solid rgba(140, 171, 214, 0.14);
                border-radius: 12px;
            }
        """)

        layout = QVBoxLayout(section)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        # Section title
        title_label = QLabel(title)
        title_label.setStyleSheet("color: #38bdf8; font-size: 13px; font-weight: 700; letter-spacing: 0.5px; border: none;")
        layout.addWidget(title_label)

        # Divider
        divider = QFrame()
        divider.setFixedHeight(1)
        divider.setStyleSheet("background-color: rgba(140, 171, 214, 0.10); border: none;")
        layout.addWidget(divider)

        # Fields
        for label_text, env_key, placeholder, is_password in fields:
            row = QVBoxLayout()
            row.setSpacing(6)

            label = QLabel(label_text)
            label.setStyleSheet("color: #94a3b8; font-size: 12px; font-weight: 500; border: none;")

            field = QLineEdit()
            field.setPlaceholderText(placeholder)
            field.setFixedHeight(42)
            field.setObjectName(env_key)
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
                        background: #101726; color: #64748b;
                        border: 1px solid rgba(140, 171, 214, 0.18); border-radius: 8px;
                        font-size: 16px;
                    }
                    QPushButton:hover { color: #f8fafc; border-color: #3b82f6; }
                    QPushButton:checked { color: #38bdf8; border-color: #38bdf8; }
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
                background-color: #0d1527;
                border: 1px solid rgba(140, 171, 214, 0.14);
                border-radius: 12px;
            }
        """)

        layout = QVBoxLayout(section)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        title = QLabel("⚙️  Preferences")
        title.setStyleSheet("color: #38bdf8; font-size: 13px; font-weight: 700; letter-spacing: 0.5px; border: none;")
        layout.addWidget(title)

        divider = QFrame()
        divider.setFixedHeight(1)
        divider.setStyleSheet("background-color: rgba(140, 171, 214, 0.10); border: none;")
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
                    color: #cbd5e1;
                    font-size: 13px;
                    border: none;
                    spacing: 12px;
                }
                QCheckBox::indicator {
                    width: 18px; height: 18px;
                    border: 1px solid rgba(140, 171, 214, 0.25);
                    border-radius: 4px;
                    background: #101726;
                }
                QCheckBox::indicator:checked {
                    background: #3b82f6;
                    border-color: #3b82f6;
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
                background-color: #0d1527;
                border: 1px solid rgba(140, 171, 214, 0.14);
                border-radius: 12px;
            }
        """)

        layout = QVBoxLayout(section)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        title = QLabel("📋  Conversation Log")
        title.setStyleSheet("color: #38bdf8; font-size: 13px; font-weight: 700; letter-spacing: 0.5px; border: none;")

        desc = QLabel("Export your full conversation history to a text or markdown file.")
        desc.setStyleSheet("color: #94a3b8; font-size: 12px; border: none;")
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
                    background: rgba(16, 23, 38, 0.7);
                    color: #cbd5e1;
                    border: 1px solid rgba(140, 171, 214, 0.18);
                    border-radius: 6px;
                    padding: 0 16px;
                    font-size: 12px;
                    font-weight: 500;
                }
                QPushButton:hover { color: #ffffff; border-color: #3b82f6; background: rgba(59, 130, 246, 0.12); }
            """)

        export_txt_btn.clicked.connect(lambda: self._export_log("txt"))
        export_md_btn.clicked.connect(lambda: self._export_log("md"))

        self._export_status = QLabel("")
        self._export_status.setStyleSheet("color: #38bdf8; font-size: 12px; border: none; font-weight: 500;")

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
                background-color: #0d1527;
                border: 1px solid rgba(239, 68, 68, 0.2);
                border-radius: 12px;
            }
        """)

        layout = QHBoxLayout(section)
        layout.setContentsMargins(24, 16, 24, 16)

        label = QLabel("Log out of MakiAI")
        label.setStyleSheet("color: #94a3b8; font-size: 13px; border: none;")

        logout_btn = QPushButton("↩  Logout")
        logout_btn.setFixedHeight(38)
        logout_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        logout_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #ef4444;
                border: 1px solid rgba(239, 68, 68, 0.5);
                border-radius: 6px;
                padding: 0 20px;
                font-size: 13px;
                font-weight: 600;
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
        bar.setFixedHeight(68)
        bar.setObjectName("saveBar")
        bar.setStyleSheet("""
            QFrame#saveBar {
                background-color: #0d1527;
                border-top: 1px solid rgba(140, 171, 214, 0.12);
            }
        """)

        layout = QHBoxLayout(bar)
        layout.setContentsMargins(40, 0, 40, 0)

        self._save_status = QLabel("")
        self._save_status.setStyleSheet("color: #38bdf8; font-size: 12px; font-weight: 500;")

        spacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        save_btn = QPushButton("Save Settings")
        save_btn.setFixedSize(160, 44)
        save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        save_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #2563eb, stop:1 #3b82f6);
                color: #ffffff;
                border: none;
                border-radius: 8px;
                font-size: 14px;
                font-weight: 700;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #3b82f6, stop:1 #60a5fa);
            }
            QPushButton:pressed {
                background: #1d4ed8;
            }
        """)
        save_btn.clicked.connect(self._save)

        layout.addWidget(self._save_status)
        layout.addItem(spacer)
        layout.addWidget(save_btn)

        return bar

    # ─── Load / Save ──────────────────────────────────────────────────────────

    def _load_current_values(self) -> None:
        """Populate all fields with current values from settings."""
        env_keys = [
            "GROQ_API_KEY", "GEMINI_API_KEY",
            "ELEVENLABS_API_KEY", "ELEVENLABS_VOICE_ID",
            "WAKE_WORD", "KB_PATH",
        ]
        for key in env_keys:
            field = self.findChild(QLineEdit, key)
            if field:
                field.setText(self.settings.get_env(key))

        for key, cb in self._toggles.items():
            cb.setChecked(bool(self.settings.get(key, True)))

    def _save(self) -> None:
        """Save all settings and emit settings_saved signal."""
        changed = {}

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

        for key, cb in self._toggles.items():
            self.settings.set(key, cb.isChecked())
            changed[key] = cb.isChecked()

        self._save_status.setText("✓ Settings saved successfully.")
        print(f"[SettingsPage] Saved: {list(changed.keys())}")

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
                background-color: #101726;
                color: #f8fafc;
                border: 1px solid rgba(140, 171, 214, 0.18);
                border-radius: 8px;
                padding: 0 16px;
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
        """
