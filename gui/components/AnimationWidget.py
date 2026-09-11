"""
MakiAI — Animation Widget
State-driven Lottie animation display for the MainPage center stage.

Renders Lottie JSON animations using rlottie-python.
Falls back to the painted pulsing circles if:
  - rlottie-python is not installed
  - The Lottie JSON file is missing or invalid

To swap in a real animation from 21st.dev:
  1. Download the Lottie JSON file
  2. Replace the matching file in gui/assets/animations/
  3. Restart — no code changes needed

Animation files:
  gui/assets/animations/idle.json      → IDLE state
  gui/assets/animations/listening.json → LISTENING state
  gui/assets/animations/thinking.json  → THINKING state
  gui/assets/animations/speaking.json  → SPEAKING state
"""

from pathlib import Path

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt6.QtCore import Qt, QTimer, QSize, pyqtSlot
from PyQt6.QtGui import QPainter, QColor, QRadialGradient, QPen, QBrush, QImage, QPixmap

from core.state_manager import AppState


# Paths to Lottie animation files
ANIMATION_DIR = Path(__file__).resolve().parents[1] / "assets" / "animations"

ANIMATION_FILES = {
    AppState.IDLE:      ANIMATION_DIR / "idle.json",
    AppState.LISTENING: ANIMATION_DIR / "listening.json",
    AppState.THINKING:  ANIMATION_DIR / "thinking.json",
    AppState.SPEAKING:  ANIMATION_DIR / "speaking.json",
}

# Fallback painted circle config per state (used when Lottie unavailable)
FALLBACK_CONFIG = {
    AppState.IDLE: {
        "color":       QColor(0, 212, 255, 40),
        "ring_color":  QColor(0, 212, 255, 80),
        "pulse_speed": 2000,
        "label":       "IDLE",
        "label_color": "#2a2a5a",
        "symbol":      "◈",
        "symbol_color":"#1e3a4a",
    },
    AppState.LISTENING: {
        "color":       QColor(0, 255, 136, 60),
        "ring_color":  QColor(0, 255, 136, 120),
        "pulse_speed": 600,
        "label":       "LISTENING",
        "label_color": "#00ff88",
        "symbol":      "◉",
        "symbol_color":"#00ff88",
    },
    AppState.THINKING: {
        "color":       QColor(255, 204, 0, 50),
        "ring_color":  QColor(255, 204, 0, 100),
        "pulse_speed": 1000,
        "label":       "THINKING",
        "label_color": "#ffcc00",
        "symbol":      "⟳",
        "symbol_color":"#ffcc00",
    },
    AppState.SPEAKING: {
        "color":       QColor(0, 212, 255, 70),
        "ring_color":  QColor(0, 212, 255, 150),
        "pulse_speed": 400,
        "label":       "SPEAKING",
        "label_color": "#00d4ff",
        "symbol":      "◈",
        "symbol_color":"#00d4ff",
    },
}


