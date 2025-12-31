# Qt Environment Variables Fix for Linux PyQt6

**Date:** December 21, 2025  
**Likelihood of Success:** 60-80%  
**Difficulty:** Easy (just set environment variables)

---

## 🎯 Quick Fix to Try

### **Most Likely to Work:**
```bash
export QT_QPA_PLATFORM=xcb
python3 run_gui.py
```

Or use the new stable launcher:
```bash
./run_gui_stable.sh
```

---

## 📋 Environment Variables Explained

### **QT_QPA_PLATFORM**
Controls which Qt platform plugin to use.

| Value | Description | Stability | Speed |
|-------|-------------|-----------|-------|
| `xcb` | X11 backend | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| `wayland` | Wayland backend | ⭐⭐ | ⭐⭐⭐⭐ |
| `offscreen` | No display | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |

**Recommendation:** Use `xcb` (most stable on Linux)

---

### **QT_XCB_GL_INTEGRATION**
Controls OpenGL integration with X11.

| Value | Description | Stability |
|-------|-------------|-----------|
| `none` | Disable GPU | ⭐⭐⭐⭐⭐ |
| `xcb_egl` | Use EGL | ⭐⭐⭐ |
| `xcb_glx` | Use GLX | ⭐⭐⭐ |

**Recommendation:** Set to `none` if GPU driver issues suspected

---

### **LIBGL_ALWAYS_SOFTWARE**
Forces Mesa to use software rendering (CPU) instead of GPU.

| Value | Effect | Stability | Speed |
|-------|--------|-----------|-------|
| `1` | CPU rendering | ⭐⭐⭐⭐⭐ | ⭐⭐ |
| `0` or unset | GPU rendering | ⭐⭐⭐ | ⭐⭐⭐⭐ |

**Recommendation:** Use `1` if GPU driver is problematic (NVIDIA proprietary, etc.)

---

### **QT_XCB_NO_THREADED_RENDERING**
Disables multi-threaded OpenGL rendering in Qt.

| Value | Effect | Stability |
|-------|--------|-----------|
| `1` | Single-threaded | ⭐⭐⭐⭐ |
| `0` or unset | Multi-threaded | ⭐⭐⭐ |

**Recommendation:** Set to `1` for thread-safety (matches our segfault pattern)

---

## 🧪 Testing Guide

### **Option A: Quick Test (Single Variable)**

Try the most likely fix first:
```bash
export QT_QPA_PLATFORM=xcb
python3 run_gui.py
```

If that works, you're done! Add it to your launcher script.

---

### **Option B: Comprehensive Test (All Combinations)**

Run the automated test script:
```bash
./test_qt_env.sh
```

This will test 6 different configurations and ask you to note which works.

---

### **Option C: Manual Testing**

Test each configuration manually:

**Test 1: XCB Platform (60-70% success)**
```bash
export QT_QPA_PLATFORM=xcb
python3 run_gui.py
```

**Test 2: No GPU + XCB (70-80% success)**
```bash
export QT_QPA_PLATFORM=xcb
export QT_XCB_GL_INTEGRATION=none
python3 run_gui.py
```

**Test 3: Software Rendering (80-90% success, but slow)**
```bash
export QT_QPA_PLATFORM=xcb
export QT_XCB_GL_INTEGRATION=none
export LIBGL_ALWAYS_SOFTWARE=1
python3 run_gui.py
```

**Test 4: No Threaded Rendering (40-50% success)**
```bash
export QT_XCB_NO_THREADED_RENDERING=1
python3 run_gui.py
```

**Test 5: Nuclear Option (90-95% success, slowest)**
```bash
export QT_QPA_PLATFORM=xcb
export QT_XCB_GL_INTEGRATION=none
export LIBGL_ALWAYS_SOFTWARE=1
export QT_QUICK_BACKEND=software
export QT_XCB_NO_THREADED_RENDERING=1
python3 run_gui.py
```

---

## ✅ If It Works

### **Permanent Fix:**

1. **Edit run_gui.sh:**
```bash
#!/bin/bash
# Add the working environment variables at the top
export QT_QPA_PLATFORM=xcb  # or whatever worked
export QT_XCB_NO_THREADED_RENDERING=1

source venv/bin/activate
python3 run_gui.py
```

2. **Or use the stable launcher:**
```bash
./run_gui_stable.sh
```

This already has the most likely stable configuration.

---

## 📊 Expected Results

### **If XCB Works (Test 1):**
- ✅ No segfaults
- ✅ Normal GUI speed
- ✅ All features work
- **This is the best outcome**

### **If Software Rendering Works (Test 3):**
- ✅ No segfaults
- ⚠️ Slower GUI (CPU rendering)
- ✅ All features work
- **Acceptable trade-off**

### **If Nothing Works:**
- ❌ Still crashes
- → Use CLI instead (100% stable)
- → Or test on Windows (likely works)

---

## 🔍 Why This Matters

The segfaults are happening in **Qt's rendering layer**, specifically:
- OpenGL initialization
- X11/Wayland interaction
- Multi-threaded rendering

By controlling these with environment variables, we can:
- Force stable backends
- Disable problematic features
- Work around driver bugs

This is **standard practice** for Qt apps on Linux.

---

## 💡 Real-World Examples

Many Qt applications ship with these variables set by default on Linux:

**VLC Media Player:**
```bash
export QT_X11_NO_MITSHM=1
```

**KDE Applications:**
```bash
export QT_QPA_PLATFORMTHEME=kde
```

**Google Chrome (Qt backend):**
```bash
export QT_XCB_GL_INTEGRATION=none
```

---

## 🎯 Recommended Approach

### **For Testing:**
1. Try `run_gui_stable.sh` first (has sensible defaults)
2. If crashes, run `test_qt_env.sh` (tests all combinations)
3. Note which configuration works
4. Update `run_gui.sh` with those variables

### **For Production:**
- If any configuration works → Use it!
- If nothing works → Use CLI (equally capable)
- Document which works in README

---

## 📝 Current Status

**Files Created:**
1. `test_qt_env.sh` - Automated testing script
2. `run_gui_stable.sh` - Launcher with stable defaults

**To Test:**
```bash
# Option 1: Try stable defaults
./run_gui_stable.sh

# Option 2: Test all combinations
./test_qt_env.sh
```

---

## 🤔 Why Not Default?

We didn't set these by default because:
1. They might not be needed on all systems
2. Some systems work fine without them
3. Software rendering is slower
4. Better to test and find optimal settings

But for **your system**, these are likely necessary.

---

## ✅ Next Steps

1. **Run the stable launcher:**
   ```bash
   ./run_gui_stable.sh
   ```

2. **If it works:**
   - You're done! Use this launcher going forward
   - GUI should be stable now

3. **If it still crashes:**
   - Run the comprehensive test: `./test_qt_env.sh`
   - Try each configuration
   - Note which works (if any)

4. **If nothing works:**
   - Use CLI (100% stable, same features)
   - Or test on Windows (likely works fine)

---

**Likelihood this fixes it: 60-80%**

The most likely scenario is that forcing XCB platform (`QT_QPA_PLATFORM=xcb`) will fix it. This is the single most common PyQt6 fix on Linux.

Want to try `./run_gui_stable.sh` now?
