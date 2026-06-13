# =============================================================================
#  methods/office.py — Word COM 自动化（.doc/.docx → .pdf）
#  仅 Windows + Microsoft Word 可用。线程内需 pythoncom.CoInitialize()。
# =============================================================================

import os
import sys
import tempfile


class OfficeError(Exception):
    """Office 转换相关错误。"""


def _ensure_windows():
    if sys.platform != "win32":
        raise OfficeError("Office 转换仅支持 Windows")


def coinitialize():
    """在工作线程入口处调用一次。未装 pywin32 时静默跳过。"""
    try:
        import pythoncom
        pythoncom.CoInitialize()
    except ImportError:
        pass
    except Exception:
        pass


def couninitialize():
    """在工作线程退出时调用。"""
    try:
        import pythoncom
        pythoncom.CoUninitialize()
    except ImportError:
        pass
    except Exception:
        pass


def word_to_pdf_temp(docx_path: str) -> str:
    """用 Word COM 把 .doc/.docx 转成临时 PDF 文件，返回临时 PDF 路径。

    调用方在 finally 中删除临时 PDF。
    """
    _ensure_windows()
    try:
        from win32com import client as win32_client
    except ImportError:
        raise OfficeError("未安装 pywin32（pip install pywin32）")

    docx_abs = os.path.abspath(docx_path)
    if not os.path.exists(docx_abs):
        raise OfficeError(f"文件不存在：{docx_abs}")

    fd, tmp_pdf = tempfile.mkstemp(suffix=".pdf", prefix="scan_office_")
    os.close(fd)
    # 注：Word.SaveAs 会覆盖已存在文件（DisplayAlerts=0），无需先删除。
    # 用系统 tempdir 而非 methods/_tmp/ 是因为扫描模式不走 cleanup_temp 流程。

    word = None
    doc = None
    try:
        word = win32_client.DispatchEx("Word.Application")
        word.Visible = False
        word.DisplayAlerts = 0  # wdAlertsNone

        doc = word.Documents.Open(
            docx_abs,
            ReadOnly=True,
            ConfirmConversions=False,
            AddToRecentFiles=False,
        )
        # 17 = wdFormatPDF
        doc.SaveAs(tmp_pdf, FileFormat=17)
    except Exception as e:
        # 抓住 COM 错误，统一抛 OfficeError
        msg = str(e)
        if "密码" in msg or "password" in msg.lower():
            raise OfficeError("文档受密码保护") from e
        if "RPC" in msg or "未安装" in msg or "CoCreateInstance" in msg:
            raise OfficeError("未安装 Microsoft Word 或 COM 不可用") from e
        raise OfficeError(f"Word COM 失败：{msg}") from e
    finally:
        if doc is not None:
            try:
                doc.Close(SaveChanges=0)
            except Exception:
                pass
        if word is not None:
            try:
                word.Quit()
            except Exception:
                pass

    if not os.path.exists(tmp_pdf):
        raise OfficeError("Word 未输出 PDF")
    return tmp_pdf
