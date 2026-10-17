"""Move this run's browser outside the desktop; never embed a full window."""
import ctypes as C
import os
class BrowserWindow:
    def __init__(self):
        if os.name!='nt':raise OSError('Posicionamento externo requer Windows.')
        self.u=C.WinDLL('user32',use_last_error=True)
        handle=C.c_void_p
        self.callback=C.WINFUNCTYPE(C.c_int,handle,C.c_ssize_t)
        self.u.EnumWindows.argtypes=[self.callback,C.c_ssize_t]
        self.u.GetWindowThreadProcessId.argtypes=[handle,C.POINTER(C.c_uint32)]
        self.u.GetClassNameW.argtypes=[handle,C.c_wchar_p,C.c_int]
        self.u.IsWindowVisible.argtypes=[handle]
        self.u.SetWindowPos.argtypes=[handle,handle,C.c_int,C.c_int,C.c_int,C.c_int,C.c_uint]
    def move_offscreen(self,pid):
        found=[]
        @self.callback
        def visit(hwnd,unused):
            owner=C.c_uint32();self.u.GetWindowThreadProcessId(hwnd,C.byref(owner))
            name=C.create_unicode_buffer(256);self.u.GetClassNameW(hwnd,name,256)
            if owner.value==pid and name.value.startswith('Chrome_WidgetWin') and self.u.IsWindowVisible(hwnd):found.append(hwnd)
            return 1
        self.u.EnumWindows(visit,0)
        if not found:return False
        if not self.u.SetWindowPos(found[0],None,-32000,-32000,1280,900,0x0004|0x0010):
            raise OSError('Não foi possível retirar o navegador da área visível.')
        return True
