"""
Toast notification widget for non-intrusive success messages.

Provides a floating notification that appears in the corner,
stays for 1 second, then fades out over 1 second.
"""

from PyQt6.QtWidgets import QLabel, QGraphicsOpacityEffect, QWidget, QHBoxLayout, QPushButton, QVBoxLayout
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, pyqtProperty
from PyQt6.QtGui import QFont, QCursor


class ToastNotification(QLabel):
    """
    A toast notification widget that appears in the corner and fades out.
    
    Usage:
        toast = ToastNotification(parent_widget)
        toast.show_message("Configuration pulled successfully!", success=True)
    """
    
    def __init__(self, parent=None):
        """Initialize the toast notification."""
        super().__init__(parent)
        
        # Styling
        self.setStyleSheet("""
            QLabel {
                background-color: #2e7d32;
                color: white;
                padding: 15px 20px;
                border-radius: 8px;
                font-size: 14px;
                font-weight: bold;
            }
        """)
        
        # Position and appearance
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | 
            Qt.WindowType.Tool | 
            Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        
        # Opacity effect for fade animation
        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.opacity_effect)
        self.opacity_effect.setOpacity(1.0)
        
        # Animation
        self.fade_animation = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.fade_animation.setDuration(1000)  # 1 second fade
        self.fade_animation.setStartValue(1.0)
        self.fade_animation.setEndValue(0.0)
        self.fade_animation.setEasingCurve(QEasingCurve.Type.InOutQuad)
        self.fade_animation.finished.connect(self.hide)
        
        # Timers
        self.display_timer = QTimer(self)
        self.display_timer.setSingleShot(True)
        self.display_timer.timeout.connect(self._start_fade)
        
        self.hide()
    
    def show_message(self, message: str, success: bool = True, duration: int = 1000):
        """
        Show a toast notification.
        
        Args:
            message: Message to display
            success: True for success (green), False for error (red)
            duration: How long to display before fading (milliseconds)
        """
        # Set message
        self.setText(message)
        
        # Set color based on type
        if success:
            bg_color = "#2e7d32"  # Green
        else:
            bg_color = "#c62828"  # Red
        
        self.setStyleSheet(f"""
            QLabel {{
                background-color: {bg_color};
                color: white;
                padding: 15px 20px;
                border-radius: 8px;
                font-size: 14px;
                font-weight: bold;
            }}
        """)
        
        # Adjust size to content
        self.adjustSize()
        
        # Position in bottom-right corner of parent
        if self.parent():
            parent_rect = self.parent().rect()
            x = parent_rect.width() - self.width() - 20
            y = parent_rect.height() - self.height() - 20
            self.move(x, y)
        
        # Reset opacity and show
        self.opacity_effect.setOpacity(1.0)
        self.show()
        self.raise_()  # Bring to front (z-axis)
        
        # Start display timer
        self.display_timer.start(duration)
    
    def _start_fade(self):
        """Start the fade-out animation."""
        self.fade_animation.start()


class ToastManager:
    """
    Manages toast notifications for a parent widget.
    
    Usage:
        self.toast_manager = ToastManager(self)
        self.toast_manager.show_success("Operation completed!")
        self.toast_manager.show_error("Operation failed!")
    """
    
    def __init__(self, parent):
        """Initialize the toast manager."""
        self.parent = parent
        self.toast = ToastNotification(parent)
    
    def show_success(self, message: str, duration: int = 1000):
        """Show a success toast (green)."""
        self.toast.show_message(message, success=True, duration=duration)
    
    def show_error(self, message: str, duration: int = 2000):
        """Show an error toast (red) - stays longer by default."""
        self.toast.show_message(message, success=False, duration=duration)
    
    def show_info(self, message: str, duration: int = 1000):
        """Show an info toast (same as success for now)."""
        self.toast.show_message(message, success=True, duration=duration)


class DismissibleErrorNotification(QWidget):
    """
    A dismissible error notification that stays visible until user dismisses it.
    Shows errors with an X button in the corner.
    """
    
    def __init__(self, parent=None):
        """Initialize the dismissible error notification."""
        super().__init__(parent)
        
        # Window flags for floating overlay
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | 
            Qt.WindowType.Tool | 
            Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        
        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # Container widget for styling
        self.container = QWidget()
        self.container.setStyleSheet("""
            QWidget {
                background-color: #c62828;
                border-radius: 8px;
                padding: 15px;
            }
        """)
        
        container_layout = QHBoxLayout(self.container)
        container_layout.setContentsMargins(15, 15, 15, 15)
        
        # Error message label
        self.message_label = QLabel()
        self.message_label.setStyleSheet("""
            QLabel {
                color: white;
                font-size: 14px;
                font-weight: bold;
                background: transparent;
                padding: 0;
            }
        """)
        self.message_label.setWordWrap(True)
        self.message_label.setMaximumWidth(400)
        container_layout.addWidget(self.message_label)
        
        # Close button
        self.close_button = QPushButton("✕")
        self.close_button.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: white;
                border: none;
                font-size: 20px;
                font-weight: bold;
                padding: 0;
                margin-left: 10px;
                min-width: 20px;
                max-width: 20px;
                min-height: 20px;
                max-height: 20px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.2);
                border-radius: 10px;
            }
        """)
        self.close_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.close_button.clicked.connect(self.dismiss)
        container_layout.addWidget(self.close_button)
        
        main_layout.addWidget(self.container)
        
        self.hide()
    
    def show_error(self, message: str):
        """
        Show an error message that stays until dismissed.
        
        Args:
            message: Error message to display
        """
        self.message_label.setText(message)
        
        # Adjust size to content
        self.adjustSize()
        
        # Position in bottom-right corner of parent
        if self.parent():
            parent_rect = self.parent().rect()
            x = parent_rect.width() - self.width() - 20
            y = parent_rect.height() - self.height() - 20
            self.move(x, y)
        
        self.show()
        self.raise_()  # Bring to front
    
    def dismiss(self):
        """Dismiss the error notification."""
        self.hide()
