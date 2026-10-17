"""Host only this app's dedicated Edge/Chrome window in a Tk frame on Windows."""
import ctypes as C
import os

class BrowserEmbed:
    def __init__(self):
        if os.name != 'nt':
            raise OSError('A incorporação do navegador compacto requer Windows.')
        self.u = C.WinDLL('user32', use_last_error=True)
        handle, integer = C.c_void_p, C.c_ssize_t
        self.callback_type = C.WINFUNCTYPE(C.c_int, handle, integer)
        self.u.EnumWindows.argtypes = [self.callback_type, integer]
        self.u.EnumWindows.restype = C.c_int
        self.u.GetWindowThreadProcessId.argtypes = [handle, C.POINTER(C.c_uint32)]
        self.u.IsWindowVisible.argtypes = [handle]
        self.u.IsWindow.argtypes = [handle]
        self.u.SetParent.argtypes = [handle, handle]
        self.u.SetParent.restype = handle
        self.u.GetClassNameW.argtypes = [handle, C.c_wchar_p, C.c_int]
        suffix = 'LongPtrW' if C.sizeof(handle) == 8 else 'LongW'
        self.get_style = getattr(self.u, 'GetWindow' + suffix)
        self.set_style = getattr(self.u, 'SetWindow' + suffix)
        self.get_style.argtypes = [handle, C.c_int]; self.get_style.restype = integer
        self.set_style.argtypes = [handle, C.c_int, integer]; self.set_style.restype = integer
        self.u.SetWindowPos.argtypes = [handle, handle, C.c_int, C.c_int, C.c_int, C.c_int, C.c_uint]
        self.u.MoveWindow.argtypes = [handle, C.c_int, C.c_int, C.c_int, C.c_int, C.c_int]
        self.u.ShowWindow.argtypes = [handle, C.c_int]
        self.hwnd = None

    def find(self, pid):
        found = []
        @self.callback_type
        def visit(hwnd, unused):
            owner = C.c_uint32()
            self.u.GetWindowThreadProcessId(hwnd, C.byref(owner))
            name = C.create_unicode_buffer(256)
            self.u.GetClassNameW(hwnd, name, 256)
            if owner.value == pid and name.value.startswith('Chrome_WidgetWin') and self.u.IsWindowVisible(hwnd):
                found.append(hwnd)
            return 1
        self.u.EnumWindows(visit, 0)
        return found[0] if found else None

    def attach(self, pid, parent, width, height):
        if self.hwnd and self.u.IsWindow(self.hwnd):
            owner = C.c_uint32()
            self.u.GetWindowThreadProcessId(self.hwnd, C.byref(owner))
            if owner.value != pid:
                self.hwnd = None
        if not self.hwnd or not self.u.IsWindow(self.hwnd):
            self.hwnd = self.find(pid)
        if not self.hwnd:
            return False
        # Strip only window chrome. The original verification document remains.
        style = self.get_style(self.hwnd, -16)
        style = (style & ~(0x80000000 | 0x00C00000 | 0x00040000 | 0x00080000 | 0x00020000 | 0x00010000)) | 0x40000000 | 0x10000000
        self.set_style(self.hwnd, -16, style)
        C.set_last_error(0)
        previous = self.u.SetParent(self.hwnd, parent)
        error = C.get_last_error()
        if not previous and error:
            raise OSError(error, 'O Windows não permitiu incorporar a janela do navegador: ' + C.FormatError(error))
        self.u.SetWindowPos(self.hwnd, None, 0, 0, width, height, 0x0004 | 0x0010 | 0x0020)
        self.u.ShowWindow(self.hwnd, 8)
        self.resize(width, height)
        return True

    def resize(self, width, height):
        if self.hwnd and self.u.IsWindow(self.hwnd):
            self.u.MoveWindow(self.hwnd, 0, 0, max(1,width), max(1,height), True)
