# Release Build Quick Reference

## One-Line Build Command (for reference)

```powershell
.\venv\Scripts\Activate.ps1; pip install --upgrade pyinstaller; Remove-Item -Force -Recurse build, dist, __pycache__ -ErrorAction SilentlyContinue; pyinstaller app.spec --clean --noconfirm
```

---

## Step-by-Step Instructions (Copy & Paste)

### Terminal 1: Setup & Install

```powershell
# 1. Navigate to project root
cd c:\Users\gingt\Desktop\Work\7d2d-mod-analyzer

# 2. Create virtual environment (one-time only)
python -m venv venv

# 3. Activate virtual environment
.\venv\Scripts\Activate.ps1

# 4. Install PyInstaller
pip install --upgrade pyinstaller

# 5. Verify installation
pyinstaller --version
```

**Expected:** Version 6.x or later shown

---

### Terminal 2: Clean & Build

```powershell
# 1. Activate virtual environment
cd c:\Users\gingt\Desktop\Work\7d2d-mod-analyzer
.\venv\Scripts\Activate.ps1

# 2. Clean previous builds
Remove-Item -Force -Recurse build, dist, __pycache__ -ErrorAction SilentlyContinue

# 3. Start build
pyinstaller app.spec --clean --noconfirm

# Wait for completion (2-5 minutes)
# Progress messages will show: Analyzing → Compiling → Building → Done
```

**Expected output ends with:**
```
Building EXE from EXE-00.toc completed successfully.
```

---

### Terminal 3: Verify Build

```powershell
# 1. Check it exists
ls dist/app.exe

# 2. Check file info
Get-Item dist/app.exe | Select Length, CreationTime

# 3. Verify no packing (should return nothing)
strings dist/app.exe | Select-String "UPX"

# 4. Test GUI (will open window)
dist/app.exe

# Close window when ready
```

---

## Before You Start

### Prerequisites Checklist

- [ ] Python 3.10+ installed
  - Verify: `python --version`
- [ ] pip available
  - Verify: `pip --version`
- [ ] Project folder exists: `c:\Users\gingt\Desktop\Work\7d2d-mod-analyzer`
- [ ] Files present:
  - [ ] `app.spec` (PyInstaller config)
  - [ ] `gui/app.py` (GUI entry point)
  - [ ] `main.py` (CLI entry point)
  - [ ] `config.json` (Settings)

### Configuration Checklist

- [ ] `app.spec` has `upx=False` ✅
- [ ] `app.spec` has `debug=False` ✅
- [ ] `app.spec` has `console=False` ✅
- [ ] `config.json` is readable (empty or has valid `mods_path`)
- [ ] `SECURITY.md` is present (documents what app does)

---

## Build Output Structure

After successful build, you'll have:

```
7d2d-mod-analyzer/
├── dist/
│   ├── app.exe                    ← YOUR RELEASE EXECUTABLE
│   ├── _internal/                 ← Python runtime & libraries
│   │   ├── python312.dll
│   │   ├── tcl/                   ← Tkinter data
│   │   └── ... (many support files)
│   └── (other support files)
├── build/                         ← Intermediate files (can delete)
├── app.spec                       ← Build config (used by pyinstaller)
└── (source code)
```

---

## Testing Checklist

After build completes:

```powershell
# Test 1: Executable exists and is reasonable size
ls dist/app.exe
# Should show: ~80-120 MB (normal for Python standalone)

# Test 2: No UPX packing
strings dist/app.exe | Select-String "UPX"
# Should return: (nothing - no results)

# Test 3: GUI launches
dist/app.exe
# Action: Window should appear and be responsive
# Action: Close window

# Test 4: CLI responds to arguments
dist/app.exe --cli
# Expected: Error message about mods_path OR analysis output (if config set)

# Test 5: Check SECURITY.md verifies expected access
cat SECURITY.md
# Verify: "No network access", "No Registry access", "Read XML only"
```

---

## Distribution Package

To create a distribution folder for sharing:

```powershell
# 1. Create distribution folder
mkdir app-release
cd app-release

# 2. Copy necessary files
Copy-Item ../dist/app.exe .
Copy-Item ../config.json .
Copy-Item ../SECURITY.md .
Copy-Item ../BUILD.md .

# 3. Create simple setup.bat for users
@"
@echo off
echo 7d2d-mod-analyzer - Setup Complete
echo.
echo Step 1: Open config.json in notepad
echo Step 2: Set mods_path to your 7 Days to Die Mods directory
echo Step 3: Save and close
echo Step 4: Run app.exe
pause
"@ | Out-File setup.bat -Encoding ASCII

# 4. Your distribution is ready in app-release/
ls
```

Result folder structure for distribution:
```
app-release/
├── app.exe               ← Send this to users
├── config.json           ← Users edit this
├── setup.bat             ← Users run this first
├── SECURITY.md           ← Privacy/permission info
└── BUILD.md              ← Technical details (optional)
```

---

## Troubleshooting Quick Fixes

| Problem | Solution |
|---------|----------|
| `pyinstaller not found` | Run: `pip install pyinstaller` |
| `Module not found` | Ensure venv is activated (see `(venv)` prefix) |
| `Permission denied` | Delete dist/ folder and rebuild |
| `Build failed` | Run: `pyinstaller app.spec --clean --noconfirm --debug imports` |
| `Antivirus flag` | Verify `upx=False` in app.spec, upload to VirusTotal |
| `No mods_path` | Edit config.json with valid directory path |
| `Executable too large` | Normal (Python runtime + libraries = ~100MB) |

---

## Quick Rebuild (After Code Changes)

```powershell
# If you make code changes, rebuild quickly:
.\venv\Scripts\Activate.ps1
pyinstaller app.spec --clean --noconfirm

# New executable: dist/app.exe
```

---

## What NOT to Do

❌ Do NOT use `upx=True` (causes antivirus issues)  
❌ Do NOT package into `.zip` or `.7z` (breaks standalone guarantee)  
❌ Do NOT use `--onefile` (creates single file but slower startup)  
❌ Do NOT modify files in `_internal/` (breaks Python runtime)  
❌ Do NOT strip debug info manually (can break app)  
❌ Do NOT move `app.exe` without supporting files in `_internal/`  

---

## Success Indicators

✅ Build completes with "successfully" message  
✅ `dist/app.exe` exists (~80-120 MB)  
✅ GUI launches and is responsive  
✅ CLI responds to `--cli` argument  
✅ No UPX/packing detected in strings output  
✅ File opens normally (not blocked by antivirus)  
✅ Runs on systems without Python installed  

---

## Next: Verify & Distribute

1. **Test on clean system** (optional)
   - Copy `dist/app.exe` to another computer without Python
   - Verify it runs

2. **VirusTotal check** (optional)
   - Upload `dist/app.exe` to virustotal.com
   - Most scores should be 0 or very low

3. **Share distribution package**
   - Zip the `app-release/` folder
   - Include `setup.bat` and `config.json`
   - Users should see clean executable

---

## Getting Help

- Build steps: See `BUILD.md` for detailed guide
- File access: See `SECURITY.md` for what app can/cannot do
- Code entry point: See `main.py` for program flow
- GUI: See `gui/app.py` for interface code
