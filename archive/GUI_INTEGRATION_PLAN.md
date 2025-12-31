# GUI Integration Plan - Phase 8

**Priority:** High  
**Target Start:** After Security Hardening Complete  
**Estimated Duration:** 8-10 weeks  
**Framework:** PyQt6 (Recommended)

---

## Executive Summary

This plan outlines the development of a comprehensive GUI for the Prisma Access Configuration Capture system. The GUI will provide user-friendly interfaces for authentication, configuration pull/push operations, conflict resolution, and configuration management.

### Why PyQt6?

**Selected Framework:** PyQt6  
**Alternatives Considered:** Tkinter, PySide6, Web-based (Flask/React)

**Rationale:**
- ✅ Modern, native appearance across platforms
- ✅ Excellent threading support for long-running operations
- ✅ Rich widget library (tree views, progress dialogs, tabs)
- ✅ Built-in support for async operations
- ✅ Professional look and feel
- ✅ Strong documentation and community

---

## Phase 8 Overview

### Deliverables
1. Main application window with navigation
2. Authentication dialog
3. Pull workflow UI
4. Push workflow UI
5. Configuration viewer/editor
6. Conflict resolution dialog
7. Progress indicators
8. Settings/preferences dialog

### Architecture

```
gui/
├── __init__.py
├── main.py                     # Application entry point
├── main_window.py              # Main window (QMainWindow)
├── models/                     # Data models (MVC pattern)
│   ├── __init__.py
│   ├── config_model.py         # Configuration state
│   ├── operation_model.py      # Operation tracking
│   └── credentials_model.py    # Credentials management
├── views/                      # UI components (QWidget subclasses)
│   ├── __init__.py
│   ├── auth_dialog.py          # Authentication dialog
│   ├── pull_view.py            # Pull configuration UI
│   ├── push_view.py            # Push configuration UI
│   ├── conflict_view.py        # Conflict resolution
│   ├── config_viewer.py        # Configuration viewer/editor
│   ├── progress_dialog.py      # Progress indicators
│   └── settings_dialog.py      # Application settings
├── controllers/                # Business logic controllers
│   ├── __init__.py
│   ├── pull_controller.py      # Pull orchestration
│   ├── push_controller.py      # Push orchestration
│   ├── auth_controller.py      # Authentication logic
│   └── config_controller.py    # Configuration management
├── workers/                    # Background workers (QThread)
│   ├── __init__.py
│   ├── pull_worker.py          # Async pull operations
│   ├── push_worker.py          # Async push operations
│   └── validation_worker.py    # Async validation
├── widgets/                    # Custom widgets
│   ├── __init__.py
│   ├── folder_tree.py          # Folder selection tree
│   ├── rule_list.py            # Rule display widget
│   ├── conflict_list.py        # Conflict display widget
│   └── log_viewer.py           # Log display widget
└── resources/                  # UI resources
    ├── icons/                  # Application icons
    ├── styles/                 # QSS stylesheets
    └── ui/                     # Qt Designer files (optional)
```

---

## Week-by-Week Implementation Plan

### Week 1-2: Foundation & Infrastructure

#### Week 1: Project Setup
**Goals:**
- Set up PyQt6 project structure
- Create main window skeleton
- Implement navigation system
- Add basic styling

**Tasks:**
1. Install PyQt6 and dependencies
   ```bash
   pip install PyQt6 PyQt6-Qt6 PyQt6-sip
   ```

2. Create main application entry point
   ```python
   # gui/main.py
   import sys
   from PyQt6.QtWidgets import QApplication
   from gui.main_window import MainWindow
   
   def main():
       app = QApplication(sys.argv)
       app.setApplicationName("Prisma Access Config Manager")
       app.setOrganizationName("PA Config Lab")
       
       window = MainWindow()
       window.show()
       
       sys.exit(app.exec())
   
   if __name__ == '__main__':
       main()
   ```

