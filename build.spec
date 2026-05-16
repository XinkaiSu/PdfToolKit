# -*- mode: python ; coding: utf-8 -*-
# PyInstaller 打包配置
# 使用方法：pyinstaller build.spec --clean

import sys
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

# 从 version.py 读取版本号
sys.path.insert(0, '.')
from version import __version__
_version_tuple = tuple(int(x) for x in __version__.split('.'))

block_cipher = None

# 收集 customtkinter 数据文件（主题、图标等）
customtkinter_datas = collect_data_files('customtkinter')

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=customtkinter_datas,
    hiddenimports=[
        'config',
        'core',
        'cover',
        'gui',
        'gui.app',
        'gui.cover_tab',
        'gui.toc_tab',
        'gui.pagenum_tab',
        'gui.font_tab',
        'gui.path_tab',
        'gui.filelist_tab',
        'gui.bookmark_tab',
        'pikepdf',
        'pikepdf._cpphelpers',
        'reportlab',
        'reportlab.graphics',
        'reportlab.pdfbase',
        'reportlab.pdfgen',
        'reportlab.lib',
        'fitz',
        'fitz._fitz',
        'PIL',
        'customtkinter',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # 不再需要的 DOCX 相关依赖
        'docx',
        'lxml',
        'win32com',
        'comtypes',
        # 排除不需要的大型模块
        'tkinter.test',
        'unittest',
        'pydoc',
        'distutils',
        'setuptools',
        'pip',
        'numpy',
        'scipy',
        'matplotlib',
        'pandas',
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
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='PdfToolKit',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
    version='version_info.py',
)
