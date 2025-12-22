# Batched GUI Updates - Segfault Prevention Fix

**Date:** December 21, 2025  
**Status:** ✅ Complete

---

## 🐛 **Problem**

After fixing the progress bar math to show all updates (removing the 10% filter), the GUI segfaulted again. The rapid GUI updates were triggering PyQt6/Qt6 threading issues.

### **The Trade-Off:**
- **Filter updates (every 10%)**: Stable but results window misses most updates ❌
- **Show all updates**: Complete visibility but causes segfaults ❌

---

## 💡 **Solution: Batched GUI Updates**

Instead of updating the results text widget on every progress callback (which can be 20-30+ times in rapid succession), we now:

1. **Queue messages** in a list
2. **Batch update** the GUI every 250ms using a QTimer
3. **Flush remaining messages** when pull completes

This provides:
- ✅ **All messages shown** (no filtering)
- ✅ **Stable GUI** (fewer rapid updates)
- ✅ **Better performance** (batch append is more efficient)

---

## 🔧 **Implementation**

### **1. Add QTimer Import**
```python
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
```

### **2. Initialize Batching in `__init__`**
```python
def __init__(self, parent=None):
    super().__init__(parent)
    
    # ... existing init ...
    
    # Batch GUI updates to prevent segfaults from rapid updates
    self.pending_messages = []
    self.update_timer = QTimer()
    self.update_timer.timeout.connect(self._flush_pending_messages)
    self.update_timer.setInterval(250)  # Update GUI every 250ms
```

### **3. Queue Messages Instead of Immediate Append**
```python
def _on_progress(self, message: str, percentage: int):
    """Handle progress updates - batched to prevent GUI overload."""
    try:
        # Update progress label and bar immediately (lightweight)
        self.progress_label.setText(message)
        self.progress_bar.setValue(percentage)
        
        # Queue message for batched update (prevents rapid GUI updates)
        self.pending_messages.append(f"[{percentage}%] {message}")
        
        # Start timer if not already running
        if not self.update_timer.isActive():
            self.update_timer.start()
    
    except RuntimeError as e:
        print(f"Progress update error: {e}")
```

### **4. Batch Flush Messages Every 250ms**
```python
def _flush_pending_messages(self):
    """Flush all pending messages to results text widget in one batch."""
    if not self.pending_messages:
        return
    
    try:
        # Append all pending messages at once (more efficient)
        self.results_text.append("\n".join(self.pending_messages))
        self.pending_messages.clear()
        
        # Force GUI to process events
        QApplication.processEvents()
    
    except RuntimeError as e:
        print(f"Batch update error: {e}")
```

### **5. Flush Remaining Messages on Completion**
```python
def _on_pull_finished(self, success: bool, message: str, config: Optional[Dict]):
    """Handle pull completion."""
    try:
        # Stop update timer and flush any remaining messages
        self.update_timer.stop()
        self._flush_pending_messages()
        
        # Re-enable UI
        self._set_ui_enabled(True)
        
        # ... rest of completion handling ...
```

---

## 📊 **How It Works**

### **Timeline Example:**

```
Time 0ms:     Progress: "Folder 1/7 - Rules (1/3)"
              Action:    Queue message, start timer

Time 50ms:    Progress: "Folder 1/7 - Objects (2/3)"
              Action:    Queue message (timer already running)

Time 100ms:   Progress: "Folder 1/7 - Profiles (3/3)"
              Action:    Queue message (timer already running)

Time 150ms:   Progress: "Folder 2/7 - Rules (1/3)"
              Action:    Queue message (timer already running)

Time 250ms:   Timer fires!
              Action:    Flush all 4 queued messages at once
                        - "[12%] Folder 1/7 - Rules (1/3)"
                        - "[15%] Folder 1/7 - Objects (2/3)"
                        - "[18%] Folder 1/7 - Profiles (3/3)"
                        - "[21%] Folder 2/7 - Rules (1/3)"

Time 300ms:   Progress: "Folder 2/7 - Objects (2/3)"
              Action:    Queue message, timer continues

Time 500ms:   Timer fires again!
              Action:    Flush accumulated messages
```

