"""
MakiAI — Status Indicator
Small badge widget showing current app state in the top bar.
Follows MakiSync brand colors and modern pill styling.
Updates automatically when StateManager fires a state change.
"""

from PyQt6.QtWidgets import QLabel
from PyQt6.QtCore import pyqtSlot
from PyQt6.QtGui import QFont

from core.state_manager import AppState


STATE_DISPLAY = {
    AppState.IDLE:      ("● Idle",        "#94a3b8", "rgba(148, 163, 184, 0.10)", "rgba(148, 163, 184, 0.20)"),
    AppState.LISTENING: ("● Listening...", "#38bdf8", "rgba(56, 189, 248, 0.12)", "rgba(56, 189, 248, 0.35)"),
    AppState.THINKING:  ("● Thinking...", "#fbbf24", "rgba(251, 191, 36, 0.12)", "rgba(251, 191, 36, 0.35)"),
    AppState.SPEAKING:  ("● Speaking...", "#3b82f6", "rgba(59, 130, 246, 0.15)", "rgba(59, 130, 246, 0.40)"),
}


class StatusIndicator(QLabel):
    """
    Top-bar status badge that reflects the current AppState with a sleek pill shape.

    Usage:
        indicator = StatusIndicator()
        state_manager.on_state_change(indicator.set_state)
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(26)
        self.set_state(AppState.IDLE)

    @pyqtSlot(object)
    def set_state(self, state: AppState) -> None:
        """
        Update the badge text, color, and pill background for the given state.

        Args:
            state: The new AppState.
        """
        text, text_color, bg_color, border_color = STATE_DISPLAY.get(
            state, ("● Idle", "#94a3b8", "rgba(148, 163, 184, 0.10)", "rgba(148, 163, 184, 0.20)")
        )
        self.setText(f"  {text}  ")
        self.setStyleSheet(f"""
            QLabel {{
                color: {text_color};
                background-color: {bg_color};
                border: 1px solid {border_color};
                border-radius: 13px;
                font-size: 11px;
                font-weight: 600;
                letter-spacing: 0.5px;
                padding: 0 8px;
            }}
        """)
