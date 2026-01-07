from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QListWidget, 
    QListWidgetItem, QLabel, QLineEdit, QTextEdit, QComboBox, 
    QCheckBox, QMessageBox, QFrame, QSplitter
)
from PyQt6.QtCore import Qt
from models.project import WorldRule, Project
import uuid

class WorldRulesDialog(QDialog):
    def __init__(self, parent, project: Project):
        super().__init__(parent)
        self.project = project
        self.setWindowTitle("World Rules Engine - Define Laws of the Universe")
        self.resize(800, 600)
        self.init_ui()
        self.load_rules()

    def init_ui(self):
        layout = QVBoxLayout(self)
        
        self.setStyleSheet("""
            QDialog {
                background-color: #121212;
                color: #E0E0E0;
            }
            QLabel {
                color: #E0E0E0;
            }
            QListWidget {
                background-color: #1E1E1E;
                border: 1px solid #3D3D3D;
                border-radius: 4px;
                color: #E0E0E0;
            }
            QListWidget::item:selected {
                background-color: #7C4DFF;
                color: white;
            }
            QLineEdit, QTextEdit, QComboBox {
                background-color: #1E1E1E;
                border: 1px solid #3D3D3D;
                border-radius: 4px;
                padding: 6px;
                color: #E0E0E0;
            }
            QCheckBox {
                color: #E0E0E0;
            }
            QPushButton {
                background-color: #252526;
                border: 1px solid #3D3D3D;
                border-radius: 6px;
                padding: 8px 16px;
                color: #E0E0E0;
            }
            QPushButton:hover {
                background-color: #3D3D3D;
                border-color: #7C4DFF;
            }
        """)

        header = QLabel("World Rules Engine")
        header.setStyleSheet("font-size: 16pt; font-weight: bold; color: #7C4DFF; margin-bottom: 10px;")
        layout.addWidget(header)
        
        description = QLabel("Define the laws, magic limits, technology levels, and cultural norms for your story. AI will use these to flag violations.")
        description.setWordWrap(True)
        description.setStyleSheet("color: #A0A0A0; margin-bottom: 20px;")
        layout.addWidget(description)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)
        
        # Left side: List of rules
        left_widget = QFrame()
        left_layout = QVBoxLayout(left_widget)
        
        self.rules_list = QListWidget()
        self.rules_list.currentRowChanged.connect(self._on_row_changed)
        left_layout.addWidget(self.rules_list)
        
        btn_layout = QHBoxLayout()
        add_btn = QPushButton("Add Rule")
        add_btn.clicked.connect(self.add_rule)
        add_btn.setStyleSheet("background-color: #2ecc71; color: white; font-weight: bold;")
        
        delete_btn = QPushButton("Delete")
        delete_btn.clicked.connect(self.delete_rule)
        delete_btn.setStyleSheet("background-color: #e74c3c; color: white;")
        
        btn_layout.addWidget(add_btn)
        btn_layout.addWidget(delete_btn)
        left_layout.addLayout(btn_layout)
        
        splitter.addWidget(left_widget)
        
        # Right side: Rule editor
        self.editor_widget = QFrame()
        self.editor_widget.setFrameShape(QFrame.Shape.StyledPanel)
        editor_layout = QVBoxLayout(self.editor_widget)
        
        editor_layout.addWidget(QLabel("Rule Name:"))
        self.name_edit = QLineEdit()
        editor_layout.addWidget(self.name_edit)
        
        editor_layout.addWidget(QLabel("Category:"))
        self.category_combo = QComboBox()
        self.category_combo.addItems(["Magic", "Technology", "Culture", "Physics", "Reality", "Other"])
        editor_layout.addWidget(self.category_combo)
        
        editor_layout.addWidget(QLabel("Description / Law:"))
        self.desc_edit = QTextEdit()
        self.desc_edit.setPlaceholderText("Describe the rule clearly (e.g., 'Magic costs physical stamina', 'No gunpowder exists', 'Time travel creates branching realities')")
        editor_layout.addWidget(self.desc_edit)
        
        editor_layout.addWidget(QLabel("Consequences (Optional):"))
        self.cons_edit = QTextEdit()
        self.cons_edit.setPlaceholderText("What happens if this rule is broken or exercised?")
        editor_layout.addWidget(self.cons_edit)
        
        self.active_check = QCheckBox("Rule is Active (AI will check this)")
        self.active_check.setChecked(True)
        editor_layout.addWidget(self.active_check)
        
        save_rule_btn = QPushButton("Save Rule Changes")
        save_rule_btn.clicked.connect(self.save_current_rule)
        save_rule_btn.setStyleSheet("background-color: #7C4DFF; color: white; font-weight: bold; padding: 10px;")
        editor_layout.addWidget(save_rule_btn)
        
        editor_layout.addStretch()
        splitter.addWidget(self.editor_widget)
        
        splitter.setSizes([300, 500])
        layout.addWidget(splitter)
        
        # Dialog buttons
        bottom_buttons = QHBoxLayout()
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        bottom_buttons.addStretch()
        bottom_buttons.addWidget(close_btn)
        layout.addLayout(bottom_buttons)
        
        self.editor_widget.setEnabled(False)
        self.current_rule_id = None

    def load_rules(self):
        self.rules_list.clear()
        for rule in self.project.world_rules:
            item = QListWidgetItem(rule.name)
            item.setData(Qt.ItemDataRole.UserRole, rule.id)
            self.rules_list.addItem(item)

    def _on_row_changed(self, row):
        if row >= 0:
            item = self.rules_list.item(row)
            self.on_rule_selected(item)
        else:
            self.editor_widget.setEnabled(False)
            self.current_rule_id = None

    def on_rule_selected(self, item):
        if not item:
            return
        rule_id = item.data(Qt.ItemDataRole.UserRole)
        rule = next((r for r in self.project.world_rules if r.id == rule_id), None)
        if rule:
            self.current_rule_id = rule.id
            self.name_edit.setText(rule.name)
            self.category_combo.setCurrentText(rule.rule_category)
            self.desc_edit.setPlainText(rule.description)
            self.cons_edit.setPlainText(rule.consequences)
            self.active_check.setChecked(rule.is_active)
            self.editor_widget.setEnabled(True)

    def add_rule(self):
        new_rule = WorldRule(
            name="New Rule",
            description="",
            rule_category="Magic"
        )
        self.project.world_rules.append(new_rule)
        self.load_rules()
        # Select the new rule
        for i in range(self.rules_list.count()):
            item = self.rules_list.item(i)
            if item.data(Qt.ItemDataRole.UserRole) == new_rule.id:
                self.rules_list.setCurrentItem(item)
                self.name_edit.setFocus()
                break

    def delete_rule(self):
        if not self.current_rule_id:
            return
        
        res = QMessageBox.question(self, "Confirm Delete", "Are you sure you want to delete this rule?")
        if res == QMessageBox.StandardButton.Yes:
            self.project.world_rules = [r for r in self.project.world_rules if r.id != self.current_rule_id]
            self.current_rule_id = None
            self.editor_widget.setEnabled(False)
            self.load_rules()

    def save_current_rule(self):
        if not self.current_rule_id:
            return
        
        rule = next((r for r in self.project.world_rules if r.id == self.current_rule_id), None)
        if rule:
            rule.name = self.name_edit.text()
            rule.rule_category = self.category_combo.currentText()
            rule.description = self.desc_edit.toPlainText()
            rule.consequences = self.cons_edit.toPlainText()
            rule.is_active = self.active_check.isChecked()
            
            # Update list item text
            item = self.rules_list.currentItem()
            if item:
                item.setText(rule.name)
            
            # Notify parent/app about changes if needed (the project object is modified in place)
            QMessageBox.information(self, "Saved", f"Rule '{rule.name}' updated.")
