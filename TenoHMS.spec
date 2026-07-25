# -*- mode: python ; coding: utf-8 -*-
import os
import sys
from PyInstaller.utils.hooks import collect_submodules

block_cipher = None
ROOT = os.path.abspath('.')

a = Analysis(
    ['launcher.py'],
    pathex=[ROOT],
    binaries=[],
    datas=[
        ('templates', 'templates'),
        ('static', 'static'),
        ('staticfiles', 'staticfiles'),
        ('media', 'media'),
        ('db.sqlite3', '.'),
        ('.env', '.'),
    ],
    hiddenimports=[
        *collect_submodules('django'),
        *collect_submodules('crispy_forms'),
        *collect_submodules('crispy_bootstrap5'),
        *collect_submodules('django_bootstrap5'),
        *collect_submodules('django_filters'),
        *collect_submodules('django_tables2'),
        *collect_submodules('import_export'),
        *collect_submodules('django_htmx'),
        *collect_submodules('whitenoise'),
        'tenohms.settings.desktop',
        'tenohms.settings.base',
        'accounts',
        'core',
        'core.templatetags.core_tags',
        'dashboard',
        'patients',
        'triage',
        'triage.templatetags.visit_tags',
        'consultation',
        'laboratory',
        'radiology',
        'pharmacy',
        'admission',
        'discharge',
        'wards',
        'nursing',
        'billing',
        'cashier',
        'inventory',
        'reports',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='TenoHMS',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='TenoHMS',
)