3. Create main window with navigation
   ```python
   # gui/main_window.py
   from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, 
                                  QHBoxLayout, QStackedWidget, QPushButton,
                                  QMenuBar, QStatusBar)
   from PyQt6.QtCore import Qt
   
   class MainWindow(QMainWindow):
       def __init__(self):
           super().__init__()
           self.setWindowTitle("Prisma Access Configuration Manager")
           self.setGeometry(100, 100, 1400, 900)
           
           self.setup_ui()
           self.setup_menu()
           self.setup_statusbar()
       
       def setup_ui(self):
           # Central widget with stacked layout for different views
           central_widget = QWidget()
           self.setCentralWidget(central_widget)
           
           main_layout = QHBoxLayout()
           central_widget.setLayout(main_layout)
           
           # Navigation sidebar
           nav_widget = self.create_navigation()
           main_layout.addWidget(nav_widget)
           
           # Content area (stacked widget for different views)
           self.content_stack = QStackedWidget()
           main_layout.addWidget(self.content_stack, 1)
           
           # Add views
           from gui.views.pull_view import PullView
           from gui.views.push_view import PushView
           from gui.views.config_viewer import ConfigViewer
           
           self.pull_view = PullView()
           self.push_view = PushView()
           self.config_view = ConfigViewer()
           
           self.content_stack.addWidget(self.pull_view)
           self.content_stack.addWidget(self.push_view)
           self.content_stack.addWidget(self.config_view)
       
       def create_navigation(self):
           nav_widget = QWidget()
           nav_widget.setFixedWidth(200)
           nav_layout = QVBoxLayout()
           nav_widget.setLayout(nav_layout)
           
           # Navigation buttons
           btn_pull = QPushButton("Pull Configuration")
           btn_push = QPushButton("Push Configuration")
           btn_view = QPushButton("View Configuration")
           btn_settings = QPushButton("Settings")
           
           btn_pull.clicked.connect(lambda: self.content_stack.setCurrentIndex(0))
           btn_push.clicked.connect(lambda: self.content_stack.setCurrentIndex(1))
           btn_view.clicked.connect(lambda: self.content_stack.setCurrentIndex(2))
           
           nav_layout.addWidget(btn_pull)
           nav_layout.addWidget(btn_push)
           nav_layout.addWidget(btn_view)
           nav_layout.addWidget(btn_settings)
           nav_layout.addStretch()
           
           return nav_widget
   ```

**Deliverables:**
- [ ] Main window with navigation sidebar
- [ ] Stacked widget for view switching
- [ ] Basic menu bar
- [ ] Status bar for messages

#### Week 2: Authentication & Credentials
**Goals:**
- Create authentication dialog
- Implement secure credential storage
- Add credential validation

**Tasks:**
1. Authentication dialog
   ```python
   # gui/views/auth_dialog.py
   from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QFormLayout, 
                                  QLineEdit, QPushButton, QLabel, QCheckBox)
   from PyQt6.QtCore import pyqtSignal
   
   class AuthDialog(QDialog):
       authenticated = pyqtSignal(str, str, str)  # tsg_id, user, secret
       
       def __init__(self, parent=None):
           super().__init__(parent)
           self.setWindowTitle("Prisma Access Authentication")
           self.setModal(True)
           self.setup_ui()
       
       def setup_ui(self):
           layout = QVBoxLayout()
           self.setLayout(layout)
           
           # Form layout
           form_layout = QFormLayout()
           
           self.tsg_input = QLineEdit()
           self.tsg_input.setPlaceholderText("tsg-1234567890")
           form_layout.addRow("TSG ID:", self.tsg_input)
           
           self.user_input = QLineEdit()
           self.user_input.setPlaceholderText("API Client ID")
           form_layout.addRow("API User:", self.user_input)
           
           self.secret_input = QLineEdit()
           self.secret_input.setEchoMode(QLineEdit.EchoMode.Password)
           self.secret_input.setPlaceholderText("API Client Secret")
           form_layout.addRow("API Secret:", self.secret_input)
           
           self.save_checkbox = QCheckBox("Save credentials (encrypted)")
           form_layout.addRow("", self.save_checkbox)
           
           layout.addLayout(form_layout)
           
           # Buttons
           btn_layout = QHBoxLayout()
           self.btn_connect = QPushButton("Connect")
           self.btn_cancel = QPushButton("Cancel")
           
           self.btn_connect.clicked.connect(self.handle_connect)
           self.btn_cancel.clicked.connect(self.reject)
           
           btn_layout.addWidget(self.btn_connect)
           btn_layout.addWidget(self.btn_cancel)
           layout.addLayout(btn_layout)
           
           # Status label
           self.status_label = QLabel("")
           layout.addWidget(self.status_label)
       
       def handle_connect(self):
           tsg_id = self.tsg_input.text().strip()
           api_user = self.user_input.text().strip()
           api_secret = self.secret_input.text().strip()
           
           if not all([tsg_id, api_user, api_secret]):
               self.status_label.setText("⚠ All fields are required")
               return
           
           # Emit signal with credentials
           self.authenticated.emit(tsg_id, api_user, api_secret)
   ```

