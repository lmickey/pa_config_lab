# How to Run the GUI - IMPORTANT!

## ⚠️ CRITICAL: Do NOT use `python3` to run `.sh` files!

The file `run_gui.sh` is a **bash script**, not a Python script.

## ✅ Correct Ways to Run:

### Option 1: Run with bash (Recommended)
```bash
bash run_gui.sh
```

### Option 2: Make executable and run directly
```bash
chmod +x run_gui.sh
./run_gui.sh
```

### Option 3: Use sh
```bash
sh run_gui.sh
```

## ❌ WRONG Ways (Don't do this!):

```bash
python3 run_gui.sh    # ❌ WRONG - This is a bash script!
python run_gui.sh     # ❌ WRONG - This is a bash script!
```

## Why the Error Happens

When you run `python3 run_gui.sh`, Python tries to parse the bash script as Python code. That's why you see:
```
SyntaxError: invalid syntax
```

The bash syntax `$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)` is not valid Python syntax!

## Quick Test

Try this right now:
```bash
cd ~/Code/pa_config_lab
bash run_gui.sh
```

This should work! The script will:
1. Activate the virtual environment
2. Run the GUI
3. Deactivate when done

## Alternative: Run Python Directly

If the script still doesn't work, you can run Python directly:

```bash
cd ~/Code/pa_config_lab
source venv/bin/activate
python3 pa_config_gui.py
```

But remember: **`.sh` files are bash scripts, not Python scripts!**
