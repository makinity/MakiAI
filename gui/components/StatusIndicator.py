"""
MakiAI — Status Indicator
Small badge widget showing current app state in the top bar.
Updates automatically when StateManager fires a state change.
"""

from PyQt6.QtWidgets import QLabel
from PyQt6.QtCore import pyqtSlot

from core.state_manager import AppState


STATE_DISPLAY = {
    AppState.IDLE:      ("● Idle",        "#3a3a6a"),
    AppState.LISTENING: ("● Listening...", "#00ff88"),
    AppState.THINKING:  ("● Thinking...", "#ffcc00"),
    AppState.SPEAKING:  ("● Speaking...", "#00d4ff"),
}


class StatusIndicator(QLabel):
    """
    Top-bar status badge that reflects the current AppState.

    Usage:
        indicator = StatusIndicator()
        state_manager.on_state_change(indicator.set_state)
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.set_state(AppState.IDLE)
        self.setStyleSheet("font-size: 12px; padding: 0 4px;")

    @pyqtSlot(object)
    def set_state(self, state: AppState) -> None:
        """
        Update the badge text and color for the given state.

        Args:
            state: The new AppState.
        """
        text, color = STATE_DISPLAY.get(state, ("● Idle", "#3a3a6a"))
        self.setText(text)
        self.setStyleSheet(f"color: {color}; font-size: 12px; padding: 0 4px;")
