"""
MakiAI — State Manager
Manages the app's current state: IDLE, LISTENING, THINKING, SPEAKING.
Notifies listeners (GUI, orchestrator) whenever state changes.
"""

from enum import Enum
from typing import Callable


class AppState(Enum):
    IDLE = "idle"
    LISTENING = "listening"
    THINKING = "thinking"
    SPEAKING = "speaking"


class StateManager:
    """
    Central state machine for MakiAI.
    Holds the current app state and fires callbacks on every transition.
    """

    def __init__(self):
        self._state: AppState = AppState.IDLE
        self._listeners: list[Callable[[AppState], None]] = []

    @property
    def state(self) -> AppState:
        """Return the current app state."""
        return self._state

    def set_state(self, new_state: AppState) -> None:
        """
        Transition to a new state and notify all listeners.

        Args:
            new_state: The AppState to transition to.
        """
        if new_state == self._state:
            return

        previous = self._state
        self._state = new_state
        print(f"[StateManager] {previous.value} -> {new_state.value}")
        self._notify(new_state)

    def on_state_change(self, callback: Callable[[AppState], None]) -> None:
        """
        Register a callback to be called whenever the state changes.

        Args:
            callback: A function that receives the new AppState.
        """
        self._listeners.append(callback)

    def remove_listener(self, callback: Callable[[AppState], None]) -> None:
        """
        Unregister a previously registered callback.

        Args:
            callback: The callback to remove.
        """
        if callback in self._listeners:
            self._listeners.remove(callback)

    def _notify(self, new_state: AppState) -> None:
        """Fire all registered callbacks with the new state."""
        for listener in self._listeners:
            try:
                listener(new_state)
            except Exception as e:
                print(f"[StateManager] Listener error: {e}")

    def is_idle(self) -> bool:
        return self._state == AppState.IDLE

    def is_listening(self) -> bool:
        return self._state == AppState.LISTENING

    def is_thinking(self) -> bool:
        return self._state == AppState.THINKING

    def is_speaking(self) -> bool:
        return self._state == AppState.SPEAKING

    def reset(self) -> None:
        """Force reset back to IDLE."""
        self.set_state(AppState.IDLE)
