# -*- mode: python ; coding: utf-8 -*-
import os

# Get the path to your project
project_path = os.path.abspath('.')

# Build binaries list, filtering out None values
binaries = []
if os.path.exists('src\\ps3000a.dll'):
    binaries.append(('src\\ps3000a.dll', '.'))
if os.path.exists('src\\ps4000a.dll'):
    binaries.append(('src\\ps4000a.dll', '.'))

# Build datas list, filtering out None values
datas = []
if os.path.exists('picosdk'):
    datas.append(('picosdk', 'picosdk'))

a = Analysis(
    ['src\\main.py'],
    pathex=[project_path],
    binaries=binaries,
    datas=datas,
    hiddenimports=[
        'picosdk',
        'picosdk.ps3000a',
        'picosdk.ps4000a',
        'picosdk.library',
        'picosdk.constants',
        'picosdk.errors',
        'picosdk.functions',
        'PyQt5.QtCore',
        'PyQt5.QtWidgets',
        'PyQt5.QtGui',
        'numpy',
        'matplotlib',
        'psutil',
        'ctypes'
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='PicoScope-GUI',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # Set to True for debugging
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
