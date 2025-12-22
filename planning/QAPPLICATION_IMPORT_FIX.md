# QApplication Import Fix

**Date:** December 21, 2025  
**Issue:** GUI crashed after authentication with "Unhandled Python exception"

---

## 🐛 **Problem**

The GUI was crashing immediately after authentication completed with:
```
Unhandled Python exception
Aborted
```

---

## 🔍 **Root Cause**

The `QApplication` class was being used in `_flush_pending_messages()` but was not imported at the module level:

```python
# In _flush_pending_messages():
QApplication.processEvents()  # ❌ QApplication not imported!
```

---

## 🔧 **Fix**

Added `QApplication` to the imports:

```python
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGroupBox,
    QCheckBox,
    QPushButton,
    QLabel,
    QProgressBar,
    QTextEdit,
    QMessageBox,
    QScrollArea,
    QApplication,  # ✅ Added
)
```

---

## ✅ **Status**

**Fixed:** `gui/pull_widget.py` now properly imports `QApplication`

**Ready for testing:**
```bash
./run_gui_wayland.sh
```

---

**Files Modified:**
- `gui/pull_widget.py` - Added QApplication import
