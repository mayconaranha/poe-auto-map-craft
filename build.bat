@echo off
REM Build AutoCraft as a standalone .exe using PyInstaller
REM Run this script from the craft-map directory

pyinstaller ^
  --onefile ^
  --windowed ^
  --name AutoCraft ^
  --add-data "image;image" ^
  autocraft.py

echo.
echo Build complete. Executable is in dist\AutoCraft.exe
