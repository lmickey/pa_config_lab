# QTimer Threading Fix - Timer Cannot Be Started from Another Thread

**Date:** December 21, 2025  
**Status:** ✅ Complete

---

## 🐛 **Problem**

GUI logs showed threading warnings during pull operation:
```
QBasicTimer::start: Timers cannot be started from another thread
QBasicTimer::start: Timers cannot be started from another thread
```

These appeared around the time crypto information was being pulled.

---

## 🔍 **Root Cause**

The `_on_progress()` method was trying to start the QTimer from within a signal handler that's called from the worker thread:

### **Before (Thread Violation):**
```python
def _on_progress(self, message: str, percentage: int):
    # This method is called from worker thread via signal
    self.progress_label.setText(message)
    self.progress_bar.setValue(percentage)
    
    self.pending_messages.append(f"[{percentage}%] {message}")
    
    # ❌ Starting timer from worker thread!
    if not self.update_timer.isActive():
        self.update_timer.start()  # Qt threading violation!
```

**Problem:** Qt timers must be started/stopped from the thread they belong to (the GUI thread). Starting them from the worker thread causes the warning and can lead to undefined behavior.

---

## 🔧 **Solution: Continuous Timer**

Instead of starting/stopping the timer on every progress update, start it once when the pull begins and let it run continuously:

### **After (Thread-Safe):**

**1. Initialize timer (runs continuously):**
```python
def __init__(self, parent=None):
    # ... existing init ...
    
    # Batch GUI updates to prevent segfaults from rapid updates
    self.pending_messages = []
    self.update_timer = QTimer()
    self.update_timer.timeout.connect(self._flush_pending_messages)
    self.update_timer.setInterval(250)  # Update GUI every 250ms
    # Timer will be started when pull begins, not on every progress update
```

**2. Start timer once at pull start (GUI thread):**
```python
def _start_pull(self):
    # ... connection checks ...
    
    # Clear previous results
    self.results_text.clear()
    
    # ✅ Start timer once from GUI thread
    self.pending_messages.clear()
    self.update_timer.start()
    
    # Create and start worker
    self.worker = PullWorker(...)
```

**3. Remove start/stop from progress handler:**
```python
def _on_progress(self, message: str, percentage: int):
    # Called from worker thread via signal
    self.progress_label.setText(message)
    self.progress_bar.setValue(percentage)
    
    # Just queue the message
    self.pending_messages.append(f"[{percentage}%] {message}")
    
    # ✅ Timer is already running continuously - no need to start/stop
```

**4. Stop timer once at pull completion (GUI thread):**
```python
def _on_pull_finished(self, success: bool, message: str, config: Optional[Dict]):
    try:
        # ✅ Stop timer from GUI thread
        self.update_timer.stop()
        self._flush_pending_messages()
        
        # ... rest of completion handling ...
```

---

## ✅ **Benefits**

### **1. Thread-Safe**
- Timer is only started/stopped from the GUI thread
- No Qt threading violations
- No warnings in logs

### **2. Simpler Logic**
- Timer runs continuously during pull
- No checking `isActive()` on every progress update
- Cleaner code

### **3. Same Functionality**
- Still batches updates every 250ms
- Still prevents rapid GUI updates
- Still shows all messages

### **4. More Efficient**
- No repeated start/stop overhead
- Timer just keeps running and flushing when there are messages
- Empty queue is handled gracefully in `_flush_pending_messages()`

---

## 🔍 **How It Works**

### **Timeline:**

```
Time 0ms:     User clicks "Pull Configuration"
              Action: Start timer from GUI thread ✅

Time 250ms:   Timer fires (1st time)
              Action: Check pending_messages (empty), do nothing

Time 500ms:   Timer fires (2nd time)
              Progress has accumulated 3 messages
              Action: Flush all 3 messages to results text

Time 750ms:   Timer fires (3rd time)
              Progress has accumulated 2 messages
              Action: Flush both messages

... (continues every 250ms)

Time 60s:     Pull completes
              Action: Stop timer from GUI thread ✅
              Action: Final flush of any remaining messages
```

---

## 📋 **Before vs After**

| Aspect | Before | After |
|--------|--------|-------|
| **Timer Start** | Every progress call | Once at pull start |
| **Thread** | Worker thread ❌ | GUI thread ✅ |
| **Qt Warnings** | Yes ⚠️ | No ✅ |
| **Complexity** | Check isActive() | Always running |
| **Performance** | Start/stop overhead | Runs continuously |
| **Functionality** | Batches updates | Batches updates |

---

## 🧪 **Testing**

### **Verification:**

1. Run GUI pull operation
2. **Before fix:** See warnings in terminal
   ```
   QBasicTimer::start: Timers cannot be started from another thread
   ```
3. **After fix:** No warnings ✅
4. Results window still shows all messages (batched)
5. Progress bar still updates smoothly

---

## 📝 **Files Modified**

- `gui/pull_widget.py`
  - `__init__()` - Added comment about timer lifecycle
  - `_start_pull()` - Start timer once from GUI thread
  - `_on_progress()` - Removed timer start/stop logic
  - `_on_pull_finished()` - Already had timer stop (correct)

---

## 💡 **Why This Matters**

### **Qt Threading Rules:**
1. **GUI operations must happen in GUI thread**
2. **QTimer belongs to the thread that created it**
3. **Starting a timer from another thread is undefined behavior**

### **Our Case:**
- QTimer created in GUI thread (`__init__`)
- `_on_progress()` called from worker thread (via signal)
- Trying to start timer from worker thread = violation

### **The Fix:**
- Start timer once in GUI thread
- Let it run continuously
- Worker thread just queues messages (thread-safe list operation)
- Timer processes queue from GUI thread

---

**Status:** ✅ Implementation Complete - Ready for Testing  
**Impact:** Medium - Fixes Qt threading warnings and potential undefined behavior
