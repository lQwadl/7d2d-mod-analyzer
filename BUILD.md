# Release Build Guide for 7d2d-mod-manager

This guide walks you through building a clean, Release-mode executable without any packaging, compression, or obfuscation.

## Build Overview

- **Output:** Single standalone `app.exe` file
- **Mode:** Release (optimized, no debug symbols)
- **Packing:** None (no UPX or executable compression)
- **Size:** ~80-120 MB (larger than packed, but transparent and antivirus-safe)
- **Signing:** Not signed (you can optionally sign after building)

---

## Prerequisites

Ensure you have:
- Python 3.10+ installed
- `pip` package manager available
- Windows OS (for `.exe` output)

### Verify Python installation:
```bash
python --version
pip --version
```

Expected output:
- `Python 3.10.x` or later
- `pip 22.x` or later

---

## Step 1: Set Up Python Virtual Environment

A virtual environment isolates your build dependencies from system Python.

```bash
# Navigate to project root
cd c:\Users\gingt\Desktop\Work\7d2d-mod-manager

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On PowerShell:
.\venv\Scripts\Activate.ps1

# On CMD:
venv\Scripts\activate.bat
```

**Expected output:** Your terminal prompt should show `(venv)` prefix.

---

## Step 2: Install Build Dependencies

Install only the runtime dependencies (not dev dependencies):

```bash
# Upgrade pip to latest
pip install --upgrade pip

# Install PyInstaller (the build tool)
pip install pyinstaller

# Install project dependencies (if any from requirements.txt)
# If you have a requirements.txt or dependencies listed:
# pip install -r requirements.txt
# For now, PyInstaller will detect imports automatically

# Verify PyInstaller installation
pyinstaller --version
```

**Expected output:** PyInstaller version 6.x or later

### Minimal Dependency Check

Your project uses only standard library modules (tkinter, json, logging, pathlib, etc.) plus:
- `xml.etree.ElementTree` (standard library)
- Internal scanner/logic modules

These should be automatically detected by PyInstaller.

---

## Step 3: Verify app.spec Configuration

The PyInstaller spec file controls the build behavior. Verify it's configured for Release:

**File:** `app.spec`

Key settings to verify:

```python
# ✅ No UPX packing
upx=False

# ✅ No debug symbols
debug=False

# ✅ Not a console app (GUI-only)
console=False

# ✅ No stripping of binaries
strip=False

# ✅ Standard optimization
optimize=0
```

All these should already be correct from previous security updates.

---

## Step 4: Clean Previous Build Artifacts

Remove old build outputs to ensure a clean build:

```bash
# Remove previous build outputs
Remove-Item -Force -Recurse build -ErrorAction SilentlyContinue
Remove-Item -Force -Recurse dist -ErrorAction SilentlyContinue
Remove-Item -Force -Recurse __pycache__ -ErrorAction SilentlyContinue
Remove-Item -Force *.egg-info -ErrorAction SilentlyContinue

# Verify cleanup
ls -la | grep -E "(build|dist)"
```

Expected: No build/dist folders

---

## Step 5: Build the Release Executable

Execute PyInstaller with the configured spec file:

```bash
# Build using app.spec (Release mode)
pyinstaller app.spec --clean --noconfirm

# Progress output will show:
# - Analysis: finding imports
# - Compile: bytecode generation
# - Dependency Analysis
# - Building: creating executable
# - Completed!
```

Build time: **2-5 minutes** depending on your system

**Expected output:**
```
Building EXE from EXE-00.toc completed successfully.
```

---

## Step 6: Verify the Build

Check what was created:

```bash
# List dist folder contents
ls -la dist/

# Check executable properties
file dist/app.exe
Get-Item dist/app.exe | Select Length, CreationTime
```

**Expected output:**
- `dist/app.exe` exists (~80-120 MB)
- `dist` folder contains support files (Python runtime, libraries)

### Verify Executable is Not Packed:

```bash
# Check file signature (should NOT mention UPX)
strings dist/app.exe | Select-String -Pattern "UPX|packed|compressed" -ErrorAction SilentlyContinue

# If nothing returned = Good! (No packing detected)

# Check file type
file dist/app.exe
# Should show: PE32+ executable (console)
```

---

## Step 7: Test the Executable

### Quick functionality test:

```bash
# Test GUI startup (will open window)
dist/app.exe

# If window opens and is responsive = Success!
# Close window when done
```

### Test CLI mode:

```bash
# Test CLI without path (should show error about no mods_path)
dist/app.exe --cli

# Expected: "No mods path specified. Set mods_path in config.json..."
```

### Test with config:

```bash
# Set a valid mods path in config.json first:
# {
#   "mods_path": "C:/Path/To/Your/Mods"
# }

# Then run CLI analysis:
dist/app.exe --cli
```

---

## Step 8: Prepare for Distribution

### Create a distribution package:

```bash
# Create a release directory
mkdir app-release
cd app-release

# Copy the executable and required files
Copy-Item ..\dist\app.exe .
Copy-Item ..\config.json .
Copy-Item ..\SECURITY.md .
Copy-Item ..\README.md . -ErrorAction SilentlyContinue

# Create a setup batch file for first-time users
```

