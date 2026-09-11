"""
MakiAI — Animation Widget
State-driven Lottie animation display for the MainPage center stage.
Follows MakiSync brand colors and aesthetic glow effects.

Renders Lottie JSON animations using rlottie-python.
Falls back to high-fidelity painted pulsing circles if:
  - rlottie-python is not installed
  - The Lottie JSON file is missing or invalid

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

# Fallback painted circle config per state with MakiSync brand colors
FALLBACK_CONFIG = {
    AppState.IDLE: {
        "color":        QColor(59, 130, 246, 25),    # subtle #3b82f6 core
        "ring_color":   QColor(59, 130, 246, 60),
        "pulse_speed":  2200,
        "label":        "READY",
        "label_color":  "#64748b",
        "symbol":       "◈",
        "symbol_color": "#3b82f6",
    },
    AppState.LISTENING: {
        "color":        QColor(56, 189, 248, 45),    # vibrant cyan #38bdf8
        "ring_color":   QColor(56, 189, 248, 120),
        "pulse_speed":  700,
        "label":        "LISTENING",
        "label_color":  "#38bdf8",
        "symbol":       "◉",
        "symbol_color": "#38bdf8",
    },
    AppState.THINKING: {
        "color":        QColor(251, 191, 36, 40),    # warm amber #fbbf24
        "ring_color":   QColor(251, 191, 36, 110),
        "pulse_speed":  1100,
        "label":        "PROCESSING",
        "label_color":  "#fbbf24",
        "symbol":       "⟳",
        "symbol_color": "#fbbf24",
    },
    AppState.SPEAKING: {
        "color":        QColor(59, 130, 246, 65),    # electric blue #3b82f6
        "ring_color":   QColor(96, 165, 250, 160),   # #60a5fa glow
        "pulse_speed":  450,
        "label":        "SPEAKING",
        "label_color":  "#60a5fa",
        "symbol":       "◈",
        "symbol_color": "#93c5fd",
    },
}


class AnimationWidget(QWidget):
    """
    Lottie-powered animation widget for MakiAI's center stage HUD.

    Renders Lottie JSON animations via rlottie-python.
    Gracefully falls back to painted circles if rlottie is unavailable.
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
                    except Exception as e:
                        print(f"[AnimationWidget] Failed to load {path.name}: {e}")

            if loaded > 0:
                self._load_lottie_state(AppState.IDLE)
                print(f"[AnimationWidget] rlottie ready — {loaded}/4 animations loaded.")
                return True
            else:
                return False

        except ImportError:
            return False
        except Exception:
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
        """Transition to a new animation state."""
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
            self._timer.stop()
        except Exception:
            pass

    def _tick_lottie(self) -> None:
        """Advance Lottie frame and render to pixmap."""
        player = self._lottie_players.get(self._state)
        if not player or self._total_frames == 0:
            return

        try:
            w, h = self.width(), self.height()
            if w <= 0 or h <= 0:
                return

            buffer = player.lottie_animation_render(
                self._current_frame, w, h
            )

            image = QImage(
                bytes(buffer), w, h,
                QImage.Format.Format_RGBA8888
            )
            self._current_pixmap = QPixmap.fromImage(image)

            self._current_frame = (self._current_frame + 1) % self._total_frames
            self.update()

        except Exception as e:
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
        """Draw the fallback pulsing circle with MakiSync glow styling."""
        config = FALLBACK_CONFIG.get(self._state, FALLBACK_CONFIG[AppState.IDLE])
        w, h = self.width(), self.height()
        cx, cy = w // 2, h // 2
        base_radius = min(w, h) // 3
        radius = int(base_radius * self._pulse_scale)

        # Outer ambient ring
        ring_color = QColor(config["ring_color"])
        ring_color.setAlpha(int(60 * self._pulse_scale))
        painter.setPen(QPen(ring_color, 2))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        outer_r = int(radius * 1.35)
        painter.drawEllipse(cx - outer_r, cy - outer_r, outer_r * 2, outer_r * 2)

        # Secondary micro ring
        mid_r = int(radius * 1.15)
        mid_color = QColor(config["ring_color"])
        mid_color.setAlpha(int(40 * self._pulse_scale))
        painter.setPen(QPen(mid_color, 1))
        painter.drawEllipse(cx - mid_r, cy - mid_r, mid_r * 2, mid_r * 2)

        # Radial core gradient
        gradient = QRadialGradient(cx, cy, radius)
        fill_color = QColor(config["color"])
        gradient.setColorAt(0.0, fill_color)
        edge = QColor(fill_color)
        edge.setAlpha(0)
        gradient.setColorAt(1.0, edge)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(gradient))
        painter.drawEllipse(cx - radius, cy - radius, radius * 2, radius * 2)

        # Center Symbol / Icon
        painter.setPen(QColor(config["symbol_color"]))
        f = painter.font()
        f.setPointSize(int(base_radius * 0.50))
        painter.setFont(f)
        painter.drawText(
            cx - base_radius, cy - base_radius,
            base_radius * 2, base_radius * 2,
            Qt.AlignmentFlag.AlignCenter,
            config["symbol"],
        )

        # State label pill
        painter.setPen(QColor(config["label_color"]))
        lf = painter.font()
        lf.setPointSize(9)
        lf.setBold(True)
        painter.setFont(lf)
        painter.drawText(
            0, cy + base_radius + 18, w, 30,
            Qt.AlignmentFlag.AlignCenter,
            config["label"],
        )
