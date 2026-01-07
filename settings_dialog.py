"""
Settings dialog with modern styling
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QTabWidget,
    QLineEdit, QSpinBox, QCheckBox, QDialogButtonBox, QLabel,
    QGroupBox, QPushButton, QMessageBox, QWidget, QRadioButton,
    QButtonGroup
)
from PyQt6.QtCore import Qt, QSettings

class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.settings = QSettings("Rabbit Consulting", "Novelist AI")
        self.init_ui()
        self.load_settings()
        self.apply_modern_style()

    def init_ui(self):
        """Initialize the dialog UI"""
        self.setWindowTitle("Settings")
        self.setMinimumSize(650, 550)

        # Main layout with no margins to allow header to span full width
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header
        header = QLabel("⚙️ Application Settings")
        header.setObjectName("settingsHeader")
        layout.addWidget(header)

        # Content container
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(15, 15, 15, 15)
        content_layout.setSpacing(15)

        # Provider Selection
        provider_group = QGroupBox("AI Service Provider")
        provider_layout = QHBoxLayout(provider_group)
        
        self.provider_bg = QButtonGroup(self)
        self.azure_radio = QRadioButton("Azure OpenAI")
        self.openai_radio = QRadioButton("Standard OpenAI")
        
        self.provider_bg.addButton(self.azure_radio, 0)
        self.provider_bg.addButton(self.openai_radio, 1)
        
        provider_layout.addWidget(self.azure_radio)
        provider_layout.addWidget(self.openai_radio)
        provider_layout.addStretch()
        
        content_layout.addWidget(provider_group)

        # Tab widget
        self.tabs = QTabWidget()
        self.tabs.setObjectName("settingsTabs")

        # Azure OpenAI tab
        azure_tab = self.create_azure_tab()
        self.tabs.addTab(azure_tab, "Azure OpenAI")

        # OpenAI tab
        openai_tab = self.create_openai_tab()
        self.tabs.addTab(openai_tab, "Standard OpenAI")

        # Editor tab
        editor_tab = self.create_editor_tab()
        self.tabs.addTab(editor_tab, "Editor")

        # AI Analysis tab
        ai_tab = self.create_ai_tab()
        self.tabs.addTab(ai_tab, "AI Analysis")

        content_layout.addWidget(self.tabs)

        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.save_and_accept)
        button_box.rejected.connect(self.reject)
        content_layout.addWidget(button_box)

        layout.addWidget(content_widget)

        # Connect radio buttons to tab switching (optional but helpful)
        self.azure_radio.toggled.connect(self.on_provider_changed)
        self.openai_radio.toggled.connect(self.on_provider_changed)

    def on_provider_changed(self):
        if self.azure_radio.isChecked():
            self.tabs.setTabEnabled(0, True)
            self.tabs.setTabEnabled(1, False)
            self.tabs.setCurrentIndex(0)
        else:
            self.tabs.setTabEnabled(0, False)
            self.tabs.setTabEnabled(1, True)
            self.tabs.setCurrentIndex(1)

    def create_openai_tab(self):
        """Create Standard OpenAI configuration tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(15)

        # Info
        info = QLabel(
            "Configure your Standard OpenAI API key to enable AI analysis.\n"
            "Get this from platform.openai.com."
        )
        info.setWordWrap(True)
        info.setObjectName("infoLabel")
        layout.addWidget(info)

        # Form
        form = QFormLayout()
        form.setSpacing(12)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)

        self.openai_api_key_edit = QLineEdit()
        self.openai_api_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.openai_api_key_edit.setPlaceholderText("sk-...")
        form.addRow("API Key:", self.openai_api_key_edit)

        self.openai_model_edit = QLineEdit()
        self.openai_model_edit.setText("gpt-4")
        self.openai_model_edit.setPlaceholderText("gpt-4, gpt-3.5-turbo, etc.")
        form.addRow("Model:", self.openai_model_edit)

        layout.addLayout(form)

        # Test button
        test_btn = QPushButton("🔌 Test Connection")
        test_btn.setObjectName("testButton")
        test_btn.clicked.connect(self.test_openai_connection)
        layout.addWidget(test_btn)

        layout.addStretch()
        return widget

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
        form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)

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
        form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)

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
        form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)

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

        self.disable_temperature_check = QCheckBox()
        self.disable_temperature_check.setChecked(False)
        form.addRow("Disable temperature:", self.disable_temperature_check)

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
        provider = self.settings.value("ai/provider", "azure")
        if provider == "openai":
            self.openai_radio.setChecked(True)
        else:
            self.azure_radio.setChecked(True)
        self.on_provider_changed()

        self.azure_api_key_edit.setText(self.settings.value("azure/api_key", ""))
        self.azure_endpoint_edit.setText(self.settings.value("azure/endpoint", ""))
        self.azure_api_version_edit.setText(self.settings.value("azure/api_version", "2024-02-15-preview"))
        self.azure_deployment_edit.setText(self.settings.value("azure/deployment", ""))

        self.openai_api_key_edit.setText(self.settings.value("openai/api_key", ""))
        self.openai_model_edit.setText(self.settings.value("openai/model", "gpt-4"))

        self.autosave_spin.setValue(int(self.settings.value("editor/autosave_interval", 5)))
        self.font_size_spin.setValue(int(self.settings.value("editor/font_size", 12)))
        self.show_word_count_check.setChecked(self.settings.value("editor/show_word_count", True, type=bool))

        self.temperature_spin.setValue(int(self.settings.value("ai/temperature", 70)))
        self.max_tokens_spin.setValue(int(self.settings.value("ai/max_tokens", 2000)))
        self.enable_caching_check.setChecked(self.settings.value("ai/enable_caching", True, type=bool))
        self.disable_temperature_check.setChecked(self.settings.value("ai/disable_temperature", False, type=bool))

    def save_settings(self):
        """Save settings to QSettings"""
        provider = "openai" if self.openai_radio.isChecked() else "azure"
        self.settings.setValue("ai/provider", provider)

        # Strip all values to remove whitespace/newlines
        self.settings.setValue("azure/api_key", self.azure_api_key_edit.text().strip())
        self.settings.setValue("azure/endpoint", self.azure_endpoint_edit.text().strip())
        self.settings.setValue("azure/api_version", self.azure_api_version_edit.text().strip())
        self.settings.setValue("azure/deployment", self.azure_deployment_edit.text().strip())

        self.settings.setValue("openai/api_key", self.openai_api_key_edit.text().strip())
        self.settings.setValue("openai/model", self.openai_model_edit.text().strip())

        self.settings.setValue("editor/autosave_interval", self.autosave_spin.value())
        self.settings.setValue("editor/font_size", self.font_size_spin.value())
        self.settings.setValue("editor/show_word_count", self.show_word_count_check.isChecked())

        self.settings.setValue("ai/temperature", self.temperature_spin.value())
        self.settings.setValue("ai/max_tokens", self.max_tokens_spin.value())
        self.settings.setValue("ai/enable_caching", self.enable_caching_check.isChecked())
        self.settings.setValue("ai/disable_temperature", self.disable_temperature_check.isChecked())

    def save_and_accept(self):
        """Save settings and close"""
        self.save_settings()

        # Refresh AI manager with new settings
        from ai_manager import ai_manager
        ai_manager.refresh_client()

        self.accept()

    def test_azure_connection(self):
        """Test Azure OpenAI connection"""
        api_key = self.azure_api_key_edit.text()
        endpoint = self.azure_endpoint_edit.text()

        if not api_key or not endpoint:
            QMessageBox.warning(
                self,
                "Missing Information",
                "Please enter both API key and endpoint before testing."
            )
            return

        # Save settings first
        self.settings.setValue("azure/api_key", api_key)
        self.settings.setValue("azure/endpoint", endpoint)
        self.settings.setValue("azure/api_version", self.azure_api_version_edit.text())
        self.settings.setValue("azure/deployment", self.azure_deployment_edit.text())

        # Force sync settings to disk
        self.settings.sync()

        # Refresh AI manager with new settings
        from ai_manager import ai_manager
        ai_manager.refresh_client()

        # Test connection
        success, message = ai_manager.test_connection()

        if success:
            QMessageBox.information(
                self,
                "Connection Successful",
                f"{message}\n\nYour Azure OpenAI is configured correctly!"
            )
        else:
            QMessageBox.warning(
                self,
                "Connection Failed",
                f"{message}\n\nPlease check your credentials."
            )

    def test_openai_connection(self):
        """Test Standard OpenAI connection"""
        api_key = self.openai_api_key_edit.text()
        model = self.openai_model_edit.text()

        if not api_key:
            QMessageBox.warning(
                self,
                "Missing Information",
                "Please enter an API key before testing."
            )
            return

        # Save settings first
        self.settings.setValue("ai/provider", "openai")
        self.settings.setValue("openai/api_key", api_key)
        self.settings.setValue("openai/model", model)

        # Force sync settings to disk
        self.settings.sync()

        # Refresh AI manager with new settings
        from ai_manager import ai_manager
        ai_manager.refresh_client()

        # Test connection
        success, message = ai_manager.test_connection()

        if success:
            QMessageBox.information(
                self,
                "Connection Successful",
                f"{message}\n\nYour OpenAI is configured correctly!"
            )
        else:
            QMessageBox.warning(
                self,
                "Connection Failed",
                f"{message}\n\nPlease check your credentials."
            )

    def apply_modern_style(self):
        """Apply modern styling"""
        self.setStyleSheet("""
            QDialog {
                background-color: #121212;
                color: #E0E0E0;
            }
            
            QLabel {
                color: #E0E0E0;
            }

            QLabel#settingsHeader {
                font-size: 18pt;
                font-weight: bold;
                color: white;
                padding: 15px;
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #7C4DFF, stop:1 #5E35B1);
                border-radius: 6px;
                margin-bottom: 10px;
            }
            
            QLabel#infoLabel {
                color: #A0A0A0;
                padding: 10px;
                background: #1E1E1E;
                border: 1px solid #2D2D2D;
                border-radius: 6px;
                margin: 5px 0;
            }
            
            QTabWidget::pane {
                border: 1px solid #2D2D2D;
                background: #1A1A1A;
                top: -1px;
            }
            
            QTabBar::tab {
                padding: 10px 20px;
                margin-right: 2px;
                background: #252526;
                color: #A0A0A0;
                border: 1px solid #2D2D2D;
                border-bottom: none;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }
            
            QTabBar::tab:selected {
                background: #1A1A1A;
                color: #7C4DFF;
                border-bottom: 1px solid #1A1A1A;
            }
            
            QTabBar::tab:hover {
                background: #3D3D3D;
            }

            QWidget {
                background-color: transparent;
            }

            QTabWidget QWidget {
                background-color: #1A1A1A;
            }
            
            QLineEdit, QSpinBox, QComboBox {
                border: 1px solid #3D3D3D;
                border-radius: 6px;
                padding: 8px;
                background: #1E1E1E;
                color: #E0E0E0;
            }
            
            QLineEdit:focus, QSpinBox:focus, QComboBox:focus {
                border-color: #7C4DFF;
            }
            
            QCheckBox {
                color: #E0E0E0;
                spacing: 8px;
            }
            
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                background-color: #252526;
                border: 1px solid #3D3D3D;
                border-radius: 3px;
            }
            
            QCheckBox::indicator:checked {
                background-color: #7C4DFF;
                border-color: #7C4DFF;
            }

            QRadioButton {
                color: #E0E0E0;
                spacing: 8px;
            }
            
            QRadioButton::indicator {
                width: 18px;
                height: 18px;
                background-color: #252526;
                border: 1px solid #3D3D3D;
                border-radius: 9px;
            }
            
            QRadioButton::indicator:checked {
                background-color: #7C4DFF;
                border: 4px solid #252526;
            }

            QGroupBox {
                border: 1px solid #2D2D2D;
                border-radius: 6px;
                margin-top: 20px;
                padding-top: 15px;
                font-weight: bold;
                color: #7C4DFF;
            }
            
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }

            QPushButton {
                background-color: #252526;
                border: 1px solid #3D3D3D;
                border-radius: 6px;
                padding: 8px 16px;
                color: #E0E0E0;
                font-weight: 500;
            }
            
            QPushButton:hover {
                background-color: #3D3D3D;
                border-color: #7C4DFF;
            }

            QPushButton#testButton {
                background-color: #252526;
                border: 1px solid #7C4DFF;
                color: #7C4DFF;
            }

            QPushButton#testButton:hover {
                background-color: #7C4DFF;
                color: white;
            }
            
            QDialogButtonBox QPushButton {
                min-width: 80px;
            }
            
            QDialogButtonBox QPushButton[text="OK"] {
                background-color: #7C4DFF;
                color: white;
                border: none;
            }
            
            QDialogButtonBox QPushButton[text="OK"]:hover {
                background-color: #9E7CFF;
            }
        """)