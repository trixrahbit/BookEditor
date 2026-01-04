"""
Settings dialog with modern styling
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QTabWidget,
    QLineEdit, QSpinBox, QCheckBox, QDialogButtonBox, QLabel,
    QGroupBox, QPushButton, QMessageBox
)
from PyQt6.QtCore import Qt, QSettings


class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.settings = QSettings()
        self.init_ui()
        self.load_settings()
        self.apply_modern_style()

    def init_ui(self):
        """Initialize the dialog UI"""
        self.setWindowTitle("Settings")
        self.setMinimumSize(650, 550)

        layout = QVBoxLayout(self)

        # Header
        header = QLabel("⚙️ Application Settings")
        header.setObjectName("settingsHeader")
        layout.addWidget(header)

        # Tab widget
        tabs = QTabWidget()
        tabs.setObjectName("settingsTabs")

        # Azure OpenAI tab
        azure_tab = self.create_azure_tab()
        tabs.addTab(azure_tab, "🤖 Azure OpenAI")

        # Editor tab
        editor_tab = self.create_editor_tab()
        tabs.addTab(editor_tab, "✏️ Editor")

        # AI Analysis tab
        ai_tab = self.create_ai_tab()
        tabs.addTab(ai_tab, "🧠 AI Analysis")

        layout.addWidget(tabs)

        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.save_and_accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def create_azure_tab(self):
        """Create Azure OpenAI configuration tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(15)

        # Info
        info = QLabel(
            "Configure your Azure OpenAI credentials to enable AI analysis.\n"
            "Get these from your Azure Portal."
        )
        info.setWordWrap(True)
        info.setObjectName("infoLabel")
        layout.addWidget(info)

        # Form
        form = QFormLayout()
        form.setSpacing(12)

        self.azure_api_key_edit = QLineEdit()
        self.azure_api_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.azure_api_key_edit.setPlaceholderText("Your API key")
        form.addRow("API Key:", self.azure_api_key_edit)

        self.azure_endpoint_edit = QLineEdit()
        self.azure_endpoint_edit.setPlaceholderText("https://your-resource.openai.azure.com/")
        form.addRow("Endpoint:", self.azure_endpoint_edit)

        self.azure_api_version_edit = QLineEdit()
        self.azure_api_version_edit.setText("2024-02-15-preview")
        form.addRow("API Version:", self.azure_api_version_edit)

        self.azure_deployment_edit = QLineEdit()
        self.azure_deployment_edit.setPlaceholderText("gpt-4")
        form.addRow("Deployment:", self.azure_deployment_edit)

        layout.addLayout(form)

        # Test button
        test_btn = QPushButton("🔌 Test Connection")
        test_btn.setObjectName("testButton")
        test_btn.clicked.connect(self.test_azure_connection)
        layout.addWidget(test_btn)

        layout.addStretch()
        return widget

    def create_editor_tab(self):
        """Create editor preferences tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        form = QFormLayout()
        form.setSpacing(12)

        self.autosave_spin = QSpinBox()
        self.autosave_spin.setRange(0, 60)
        self.autosave_spin.setSuffix(" seconds")
        self.autosave_spin.setValue(5)
        form.addRow("Auto-save interval:", self.autosave_spin)

        self.font_size_spin = QSpinBox()
        self.font_size_spin.setRange(8, 24)
        self.font_size_spin.setValue(12)
        form.addRow("Editor font size:", self.font_size_spin)

        self.show_word_count_check = QCheckBox()
        self.show_word_count_check.setChecked(True)
        form.addRow("Show word count:", self.show_word_count_check)

        layout.addLayout(form)
        layout.addStretch()
        return widget

    def create_ai_tab(self):
        """Create AI analysis preferences tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        form = QFormLayout()
        form.setSpacing(12)

        self.temperature_spin = QSpinBox()
        self.temperature_spin.setRange(0, 100)
        self.temperature_spin.setValue(70)
        self.temperature_spin.setSuffix("%")
        form.addRow("AI Temperature:", self.temperature_spin)

        self.max_tokens_spin = QSpinBox()
        self.max_tokens_spin.setRange(100, 4000)
        self.max_tokens_spin.setSingleStep(100)
        self.max_tokens_spin.setValue(2000)
        form.addRow("Max tokens:", self.max_tokens_spin)

        self.enable_caching_check = QCheckBox()
        self.enable_caching_check.setChecked(True)
        form.addRow("Cache responses:", self.enable_caching_check)

        layout.addLayout(form)

        # Info
        info = QLabel(
            "Higher temperature = more creative but less focused.\n"
            "Lower temperature = more deterministic and focused."
        )
        info.setWordWrap(True)
        info.setObjectName("infoLabel")
        layout.addWidget(info)

        layout.addStretch()
        return widget

    def load_settings(self):
        """Load settings from QSettings"""
        self.azure_api_key_edit.setText(self.settings.value("azure/api_key", ""))
        self.azure_endpoint_edit.setText(self.settings.value("azure/endpoint", ""))
        self.azure_api_version_edit.setText(self.settings.value("azure/api_version", "2024-02-15-preview"))
        self.azure_deployment_edit.setText(self.settings.value("azure/deployment", ""))

        self.autosave_spin.setValue(int(self.settings.value("editor/autosave_interval", 5)))
        self.font_size_spin.setValue(int(self.settings.value("editor/font_size", 12)))
        self.show_word_count_check.setChecked(self.settings.value("editor/show_word_count", True, type=bool))

        self.temperature_spin.setValue(int(self.settings.value("ai/temperature", 70)))
        self.max_tokens_spin.setValue(int(self.settings.value("ai/max_tokens", 2000)))
        self.enable_caching_check.setChecked(self.settings.value("ai/enable_caching", True, type=bool))

    def save_settings(self):
        """Save settings to QSettings"""
        self.settings.setValue("azure/api_key", self.azure_api_key_edit.text())
        self.settings.setValue("azure/endpoint", self.azure_endpoint_edit.text())
        self.settings.setValue("azure/api_version", self.azure_api_version_edit.text())
        self.settings.setValue("azure/deployment", self.azure_deployment_edit.text())

        self.settings.setValue("editor/autosave_interval", self.autosave_spin.value())
        self.settings.setValue("editor/font_size", self.font_size_spin.value())
        self.settings.setValue("editor/show_word_count", self.show_word_count_check.isChecked())

        self.settings.setValue("ai/temperature", self.temperature_spin.value())
        self.settings.setValue("ai/max_tokens", self.max_tokens_spin.value())
        self.settings.setValue("ai/enable_caching", self.enable_caching_check.isChecked())

    def save_and_accept(self):
        """Save settings and close"""
        self.save_settings()
        self.accept()

    def test_azure_connection(self):
        """Test Azure OpenAI connection"""
        api_key = self.azure_api_key_edit.text()
        endpoint = self.azure_endpoint_edit.text()

        if not api_key or not endpoint:
            QMessageBox.warning(
                self,
                "Missing Information",
                "Please enter both API key and endpoint."
            )
            return

        QMessageBox.information(
            self,
            "Connection Test",
            "Connection test will be implemented with AI integration."
        )

    def apply_modern_style(self):
        """Apply modern styling"""
        self.setStyleSheet("""
            QDialog {
                background: white;
            }

            QLabel#settingsHeader {
                font-size: 18pt;
                font-weight: bold;
                color: #212529;
                padding: 15px;
            }

            QLabel#infoLabel {
                color: #6c757d;
                padding: 10px;
                background: #f8f9fa;
                border-radius: 6px;
                margin: 10px 0;
            }

            QTabWidget::pane {
                border: 1px solid #dee2e6;
                border-radius: 4px;
                background: white;
            }

            QTabBar::tab {
                padding: 10px 20px;
                margin-right: 2px;
                background: #e9ecef;
                border: 1px solid #dee2e6;
                border-bottom: none;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }

            QTabBar::tab:selected {
                background: white;
                border-bottom: 1px solid white;
            }

            QLineEdit, QSpinBox {
                border: 1px solid #ced4da;
                border-radius: 4px;
                padding: 8px;
                background: white;
            }

            QLineEdit:focus, QSpinBox:focus {
                border-color: #667eea;
            }

            QPushButton#testButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #17a2b8, stop:1 #138496);
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
                font-weight: bold;
            }

            QPushButton#testButton:hover {
                background: #117a8b;
            }
        """)