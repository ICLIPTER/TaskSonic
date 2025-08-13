import sys
from pathlib import Path
from PySide6.QtCore import Qt, QTimer, QSize
from PySide6.QtGui import QMovie, QPainter, QTransform, QCursor, QPixmap
from PySide6.QtWidgets import QApplication, QLabel, QWidget

APP_NAME = "Sonic Taskbar Runner"

BASE_DIR = Path(__file__).parent
RUN_GIF = BASE_DIR / "sonic_run.gif"
IDLE_GIF = BASE_DIR / "sonic_idle.gif"

POLL_MS = 30
IDLE_AFTER_MS = 600
SPEED_THRESHOLD = 6.0
BOTTOM_MARGIN = 6
SCALE_FACTOR = 0.7  # <-- Sonic size adjustment


class MirrorMovieLabel(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._movie = None
        self.mirrored = False
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setStyleSheet("background: transparent;")

    def setMovie(self, movie):
        self._movie = movie
        super().setMovie(movie)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.SmoothPixmapTransform, True)
        if self._movie:
            frame = self._movie.currentPixmap()
            if not frame.isNull():
                w, h = frame.width(), frame.height()
                if self.mirrored:
                    transform = QTransform()
                    transform.scale(-1, 1)
                    transform.translate(-w, 0)
                    painter.setTransform(transform, True)
                painter.drawPixmap(0, 0, frame)
                return
        painter.resetTransform()


class SonicPet(QWidget):
    def __init__(self):
        super().__init__(None, Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setWindowTitle(APP_NAME)

        self.label = MirrorMovieLabel(self)
        self.movie_run = self._load_movie(RUN_GIF)
        self.movie_idle = self._load_idle_still(IDLE_GIF)

        if self.movie_idle:
            self.label.setMovie(self.movie_idle)
            self.movie_idle.start()

        self._last_cursor_pos = QCursor.pos()
        self._last_movement_ts = 0
        self._enabled = True  # start enabled

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)
        self.timer.start(POLL_MS)

        self._resize_to_movie()
        self._snap_to_taskbar_area()
        self.show()

    def _load_movie(self, path):
        if not path.exists():
            return None
        movie = QMovie(str(path))
        movie.setScaledSize(self._scaled_size(movie))
        return movie

    def _load_idle_still(self, path):
        """Loads only the first frame of idle GIF as a still image."""
        if not path.exists():
            return None
        movie = QMovie(str(path))
        movie.jumpToFrame(0)
        movie.setScaledSize(self._scaled_size(movie))
        return movie

    def _scaled_size(self, movie):
        """Returns scaled QSize for Sonic based on SCALE_FACTOR."""
        movie.start()
        frame = movie.currentPixmap()
        movie.stop()
        if not frame.isNull():
            w = int(frame.width() * SCALE_FACTOR)
            h = int(frame.height() * SCALE_FACTOR)
            return QSize(w, h)
        return QSize(0, 0)

    def _current_movie(self):
        return self.label.movie()

    def _play_run(self):
        if self.movie_run and self._current_movie() is not self.movie_run:
            self.label.setMovie(self.movie_run)
            self.movie_run.start()

    def _play_idle(self):
        if self.movie_idle and self._current_movie() is not self.movie_idle:
            self.label.setMovie(self.movie_idle)
            self.movie_idle.start()

    def _resize_to_movie(self):
        m = self._current_movie()
        if m:
            frame = m.currentPixmap()
            if not frame.isNull():
                self.label.resize(frame.size())
                self.resize(frame.size())

    def _screen_for_cursor(self):
        from PySide6.QtGui import QGuiApplication
        screen = QGuiApplication.screenAt(QCursor.pos())
        if not screen:
            screen = QGuiApplication.primaryScreen()
        return screen

    def _snap_to_taskbar_area(self):
        screen = self._screen_for_cursor()
        geo = screen.availableGeometry()
        x = QCursor.pos().x() - self.width() // 2
        y = geo.bottom() - self.height() - BOTTOM_MARGIN
        x = max(geo.left(), min(x, geo.right() - self.width()))
        self.move(x, y)

    def _tick(self):
        self._resize_to_movie()
        if not self._enabled:
            return

        cur = QCursor.pos()
        dx = cur.x() - self._last_cursor_pos.x()
        dist = abs(dx)

        if dx != 0:
            self.label.mirrored = dx < 0
            self.label.update()

        if dist > SPEED_THRESHOLD:
            self._last_movement_ts = 0
            self._play_run()
        else:
            if self._last_movement_ts == 0:
                self._last_movement_ts = 1
            else:
                self._last_movement_ts += POLL_MS
            if self._last_movement_ts >= IDLE_AFTER_MS:
                self._play_idle()

        self._follow_bottom(cur)
        self._last_cursor_pos = cur

    def _follow_bottom(self, cursor_global):
        screen = self._screen_for_cursor()
        geo = screen.availableGeometry()
        x = cursor_global.x() - self.width() // 2
        x = max(geo.left(), min(x, geo.right() - self.width()))
        y = geo.bottom() - self.height() - BOTTOM_MARGIN
        self.move(x, y)


def main():
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    pet = SonicPet()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
