import tkinter as tk
import Quartz
import AppKit
import threading
import time
import sys

class PunksEngine:
    def __init__(self):
        self.last_key_time = 0
        self.palm_threshold = 0.2
    def event_callback(self, proxy, event_type, event, refcon):
        current_time = time.time()
        if event_type in [Quartz.kCGEventLeftMouseDown, Quartz.kCGEventLeftMouseUp]:
            if (current_time - self.last_key_time) < self.palm_threshold:
                return None
        if event_type == Quartz.kCGEventKeyDown:
            self.last_key_time = current_time
            flags = Quartz.CGEventGetFlags(event)
            keycode = Quartz.CGEventGetIntegerPropertyValue(event, Quartz.kCGKeyboardEventKeycode)
            if keycode in [8, 9, 7, 6, 0] and (flags & Quartz.kCGEventFlagMaskControl):
                flags &= ~Quartz.kCGEventFlagMaskControl
                flags |= Quartz.kCGEventFlagMaskCommand
                Quartz.CGEventSetFlags(event, flags)
            if keycode == 48 and (flags & Quartz.kCGEventFlagMaskCommand):
                ws = AppKit.NSWorkspace.sharedWorkspace()
                app = ws.frontmostApplication()
                if app:
                    app.activateWithOptions_(AppKit.NSApplicationActivateIgnoringOtherApps)
        return event

def run_tap():
    engine = PunksEngine()
    mask = (Quartz.CGEventMaskBit(Quartz.kCGEventKeyDown) | Quartz.CGEventMaskBit(Quartz.kCGEventLeftMouseDown) | Quartz.CGEventMaskBit(Quartz.kCGEventLeftMouseUp))
    event_tap = Quartz.CGEventTapCreate(Quartz.kCGSessionEventTap, Quartz.kCGHeadInsertEventTap, Quartz.kCGEventTapOptionDefault, mask, engine.event_callback, None)
    if not event_tap: sys.exit(1)
    run_loop_source = Quartz.CFMachPortCreateRunLoopSource(None, event_tap, 0)
    Quartz.CFRunLoopAddSource(Quartz.CFRunLoopGetCurrent(), run_loop_source, Quartz.kCGRunLoopCommonModes)
    Quartz.CGEventTapEnable(event_tap, True)
    Quartz.CFRunLoopRun()

class WindowsInApple:
    def __init__(self):
        app = AppKit.NSApplication.sharedApplication()
        app.setActivationPolicy_(AppKit.NSApplicationActivationPolicyProhibited)
        self.root = tk.Tk()
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.attributes("-transparent", True)
        self.root.config(bg='systemTransparent')
        self.root.tk.call('tk', 'unsupported', 'MacWindowStyle', 'style', self.root._w, 'help', 'none')
        self.canvas = tk.Canvas(self.root, highlightthickness=0, bd=0, bg='systemTransparent')
        self.canvas.pack(fill="both", expand=True)
        self.chrome_bg = "#1f1f1f"
        self.last_state = None
        self.update_loop()
        self.root.mainloop()

    def update_loop(self):
        try:
            windows = Quartz.CGWindowListCopyWindowInfo(Quartz.kCGWindowListOptionOnScreenOnly, Quartz.kCGNullWindowID)
            current_state = []
            for w in windows:
                if w.get("kCGWindowLayer", 0) == 0 and w.get("kCGWindowIsOnscreen"):
                    current_state.append((w.get("kCGWindowNumber"), str(w.get("kCGWindowBounds"))))
            
            if current_state != self.last_state:
                self.canvas.delete("all")
                for w_info in windows:
                    if w_info.get("kCGWindowLayer", 0) != 0: continue
                    owner = w_info.get("kCGWindowOwnerName", "")
                    bounds = w_info.get("kCGWindowBounds")
                    if bounds and owner not in ["WindowsintheApple", "Window Server", "Dock"]:
                        x, y, w, h = bounds['X'], bounds['Y'], bounds['Width'], bounds['Height']
                        if w > 300 and h > 100:
                            for offset in [11, 31, 51]:
                                self.canvas.create_oval(x + offset, y + 9, x + offset + 16, y + 25, fill=self.chrome_bg, outline=self.chrome_bg)
                            rx, ry = x + w - 340, y + 8
                            self.canvas.create_oval(rx + 44, ry, rx + 58, ry + 14, fill="#ff5f57", outline="#cf443e")
                            self.canvas.create_oval(rx + 22, ry, rx + 36, ry + 14, fill="#ffbd2e", outline="#cfa023")
                            self.canvas.create_oval(rx, ry, rx + 14, ry + 14, fill="#28c940", outline="#1aab29")
                self.last_state = current_state
        except: pass
        self.root.after(200, self.update_loop)

if __name__ == "__main__":
    t = threading.Thread(target=run_tap, daemon=True)
    t.start()
    WindowsInApple()
