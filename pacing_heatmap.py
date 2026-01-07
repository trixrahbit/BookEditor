from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QToolTip, QFrame
from PyQt6.QtCore import Qt, QRect, QPoint, pyqtSignal
from PyQt6.QtGui import QPainter, QColor, QLinearGradient, QBrush, QPen, QFontMetrics

class PacingHeatmapWidget(QWidget):
    """
    Visualizes pacing data as a timeline bar.
    🔵 (Calm) -> 🔴 (Intense)
    """
    scene_selected = pyqtSignal(str) # scene_name

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(150)
        self.pacing_data = [] # List of dicts with intensity, length, scene_name, etc.
        self.setMouseTracking(True)
        self.hovered_scene_index = -1

    def set_data(self, pacing_data):
        self.pacing_data = pacing_data
        self.update()

    def paintEvent(self, event):
        if not self.pacing_data:
            painter = QPainter(self)
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "No pacing data available. Run analysis.")
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        width = self.width()
        height = self.height()
        
        margin_left = 20
        margin_right = 20
        margin_top = 40
        margin_bottom = 40
        
        draw_width = width - margin_left - margin_right
        draw_height = 40 # Height of the bar
        
        total_length = sum(d.get('length', 1000) for d in self.pacing_data)
        if total_length == 0:
            return

        current_x = margin_left
        
        for i, scene in enumerate(self.pacing_data):
            scene_length = scene.get('length', 1000)
            scene_width = (scene_length / total_length) * draw_width
            
            # Map intensity (0-10) to color (Blue to Red)
            intensity = scene.get('intensity', 5)
            color = self._get_intensity_color(intensity)
            
            rect = QRect(int(current_x), margin_top, int(scene_width), draw_height)
            
            # Draw scene block
            painter.setBrush(QBrush(color))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRect(rect)
            
            # Highlight hovered
            if i == self.hovered_scene_index:
                painter.setPen(QPen(Qt.GlobalColor.white, 2))
                painter.drawRect(rect)
                
            # Dialogue vs Exposition markers (small bar below)
            diag_ratio = scene.get('dialogue_ratio', 0.5)
            diag_height = 5
            diag_rect = QRect(int(current_x), margin_top + draw_height + 5, int(scene_width), diag_height)
            
            # Yellow for dialogue-heavy, Grey for exposition
            diag_color = QColor(255, 215, 0) # Gold
            expo_color = QColor(169, 169, 169) # DarkGray
            
            # Mixed color based on ratio
            mix_color = QColor(
                int(diag_color.red() * diag_ratio + expo_color.red() * (1 - diag_ratio)),
                int(diag_color.green() * diag_ratio + expo_color.green() * (1 - diag_ratio)),
                int(diag_color.blue() * diag_ratio + expo_color.blue() * (1 - diag_ratio))
            )
            painter.setBrush(QBrush(mix_color))
            painter.drawRect(diag_rect)

            current_x += scene_width

        # Draw tension curve
        self._draw_tension_curve(painter, margin_left, margin_top, draw_width, draw_height, total_length)

        # Draw Labels
        painter.setPen(Qt.GlobalColor.white)
        painter.drawText(margin_left, margin_top - 10, "Pacing Heatmap (Calm 🔵 → Intense 🔴)")
        painter.drawText(margin_left, margin_top + draw_height + 30, "Dialogue-Heavy (Gold) vs Exposition-Heavy (Grey)")

    def _get_intensity_color(self, intensity):
        # 0 is Blue, 10 is Red
        factor = max(0, min(10, intensity)) / 10.0
        r = int(255 * factor)
        g = int(100 * (1 - factor))
        b = int(255 * (1 - factor))
        return QColor(r, g, b)

    def _draw_tension_curve(self, painter, margin_left, margin_top, draw_width, draw_height, total_length):
        if len(self.pacing_data) < 2:
            return
            
        painter.setPen(QPen(Qt.GlobalColor.white, 2, Qt.PenStyle.DashLine))
        path = []
        current_x = margin_left
        
        for scene in self.pacing_data:
            scene_length = scene.get('length', 1000)
            scene_width = (scene_length / total_length) * draw_width
            
            tension = scene.get('tension', 5)
            # Map tension (0-10) to y inside the bar
            y = margin_top + draw_height - (tension / 10.0) * draw_height
            
            path.append(QPoint(int(current_x + scene_width/2), int(y)))
            current_x += scene_width
            
        for i in range(len(path) - 1):
            painter.drawLine(path[i], path[i+1])

    def mouseMoveEvent(self, event):
        margin_left = 20
        margin_right = 20
        draw_width = self.width() - margin_left - margin_right
        
        total_length = sum(d.get('length', 1000) for d in self.pacing_data)
        if total_length == 0:
            return
            
        x = event.position().x()
        if x < margin_left or x > self.width() - margin_right:
            self.hovered_scene_index = -1
            QToolTip.hideText()
            self.update()
            return
            
        current_x = margin_left
        found_index = -1
        for i, scene in enumerate(self.pacing_data):
            scene_length = scene.get('length', 1000)
            scene_width = (scene_length / total_length) * draw_width
            if current_x <= x <= current_x + scene_width:
                found_index = i
                break
            current_x += scene_width
            
        if found_index != self.hovered_scene_index:
            self.hovered_scene_index = found_index
            if self.hovered_scene_index != -1:
                scene = self.pacing_data[self.hovered_scene_index]
                tooltip = f"<b>{scene.get('scene_name', 'Unknown')}</b><br/>" \
                          f"Intensity: {scene.get('intensity')}/10<br/>" \
                          f"Tension: {scene.get('tension')}/10<br/>" \
                          f"Dialogue Ratio: {int(scene.get('dialogue_ratio', 0) * 100)}%"
                QToolTip.showText(event.globalPosition().toPoint(), tooltip, self)
            else:
                QToolTip.hideText()
            self.update()

    def mousePressEvent(self, event):
        if self.hovered_scene_index != -1:
            scene_name = self.pacing_data[self.hovered_scene_index].get('scene_name')
            self.scene_selected.emit(scene_name)