2. Authentication controller
   ```python
   # gui/controllers/auth_controller.py
   from PyQt6.QtCore import QObject, pyqtSignal
   from prisma.api_client import PrismaAccessAPIClient
   
   class AuthController(QObject):
       authentication_success = pyqtSignal(PrismaAccessAPIClient)
       authentication_failed = pyqtSignal(str)
       
       def authenticate(self, tsg_id: str, api_user: str, api_secret: str):
           """Authenticate with Prisma Access API."""
           try:
               client = PrismaAccessAPIClient(
                   tsg_id=tsg_id,
                   api_user=api_user,
                   api_secret=api_secret
               )
               
               # Test authentication
               client.authenticate()
               
               self.authentication_success.emit(client)
           except Exception as e:
               self.authentication_failed.emit(str(e))
   ```

**Deliverables:**
- [ ] Authentication dialog with validation
- [ ] Credential storage with encryption
- [ ] Authentication controller
- [ ] Error handling and feedback

---

### Week 3-4: Pull Workflow UI

#### Week 3: Folder Selection & Preview
**Goals:**
- Create folder tree view
- Implement folder selection
- Add snippet selection

**Tasks:**
1. Folder tree widget
   ```python
   # gui/widgets/folder_tree.py
   from PyQt6.QtWidgets import QTreeWidget, QTreeWidgetItem
   from PyQt6.QtCore import Qt, pyqtSignal
   
   class FolderTreeWidget(QTreeWidget):
       selection_changed = pyqtSignal(list)
       
       def __init__(self):
           super().__init__()
           self.setHeaderLabel("Folders")
           self.setSelectionMode(QTreeWidget.SelectionMode.MultiSelection)
           self.itemSelectionChanged.connect(self.on_selection_changed)
       
       def populate_folders(self, folders: list):
           """Populate tree with folder list."""
           self.clear()
           
           for folder in folders:
               item = QTreeWidgetItem(self)
               item.setText(0, folder.get('name', ''))
               item.setData(0, Qt.ItemDataRole.UserRole, folder)
               
               # Add checkbox
               item.setCheckState(0, Qt.CheckState.Unchecked)
       
       def get_selected_folders(self) -> list:
           """Get list of selected folder names."""
           selected = []
           root = self.invisibleRootItem()
           
           for i in range(root.childCount()):
               item = root.child(i)
               if item.checkState(0) == Qt.CheckState.Checked:
                   folder_data = item.data(0, Qt.ItemDataRole.UserRole)
                   selected.append(folder_data)
           
           return selected
       
       def on_selection_changed(self):
           selected = self.get_selected_folders()
           self.selection_changed.emit(selected)
   ```

