# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=[],
    datas=[
        ('app/build', 'app/build'),
        ('modules', 'modules'),
        ('configs', 'configs'),
        ('tesseract-ocr', 'tesseract-ocr'),
        ('version.json', '.'),
        ('tests/game_catch_runtime.lua', 'tests'),
    ],
    hiddenimports=[
        'keyboard', 
        'pkg_resources.extern', 
        'webview',
        'win32api',
        'win32con',
        'win32gui',
        'pywintypes',
        'pythoncom',
        'pynput',
        'pynput.mouse',
        'pynput.keyboard',
        'frida',
        'frida._frida',
    ],  # Adicione imports ocultos se necessário
    hookspath=[],                # Adicione caminhos para hooks customizados se necessário
    runtime_hooks=[],            # Adicione runtime hooks se necessário
    excludes=['cefpython3'],  # Legacy CEF does not support this Python 3.12 release.
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='pokemacro',
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    debug=False,
    console=False,  # Altere para True se precisar de um console
)