---

## ✅ **Benefits**

### **1. Stability**
- Reduces GUI update frequency from 20-30+ per second to 4 per second (250ms intervals)
- Prevents Qt threading issues caused by rapid updates
- Much less likely to trigger segfaults

### **2. Complete Visibility**
- Still shows all progress messages
- No filtering or missing updates
- Results window has full details

### **3. Better Performance**
- Batch append is more efficient than individual appends
- Reduces GUI rendering overhead
- Smoother user experience

### **4. Responsive Progress Bar**
- Progress label and bar update immediately (lightweight operations)
- Users see real-time progress
- Only text area batching is batched (the heavy operation)

---

## 🎨 **User Experience**

### **What Users See:**

**Progress Bar & Label:**
- ✅ Updates immediately on every progress call
- ✅ Smooth, real-time feedback

**Results Text Window:**
- ✅ Updates every 250ms with accumulated messages
- ✅ All messages eventually appear
- ✅ Slight delay (max 250ms) is imperceptible to users

**Example Results Window Output:**
```
[10%] Initializing pull operation...
[12%] Folder 1/7: Shared - Capturing rules (1/3)
[15%] Folder 1/7: Shared - Capturing objects (2/3)
[18%] Folder 1/7: Shared - Capturing profiles (3/3)
← All 4 messages appear together after 250ms batch

[21%] Folder 2/7: Remote Networks - Capturing rules (1/3)
[24%] Folder 2/7: Remote Networks - Capturing objects (2/3)
[27%] Folder 2/7: Remote Networks - Capturing profiles (3/3)
← Next batch of messages
```

---

## 🔍 **Technical Details**

### **Why 250ms?**
- Fast enough to feel responsive (4 updates per second)
- Slow enough to batch multiple messages (typical folder takes ~1-2 seconds)
- Good balance between stability and user experience

### **Why Batch Append Works Better:**
```python
# Before (❌ Rapid updates)
for msg in messages:
    text_widget.append(msg)  # Triggers repaint 30 times

# After (✅ Batched)
text_widget.append("\n".join(messages))  # Triggers repaint once
```

### **Timer Behavior:**
- Timer only runs while pull is active
- Automatically restarts after each flush
- Stops when pull completes
- Final flush ensures no messages are lost

---

## 🧪 **Testing**

### **Test Scenario:**
1. Run GUI pull with 7 folders
2. Verify all ~21 folder messages appear in results window
3. Verify progress bar updates smoothly
4. **Most Important:** Verify NO segfaults during pull

### **Expected Behavior:**
- ✅ Progress bar moves smoothly (immediate updates)
- ✅ Results window shows all messages (batched every 250ms)
- ✅ No segfaults during or after pull
- ✅ Pull completes successfully with all data

---

## 📝 **Related Files**

- `gui/pull_widget.py` - Implemented batched GUI updates

---

## 📋 **Comparison: Before vs After**

| Aspect | Direct Updates | Batched Updates |
|--------|---------------|-----------------|
| **Update Frequency** | 20-30+ per second | 4 per second |
| **Segfault Risk** | High ⚠️ | Low ✅ |
| **All Messages Shown** | Yes ✅ | Yes ✅ |
| **Progress Bar** | Immediate ✅ | Immediate ✅ |
| **Performance** | Many repaints ⚠️ | Efficient ✅ |
| **User Experience** | Responsive ✅ | Responsive ✅ |

---

## 🎯 **Success Criteria**

- ✅ GUI pull completes without segfaults
- ✅ All progress messages appear in results window
- ✅ Progress bar updates smoothly
- ✅ No noticeable lag or delay
- ✅ Stable across multiple pull operations

---

**Status:** ✅ Implementation Complete - Ready for Testing  
**Impact:** Critical - Fixes segfault issue while maintaining complete visibility
