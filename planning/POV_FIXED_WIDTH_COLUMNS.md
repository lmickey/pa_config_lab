# Fixed Width Columns for Configuration Sources ✅

**Date:** December 20, 2024  
**Issue:** Checking items in left column shifted the right column

---

## Problem

When checking a checkbox in the left column, the entire right column would shift horizontally because the layout was using flexible sizing with stretch factors.

---

## Solution

Set **fixed widths** for both columns using QWidget containers:

```python
# Left column
left_widget = QWidget()
left_widget.setMinimumWidth(350)
left_widget.setMaximumWidth(450)

# Right column  
right_widget = QWidget()
right_widget.setMinimumWidth(350)
right_widget.setMaximumWidth(450)
```

---

## Changes Made

1. **Wrapped each column in a QWidget** with fixed size constraints
2. **Set minimum width: 350px** - Ensures enough space for content
3. **Set maximum width: 450px** - Prevents excessive stretching
4. **Added stretch to layout** - Uses remaining horizontal space

---

## Result

✅ **Left column:** Fixed at 350-450px width  
✅ **Right column:** Fixed at 350-450px width  
✅ **No shifting:** Checking boxes doesn't affect layout  
✅ **Aligned:** Both columns stay perfectly aligned

---

## Visual Layout

```
┌─────────────────────┬─────────────────────┐
│  Left (350-450px)   │  Right (350-450px)  │ ← Fixed widths
├─────────────────────┼─────────────────────┤
│ ☑ SPOV Questionnaire│ ☐ Existing JSON     │ ← No shifting!
│ [Browse...] _______ │ [Browse...] _______ │
│                     │                     │
│ ☐ Terraform Config  │ ☐ Manual Entry      │
│ [Browse...] _______ │ (Open dialog)       │
└─────────────────────┴─────────────────────┘
```

---

## Status

✅ **Fixed widths set**  
✅ **No layout shifting**  
✅ **Proper alignment**  
✅ **Professional appearance**

---

**Now checking/unchecking items won't cause any layout shifts!** 🎉
