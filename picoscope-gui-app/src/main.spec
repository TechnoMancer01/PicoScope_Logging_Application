# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['main.py'],
    pathex=[
        'c:\\Users\\TheAx\\Documents\\PicoSDK\\picosdk-python-wrappers',  # Add picosdk path
    ],
    binaries=[
        ('ps3000a.dll', '.'),
        ('ps4000a.dll', '.'),
        ('usbdrdaq.dll', '.'),
        ('usbpt104.dll', '.'),
        ('usbtc08.dll', '.'),
        ('picohrdl.dll', '.'),
        ('picoipp.dll', '.'),
    ],
    datas=[
        # Include the entire picosdk module
        ('c:\\Users\\TheAx\\Documents\\PicoSDK\\picosdk-python-wrappers\\picosdk', 'picosdk'),
    ],
    hiddenimports=[
        'picosdk',
        'picosdk.ps3000a',
        'picosdk.ps4000a',
        'picosdk.library',
        'picosdk.constants',
        'picosdk.device',
        'picosdk.errors',
        'picosdk.discover',
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
    a.datas,
    [],
    name='main',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
