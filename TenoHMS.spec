# -*- mode: python ; coding: utf-8 -*-
import os
import sys
from PyInstaller.utils.hooks import collect_submodules, collect_data_files, collect_all

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tenohms.settings.desktop")

import django
django_locale = os.path.join(os.path.dirname(django.__file__), 'conf', 'locale')

block_cipher = None
ROOT = os.path.abspath('.')

datas = [
    ('templates', 'templates'),
    ('static', 'static'),
    (django_locale, 'django/conf/locale'),
]

# Collect Django's own data files (locale, templates, etc.)
django_datas = collect_data_files('django', include_py_files=False)
datas.extend([(src, dst) for src, dst in django_datas])

if os.path.isdir('staticfiles'):
    datas.append(('staticfiles', 'staticfiles'))
if os.path.isdir('media'):
    datas.append(('media', 'media'))
if os.path.isfile('db.sqlite3'):
    datas.append(('db.sqlite3', '.'))
if os.path.isfile('.env'):
    datas.append(('.env', '.'))

# Collect all data and metadata for packages that need it
for pkg in [
    'django_bootstrap5',
    'crispy_forms',
    'crispy_bootstrap5',
    'django_filter',
    'django_tables2',
    'import_export',
    'django_htmx',
    'whitenoise',
]:
    pkg_datas, pkg_binaries, pkg_hiddenimports = collect_all(pkg)
    datas.extend([(src, dst) for src, dst in pkg_datas])

a = Analysis(
    ['launcher.py'],
    pathex=[ROOT],
    binaries=[],
    datas=datas,
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
        'accounts.templatetags',
        'accounts.management',
        'accounts.management.commands',
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
        'admission.management',
        'admission.management.commands',
        'discharge',
        'wards',
        'nursing',
        'billing',
        'cashier',
        'inventory',
        'inventory.management',
        'inventory.management.commands',
        'reports',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'django.contrib.gis',
    ],
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