class AnimationWidget(QWidget):
    """
    Lottie-powered animation widget for MakiAI's center stage HUD.

    Renders Lottie JSON animations via rlottie-python.
    Gracefully falls back to painted circles if rlottie is unavailable.

    Swapping animations: just replace the JSON files in gui/assets/animations/.

    Usage:
        widget = AnimationWidget()
        state_manager.on_state_change(widget.set_state)
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._state = AppState.IDLE
        self._pulse_scale = 1.0
        self._pulse_growing = True

        # Lottie state
        self._lottie_available = False
        self._lottie_players: dict[AppState, object] = {}
        self._current_frame = 0
        self._total_frames = 0
        self._current_pixmap = None

        self.setMinimumSize(280, 280)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, False)

        # Try loading rlottie
        self._lottie_available = self._init_lottie()

        # Animation timer
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(33)  # ~30fps

    # ─── Lottie Init ─────────────────────────────────────────────────────────

    def _init_lottie(self) -> bool:
        """
        Try to initialize rlottie-python and pre-load all animation files.

        Returns:
            True if rlottie is available and at least one animation loaded.
        """
        try:
            import rlottie_python as rlottie

            loaded = 0
            for state, path in ANIMATION_FILES.items():
                if path.exists():
                    try:
                        player = rlottie.LottieAnimation.from_file(str(path))
                        self._lottie_players[state] = player
                        loaded += 1
                        print(f"[AnimationWidget] Loaded Lottie: {path.name}")
                    except Exception as e:
                        print(f"[AnimationWidget] Failed to load {path.name}: {e}")
                else:
                    print(f"[AnimationWidget] Animation file not found: {path}")

            if loaded > 0:
                self._load_lottie_state(AppState.IDLE)
                print(f"[AnimationWidget] rlottie ready — {loaded}/4 animations loaded.")
                return True
            else:
                print("[AnimationWidget] No Lottie files loaded — using fallback.")
                return False

        except ImportError:
            print("[AnimationWidget] rlottie-python not installed — using fallback painter.")
            return False
        except Exception as e:
            print(f"[AnimationWidget] rlottie init error: {e} — using fallback.")
            return False

    def _load_lottie_state(self, state: AppState) -> None:
        """Load the Lottie player for the given state and reset frame counter."""
        player = self._lottie_players.get(state)
        if player:
            try:
                self._total_frames = player.lottie_animation_get_totalframe()
                self._current_frame = 0
            except Exception:
                self._total_frames = 60
                self._current_frame = 0

    # ─── Public API ──────────────────────────────────────────────────────────

    @pyqtSlot(object)
    def set_state(self, state: AppState) -> None:
        """
        Transition to a new animation state.

        Args:
            state: The new AppState to display.
        """
        if state == self._state:
            return
        self._state = state
        self._pulse_scale = 1.0
        self._current_frame = 0

        if self._lottie_available:
            self._load_lottie_state(state)

        self.update()

    # ─── Tick ────────────────────────────────────────────────────────────────

    def _tick(self) -> None:
        """Called every 33ms — advances animation frame."""
        try:
            if not self.isVisible():
                return
            if self._lottie_available:
                self._tick_lottie()
            else:
                self._tick_fallback()
        except RuntimeError:
            # Widget has been deleted — stop the timer
            self._timer.stop()

    def _tick_lottie(self) -> None:
        """Advance Lottie frame and render to pixmap."""
        player = self._lottie_players.get(self._state)
        if not player or self._total_frames == 0:
            return

        try:
            w, h = self.width(), self.height()
            if w <= 0 or h <= 0:
                return

            # Render current frame to RGBA buffer
            buffer = player.lottie_animation_render(
                self._current_frame, w, h
            )

            # Convert buffer to QPixmap
            image = QImage(
                bytes(buffer), w, h,
                QImage.Format.Format_RGBA8888
            )
            self._current_pixmap = QPixmap.fromImage(image)

            # Advance frame (loop)
            self._current_frame = (self._current_frame + 1) % self._total_frames
            self.update()

        except Exception as e:
            # Lottie render failed — switch to fallback
            print(f"[AnimationWidget] Lottie render error: {e} — switching to fallback.")
            self._lottie_available = False
            self.update()

    def _tick_fallback(self) -> None:
        """Advance fallback pulse animation."""
        config = FALLBACK_CONFIG.get(self._state, FALLBACK_CONFIG[AppState.IDLE])
        step = 30.0 / config["pulse_speed"] * 0.48

        if self._pulse_growing:
            self._pulse_scale += step
            if self._pulse_scale >= 1.12:
                self._pulse_growing = False
        else:
            self._pulse_scale -= step
            if self._pulse_scale <= 0.88:
                self._pulse_growing = True

        self.update()

    # ─── Paint ───────────────────────────────────────────────────────────────

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        if self._lottie_available and self._current_pixmap:
            self._paint_lottie(painter)
        else:
            self._paint_fallback(painter)

    def _paint_lottie(self, painter: QPainter) -> None:
        """Draw the current Lottie frame pixmap centered in the widget."""
        if self._current_pixmap:
            painter.drawPixmap(0, 0, self._current_pixmap)

    def _paint_fallback(self, painter: QPainter) -> None:
        """Draw the fallback pulsing circle."""
        config = FALLBACK_CONFIG.get(self._state, FALLBACK_CONFIG[AppState.IDLE])
        w, h = self.width(), self.height()
        cx, cy = w // 2, h // 2
        base_radius = min(w, h) // 3
        radius = int(base_radius * self._pulse_scale)

        # Outer ring
        ring_color = QColor(config["ring_color"])
        ring_color.setAlpha(int(80 * self._pulse_scale))
        painter.setPen(QPen(ring_color, 2))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        outer_r = int(radius * 1.4)
        painter.drawEllipse(cx - outer_r, cy - outer_r, outer_r * 2, outer_r * 2)

        # Radial fill
        gradient = QRadialGradient(cx, cy, radius)
        fill_color = QColor(config["color"])
        gradient.setColorAt(0.0, fill_color)
        edge = QColor(fill_color)
        edge.setAlpha(0)
        gradient.setColorAt(1.0, edge)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(gradient))
        painter.drawEllipse(cx - radius, cy - radius, radius * 2, radius * 2)

        # Symbol
        painter.setPen(QColor(config["symbol_color"]))
        f = painter.font()
        f.setPointSize(int(base_radius * 0.55))
        painter.setFont(f)
        painter.drawText(
            cx - base_radius, cy - base_radius,
            base_radius * 2, base_radius * 2,
            Qt.AlignmentFlag.AlignCenter,
            config["symbol"],
        )

        # State label
        painter.setPen(QColor(config["label_color"]))
        lf = painter.font()
        lf.setPointSize(9)
        painter.setFont(lf)
        painter.drawText(
            0, cy + base_radius + 16, w, 30,
            Qt.AlignmentFlag.AlignCenter,
            config["label"],
        )