2. Pull view implementation
   ```python
   # gui/views/pull_view.py
   from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, 
                                  QPushButton, QLabel, QCheckBox, QGroupBox)
   from gui.widgets.folder_tree import FolderTreeWidget
   
   class PullView(QWidget):
       def __init__(self):
           super().__init__()
           self.api_client = None
           self.setup_ui()
       
       def setup_ui(self):
           layout = QVBoxLayout()
           self.setLayout(layout)
           
           # Header
           header = QLabel("<h2>Pull Configuration from Prisma Access</h2>")
           layout.addWidget(header)
           
           # Folder selection
           folder_group = QGroupBox("Select Folders")
           folder_layout = QVBoxLayout()
           folder_group.setLayout(folder_layout)
           
           self.folder_tree = FolderTreeWidget()
           folder_layout.addWidget(self.folder_tree)
           
           btn_layout = QHBoxLayout()
           btn_discover = QPushButton("Discover Folders")
           btn_discover.clicked.connect(self.discover_folders)
           btn_layout.addWidget(btn_discover)
           btn_layout.addStretch()
           folder_layout.addLayout(btn_layout)
           
           layout.addWidget(folder_group)
           
           # Options
           options_group = QGroupBox("Options")
           options_layout = QVBoxLayout()
           options_group.setLayout(options_layout)
           
           self.include_snippets_cb = QCheckBox("Include Snippets")
           self.include_snippets_cb.setChecked(True)
           options_layout.addWidget(self.include_snippets_cb)
           
           self.detect_defaults_cb = QCheckBox("Detect and Filter Defaults")
           self.detect_defaults_cb.setChecked(True)
           options_layout.addWidget(self.detect_defaults_cb)
           
           layout.addWidget(options_group)
           
           # Action buttons
           action_layout = QHBoxLayout()
           self.btn_pull = QPushButton("Pull Configuration")
           self.btn_pull.clicked.connect(self.start_pull)
           self.btn_pull.setEnabled(False)
           action_layout.addWidget(self.btn_pull)
           action_layout.addStretch()
           layout.addLayout(action_layout)
           
           layout.addStretch()
       
       def set_api_client(self, client):
           """Set authenticated API client."""
           self.api_client = client
           self.btn_pull.setEnabled(True)
       
       def discover_folders(self):
           """Discover available folders."""
           if not self.api_client:
               return
           
           from gui.workers.pull_worker import FolderDiscoveryWorker
           
           # Create and start worker
           self.discovery_worker = FolderDiscoveryWorker(self.api_client)
           self.discovery_worker.folders_discovered.connect(self.on_folders_discovered)
           self.discovery_worker.start()
       
       def on_folders_discovered(self, folders):
           """Handle discovered folders."""
           self.folder_tree.populate_folders(folders)
       
       def start_pull(self):
           """Start pull operation."""
           selected_folders = self.folder_tree.get_selected_folders()
           
           if not selected_folders:
               # Show warning
               return
           
           from gui.controllers.pull_controller import PullController
           
           # Create pull controller and start
           # ... (implementation in Week 4)
   ```

**Deliverables:**
- [ ] Folder tree widget with selection
- [ ] Folder discovery integration
- [ ] Pull view layout
- [ ] Options selection (snippets, defaults)

#### Week 4: Pull Execution & Progress
**Goals:**
- Implement pull worker thread
- Add progress dialog
- Handle pull results