### Create `setup.bat` for end users:

Create file `setup.bat`:
```batch
@echo off
REM First-time setup for 7d2d-mod-manager

echo.
echo ========================================
echo 7d2d-mod-manager - Initial Setup
echo ========================================
echo.

echo Please edit config.json to set your Mods directory.
echo Example:
echo   "mods_path": "C:/Program Files/Steam/steamapps/common/7 Days To Die/Mods"
echo.

pause
```

---

## Step 9: Verify Antivirus Compatibility

Before distribution, verify the executable is clean:

```bash
# Use Windows Defender scan (built-in)
# Right-click app.exe > Scan with Windows Defender

# For online verification (optional):
# Upload to https://www.virustotal.com/
# Paste dist/app.exe
# Should show minimal/no detections
```

---

## Step 10: Optional - Code Sign the Executable

For additional trust, you can optionally sign the executable (requires certificate):

```bash
# This requires a code signing certificate
# SignTool is included in Windows SDK

signtool sign /f certificate.pfx /p password /t http://timestamp.server.com dist/app.exe
```

(Skip this if you don't have a code signing certificate)

---

## Troubleshooting

### Issue: "pyinstaller: command not recognized"

**Solution:**
```bash
# Ensure venv is activated (should see (venv) in prompt)
# If not:
.\venv\Scripts\Activate.ps1
```

### Issue: Build fails with import errors

**Solution:**
```bash
# Check for hidden imports
pyinstaller app.spec --clean --noconfirm --debug imports

# If specific module missing, add to app.spec:
# hiddenimports=['module_name']
```

### Issue: Executable is too large (>150 MB)

**Solution:**
This is normal for standalone Python executables. The size includes:
- Python runtime (~60 MB)
- Tkinter library (~20-30 MB)
- Dependencies and bytecode (~10-20 MB)

This is expected and antivirus-safe. Compression with UPX would reduce size but cause false positives.

### Issue: "No mods path specified" when running

**Solution:**
1. Edit `config.json`:
   ```json
   {
     "mods_path": "C:/Your/Mods/Path"
   }
   ```
2. Or use GUI and select directory when prompted

### Issue: Antivirus flags the executable

**Solution:**
1. Verify `upx=False` in `app.spec`
2. Verify `debug=False` and `strip=False`
3. Check `SECURITY.md` - confirm only standard file I/O
4. Try uploading to VirusTotal for detailed report
5. If false positive, can report to antivirus vendor

---

## Build Commands Reference

### Quick rebuild (after code changes):
```bash
# Activate venv
.\venv\Scripts\Activate.ps1

# Rebuild
pyinstaller app.spec --clean --noconfirm

# Done - executable in dist/app.exe
```

### Clean and full rebuild:
```bash
.\venv\Scripts\Activate.ps1
Remove-Item -Force -Recurse build, dist, __pycache__ -ErrorAction SilentlyContinue
pyinstaller app.spec --clean --noconfirm
```

### View build details:
```bash
pyinstaller app.spec --analyze
```

---

## File Structure After Build

```
7d2d-mod-manager/
├── app.spec                 # Build configuration
├── dist/
│   ├── app.exe             # ✅ Your Release executable
│   └── _internal/          # Python runtime & dependencies
├── build/                  # Intermediate build files
├── main.py                 # Entry point
├── config.json             # User configuration
└── gui/                    # Source code
    └── app.py              # GUI entry point
```

---

## Verification Checklist

- [ ] Virtual environment activated (`(venv)` in prompt)
- [ ] PyInstaller installed (`pyinstaller --version`)
- [ ] `app.spec` has `upx=False`
- [ ] Previous builds cleaned (no old dist/ folder)
- [ ] Build completed without errors
- [ ] `dist/app.exe` exists and is ~80-120 MB
- [ ] Executable runs without UPX warnings
- [ ] GUI launches successfully
- [ ] CLI mode responds correctly
- [ ] `config.json` is configured with valid mods path

---

## Next Steps

1. **Create distribution package** (optional)
   - Copy `dist/app.exe` to a release directory
   - Include `config.json`, `SECURITY.md`, `README.md`
   - Create `setup.bat` for end users

2. **Test on different systems** (optional)
   - Run on a machine without Python installed
   - Verify .NET Framework version compatibility (if needed)

3. **Submit to VirusTotal** (optional)
   - For additional confidence in antivirus compatibility
   - Share results with potential users

4. **Sign the executable** (optional)
   - Add authenticode signature if distributing to others
   - Requires code signing certificate

---

## Notes

- The executable is **standalone** - no Python installation needed on target system
- **File size** is larger (~100 MB) but this is normal and doesn't indicate bloat
- **No compression** means better antivirus compatibility
- **Debug disabled** means better performance
- **Console disabled** means GUI mode only (CLI available via command-line args)

For questions or issues, check `SECURITY.md` for file access details or `main.py` for entry point logic.
