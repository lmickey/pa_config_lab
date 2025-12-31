# Converting Legacy .bin Files to JSON

Quick guide for converting your legacy encrypted .bin configuration files to the new JSON format.

---

## Why Convert?

- ✅ Use in POV Configuration workflow
- ✅ Human-readable format
- ✅ Version control friendly
- ✅ Compatible with all new features
- ✅ Optional encryption with stronger algorithm

---

## Quick Start

### Interactive Mode (Easiest)

```bash
python convert_legacy_to_json.py
```

Follow the prompts:
1. Enter path to your .bin file
2. Enter decryption password
3. Choose output filename (or press Enter for default)
4. Choose whether to encrypt output

**Example:**
```
$ python convert_legacy_to_json.py

============================================================
Legacy .bin to JSON Converter
============================================================

Enter path to legacy .bin file: myconfig-fwdata.bin
Enter decryption password: ********
Enter output JSON file [myconfig-fwdata.json]: ⏎
Encrypt output JSON? (y/N): n

Starting conversion...
✅ Conversion successful!
Output file: myconfig-fwdata.json
```

---

## Then Use It

### In GUI
1. Launch: `python run_gui.py`
2. Click **"🔧 POV Configuration"**
3. Select **"Load from JSON configuration file"**
4. Browse to your converted JSON file
5. Click **"Load Configuration"**
6. Done! ✅

---

## Advanced Usage

### Single File with Command Line
```bash
python convert_legacy_to_json.py input.bin output.json "mypassword"
```

### Batch Convert Multiple Files
```bash
python convert_legacy_to_json.py --batch ./old_configs ./new_configs
```
Enter password once, converts all .bin files in the directory.

---

## What Gets Converted?

**Your legacy .bin file contains:**
- Firewall data (fwData)
- Prisma Access data (paData)
- Configuration name

**New JSON format includes:**
- All legacy data preserved in `legacy_data` section
- Modern v2 schema structure
- Metadata with conversion notes
- Ready for POV Configuration workflow

---

## Troubleshooting

**Wrong password:**
```
❌ Conversion failed: Incorrect padding
```
→ Check your password and try again

**File not found:**
```
❌ File not found: myfile.bin
```
→ Check the file path

**Already converted?**
→ You only need to convert once! Use the JSON file directly.

---

## Quick Reference

```bash
# Interactive (recommended for first time)
python convert_legacy_to_json.py

# Command line
python convert_legacy_to_json.py old.bin new.json password

# Batch
python convert_legacy_to_json.py --batch ./old_dir ./new_dir
```

---

**Convert once, use forever!** 🎉