**Tasks:**
1. Pull worker thread
   ```python
   # gui/workers/pull_worker.py
   from PyQt6.QtCore import QThread, pyqtSignal
   from prisma.pull.pull_orchestrator import PullOrchestrator
   
   class PullWorker(QThread):
       progress_updated = pyqtSignal(str, int, int)  # message, current, total
       pull_completed = pyqtSignal(dict)  # configuration
       pull_failed = pyqtSignal(str)  # error message
       
       def __init__(self, api_client, folder_names, include_snippets, detect_defaults):
           super().__init__()
           self.api_client = api_client
           self.folder_names = folder_names
           self.include_snippets = include_snippets
           self.detect_defaults = detect_defaults
       
       def run(self):
           """Execute pull operation in background thread."""
           try:
               orchestrator = PullOrchestrator(
                   self.api_client,
                   detect_defaults=self.detect_defaults
               )
               
               # Set progress callback
               orchestrator.set_progress_callback(self.handle_progress)
               
               # Execute pull
               config = orchestrator.pull_complete_configuration(
                   folder_names=self.folder_names,
                   include_snippets=self.include_snippets
               )
               
               self.pull_completed.emit(config)
           except Exception as e:
               self.pull_failed.emit(str(e))
       
       def handle_progress(self, message: str, current: int, total: int):
           """Handle progress updates."""
           self.progress_updated.emit(message, current, total)
   ```

2. Progress dialog
   ```python
   # gui/views/progress_dialog.py
   from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QProgressBar
   from PyQt6.QtCore import Qt
   
   class ProgressDialog(QDialog):
       def __init__(self, title="Operation in Progress", parent=None):
           super().__init__(parent)
           self.setWindowTitle(title)
           self.setModal(True)
           self.setFixedSize(500, 150)
           self.setup_ui()
       
       def setup_ui(self):
           layout = QVBoxLayout()
           self.setLayout(layout)
           
           self.message_label = QLabel("Initializing...")
           layout.addWidget(self.message_label)
           
           self.progress_bar = QProgressBar()
           self.progress_bar.setRange(0, 100)
           layout.addWidget(self.progress_bar)
           
           self.detail_label = QLabel("")
           self.detail_label.setWordWrap(True)
           layout.addWidget(self.detail_label)
       
       def update_progress(self, message: str, current: int, total: int):
           """Update progress display."""
           self.message_label.setText(message)
           
           if total > 0:
               percentage = int((current / total) * 100)
               self.progress_bar.setValue(percentage)
               self.detail_label.setText(f"{current} of {total}")
   ```

**Deliverables:**
- [ ] Pull worker thread
- [ ] Progress dialog
- [ ] Pull controller integration
- [ ] Result handling and display

---

### Week 5-6: Configuration Viewer

#### Week 5: Tree View & Navigation
**Goals:**
- Create configuration tree viewer
- Implement navigation between folders/objects
- Add search functionality

**Tasks:**
1. Configuration viewer widget
2. Tree navigation
3. Detail panels

**Deliverables:**
- [ ] Configuration tree view
- [ ] Detail panels for objects/rules
- [ ] Search/filter functionality
- [ ] Export options

#### Week 6: Editing & Validation
**Goals:**
- Add basic editing capabilities
- Implement validation
- Add save functionality

**Deliverables:**
- [ ] Inline editing
- [ ] Validation feedback
- [ ] Save configuration
- [ ] Diff view (optional)

---

### Week 7-8: Push Workflow UI

#### Week 7: Pre-Push Validation & Preview
**Goals:**
- Create push preparation view
- Implement validation display
- Add conflict detection preview

**Tasks:**
1. Push view implementation
2. Validation worker
3. Conflict preview

**Deliverables:**
- [ ] Push view layout
- [ ] Configuration selection
- [ ] Validation display
- [ ] Conflict preview

#### Week 8: Conflict Resolution & Execution
**Goals:**
- Create conflict resolution dialog
- Implement push worker
- Add push progress tracking

**Tasks:**
1. Conflict resolution UI
2. Push worker thread
3. Result reporting

**Deliverables:**
- [ ] Conflict resolution dialog
- [ ] Push worker thread
- [ ] Push progress tracking
- [ ] Success/failure reporting

---

### Week 9-10: Polish & Testing

#### Week 9: Error Handling & UX
**Goals:**
- Improve error messages
- Add help system
- Enhance user experience

**Tasks:**
- Comprehensive error handling
- Tooltips and help text
- Keyboard shortcuts
- UI polish

