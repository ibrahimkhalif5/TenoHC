# -*- mode: python ; coding: utf-8 -*-
import os
import sys
import importlib

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tenohms.settings.desktop")

block_cipher = None
ROOT = os.path.abspath('.')

datas = [
    ('templates', 'templates'),
    ('static', 'static'),
    ('seed_data', 'seed_data'),
]

if os.path.isdir('staticfiles'):
    datas.append(('staticfiles', 'staticfiles'))
if os.path.isdir('media'):
    datas.append(('media', 'media'))
if os.path.isfile('db.sqlite3'):
    datas.append(('db.sqlite3', '.'))
if os.path.isfile('.env'):
    datas.append(('.env', '.'))

# ── Bundle Django locale files explicitly ──
import django
django_path = os.path.dirname(django.__file__)
django_locale_src = os.path.join(django_path, 'conf', 'locale')
if os.path.isdir(django_locale_src):
    datas.append((django_locale_src, os.path.join('django', 'conf', 'locale')))

# ── Collect data for third-party packages ──
from PyInstaller.utils.hooks import collect_all, collect_data_files, collect_submodules

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
    pkg_datas, _, _ = collect_all(pkg)
    datas.extend([(src, dst) for src, dst in pkg_datas])

# ── Runtime hook to fix translation path for frozen Django ──
runtime_hook_code = '''
import os, sys

if getattr(sys, 'frozen', False):
    bundle_dir = sys._MEIPASS
    # Ensure Django can find its locale files
    django_locale = os.path.join(bundle_dir, 'django', 'conf', 'locale')
    if os.path.isdir(django_locale):
        import django.conf
        django.conf.settings.LOCALE_PATHS = [django_locale]
'''

runtime_hook_path = os.path.join(ROOT, '_django_hook.py')
with open(runtime_hook_path, 'w') as f:
    f.write(runtime_hook_code)

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
        'core.management',
        'core.management.commands',
        'core.management.commands.load_seed_csv',
        'core.management.commands.seed_item_master',
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
        'admission.management.commands.seed_wards',
        'discharge',
        'wards',
        'nursing',
        'billing',
        'cashier',
        'inventory',
        'inventory.management',
        'inventory.management.commands',
        'inventory.management.commands.seed_medicines',
        'reports',
        'laboratory.management',
        'laboratory.management.commands',
        'laboratory.management.commands.seed_lab_templates',
        'laboratory.management.commands.seed_lab_tests',
        'radiology.management',
        'radiology.management.commands',
        'radiology.management.commands.seed_radiology_services',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[runtime_hook_path],
    excludes=[
        'django.contrib.gis',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# Clean up runtime hook file
try:
    os.remove(runtime_hook_path)
except OSError:
    pass

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
