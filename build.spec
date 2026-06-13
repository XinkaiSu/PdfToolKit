# -*- mode: python ; coding: utf-8 -*-
# PyInstaller 打包配置
# 使用方法：pyinstaller build.spec --clean

import os
import sys
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

# 从 version.py 读取版本号（唯一来源）
sys.path.insert(0, '.')
from version import __version__
_version_tuple = tuple(int(x) for x in __version__.split('.'))

# 动态生成 Windows 版本资源文件
_version_info_path = os.path.join(os.path.dirname(os.path.abspath(SPECPATH)), '_version_info_tmp.py')
with open(_version_info_path, 'w', encoding='utf-8') as f:
    f.write(f"""# UTF-8
# 自动生成 — 勿手动编辑，版本号来源于 version.py

VSVersionInfo(
  ffi=FixedFileInfo(
    filevers={_version_tuple + (0,)},
    prodvers={_version_tuple + (0,)},
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0),
  ),
  kids=[
    StringFileInfo(
      [
        StringTable(
          "080404b0",
          [
            StringStruct("CompanyName", "XinkaiSu"),
            StringStruct("FileDescription", "PDF 批量合并工具"),
            StringStruct("FileVersion", "{__version__}"),
            StringStruct("InternalName", "PdfToolKit"),
            StringStruct("LegalCopyright", "Copyright 2025-2026 XinkaiSu"),
            StringStruct("OriginalFilename", "PdfToolKit.exe"),
            StringStruct("ProductName", "PDF 批量合并工具"),
            StringStruct("ProductVersion", "{__version__}"),
          ],
        ),
      ],
    ),
    VarFileInfo([VarStruct("Translation", [2052, 1200])]),
  ],
)
""")

block_cipher = None

# 收集 customtkinter 数据文件（主题、图标等）
customtkinter_datas = collect_data_files('customtkinter')

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=customtkinter_datas + [('gui/icon.ico', 'gui'), ('gui/icon.png', 'gui')],
    hiddenimports=[
        'config',
        'core',
        'methods',
        'methods.fonts',
        'methods.sort',
        'methods.convert',
        'methods.merge',
        'methods.toc',
        'methods.pagenum',
        'methods.bookmark',
        'methods.cover',
        'gui',
        'gui.app',
        'gui.cover_tab',
        'gui.toc_tab',
        'gui.pagenum_tab',
        'gui.font_tab',
        'gui.path_tab',
        'gui.filelist_tab',
        'gui.bookmark_tab',
        'gui.combine_filelist_tab',
        'gui.combine_params_tab',
        'gui.combine_canvas_tab',
        'gui.scan_path_tab',
        'gui.scan_params_tab',
        'gui.home_tab',
        'methods.combine',
        'methods.blankpage',
        'methods.scan',
        'methods.office',
        'scanner',
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
        'pypdfium2',
        'win32com',
        'win32com.client',
        'pythoncom',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # 不再需要的旧依赖
        'docx',
        'lxml',
        # 排除不需要的大型模块
        'tkinter.test',
        'unittest',
        'pydoc',
        'distutils',
        'setuptools',
        'pip',
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
    icon='gui/icon.ico',
    version=_version_info_path,
)