**Deliverables:**
- [ ] Error message system
- [ ] Help/documentation integration
- [ ] Keyboard shortcuts
- [ ] UI refinements

#### Week 10: Testing & Documentation
**Goals:**
- Complete GUI testing
- Write user documentation
- Package application

**Tasks:**
- GUI unit tests
- Integration tests
- User guide
- Installation guide

**Deliverables:**
- [ ] Test suite
- [ ] User documentation
- [ ] Installation package
- [ ] Release candidate

---

## Technical Specifications

### Threading Model

```python
# Main thread: UI updates
# Worker threads: Long-running operations

# Example pattern:
class OperationWorker(QThread):
    finished = pyqtSignal(object)
    error = pyqtSignal(str)
    progress = pyqtSignal(int)
    
    def run(self):
        try:
            result = self.perform_operation()
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))
```

### State Management

```python
# gui/models/application_state.py
from PyQt6.QtCore import QObject, pyqtSignal

class ApplicationState(QObject):
    """Central state management."""
    
    authenticated = pyqtSignal(bool)
    config_loaded = pyqtSignal(dict)
    operation_started = pyqtSignal(str)
    operation_completed = pyqtSignal(str, object)
    
    def __init__(self):
        super().__init__()
        self.api_client = None
        self.current_config = None
        self.is_authenticated = False
```

### Styling

```css
/* gui/resources/styles/main.qss */
QMainWindow {
    background-color: #f5f5f5;
}

QPushButton {
    background-color: #0078d4;
    color: white;
    border: none;
    padding: 8px 16px;
    border-radius: 4px;
}

QPushButton:hover {
    background-color: #106ebe;
}

QPushButton:disabled {
    background-color: #cccccc;
    color: #666666;
}
```

---

## Testing Strategy

### GUI Testing
```python
# tests/test_gui/test_main_window.py
import pytest
from PyQt6.QtWidgets import QApplication
from gui.main_window import MainWindow

@pytest.fixture
def app():
    app = QApplication([])
    yield app
    app.quit()

def test_main_window_creation(app):
    window = MainWindow()
    assert window.windowTitle() == "Prisma Access Configuration Manager"
    assert window.width() > 0
    assert window.height() > 0

def test_navigation(app):
    window = MainWindow()
    # Test navigation button clicks
    # Verify view switching
```

---

## Deployment

### Windows
```bash
# Build standalone executable
pyinstaller --name "PA Config Manager" \
            --windowed \
            --icon=icon.ico \
            gui/main.py
```

### macOS
```bash
# Build .app bundle
pyinstaller --name "PA Config Manager" \
            --windowed \
            --icon=icon.icns \
            --osx-bundle-identifier=com.paconfig.manager \
            gui/main.py
```

### Linux
```bash
# Build AppImage or deb package
pyinstaller --name "pa-config-manager" \
            --windowed \
            gui/main.py
```

---

## Success Criteria

- [ ] All views functional
- [ ] Thread-safe operations
- [ ] Responsive UI (no freezing)
- [ ] Comprehensive error handling
- [ ] Professional appearance
- [ ] Complete user documentation
- [ ] Successful test suite
- [ ] Packaged installers

---

## Post-Launch Enhancements

1. **Drag-and-drop configuration import**
2. **Configuration comparison tool**
3. **Scheduled pull operations**
4. **Multi-tenant management**
5. **Template library**
6. **Configuration analytics dashboard**

---

## Conclusion

This GUI integration plan provides a comprehensive roadmap for adding a professional user interface to the Prisma Access Configuration Capture system. The PyQt6-based architecture leverages the existing modular backend while providing a modern, user-friendly experience.

**Next Steps:**
1. Complete security hardening (2-3 weeks)
2. Begin GUI development (Week 1-2 foundation)
3. Iterative development with user feedback
4. Testing and refinement
5. Production deployment

**Total Timeline:** 10-12 weeks after security hardening complete
