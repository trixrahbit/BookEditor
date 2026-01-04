import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QPushButton, QLabel
from PyQt6.QtCore import Qt


# Simple test window to verify PyQt6 is working
class TestWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Novelist AI - Test Launch")
        self.setGeometry(100, 100, 800, 600)

        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Create layout
        layout = QVBoxLayout(central_widget)

        # Add label
        label = QLabel("Novelist AI is running!\n\nThis is a test window.")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setStyleSheet("font-size: 18pt; padding: 20px;")
        layout.addWidget(label)

        # Add button
        button = QPushButton("Click Me to Test")
        button.clicked.connect(self.on_button_clicked)
        button.setStyleSheet("font-size: 14pt; padding: 10px;")
        layout.addWidget(button)

        # Status label
        self.status_label = QLabel("Ready")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet("color: gray; padding: 10px;")
        layout.addWidget(self.status_label)

    def on_button_clicked(self):
        self.status_label.setText("Button clicked! GUI is working correctly.")
        print("Button clicked - GUI is working!")


def main():
    print("Starting Novelist AI...")
    print(f"Python version: {sys.version}")
    print(f"PyQt6 imported successfully")

    # Create application
    app = QApplication(sys.argv)
    app.setApplicationName("Novelist AI")

    # Create and show window
    window = TestWindow()
    window.show()

    print("Window created and shown")
    print("Application running - close the window to exit")

    # Start event loop - this keeps the window open
    exit_code = app.exec()
    print(f"Application closed with exit code: {exit_code}")
    return exit_code


if __name__ == '__main__':
    sys.exit(main())
