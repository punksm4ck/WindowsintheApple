import Quartz
import AppKit
from AppKit import NSWorkspace, NSApplicationActivateIgnoringOtherApps
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
                ws = NSWorkspace.sharedWorkspace()
                app = ws.frontmostApplication()
                if app:
                    app.activateWithOptions_(NSApplicationActivateIgnoringOtherApps)

        return event

def run_tap():
    engine = PunksEngine()
    mask = (Quartz.CGEventMaskBit(Quartz.kCGEventKeyDown) |
            Quartz.CGEventMaskBit(Quartz.kCGEventLeftMouseDown) |
            Quartz.CGEventMaskBit(Quartz.kCGEventLeftMouseUp))
            
    event_tap = Quartz.CGEventTapCreate(
        Quartz.kCGSessionEventTap,
        Quartz.kCGHeadInsertEventTap,
        Quartz.kCGEventTapOptionDefault,
        mask,
        engine.event_callback,
        None
    )
    
    if not event_tap:
        sys.exit(1)

    run_loop_source = Quartz.CFMachPortCreateRunLoopSource(None, event_tap, 0)
    Quartz.CFRunLoopAddSource(Quartz.CFRunLoopGetCurrent(), run_loop_source, Quartz.kCFRunLoopCommonModes)
    Quartz.CGEventTapEnable(event_tap, True)
    Quartz.CFRunLoopRun()

if __name__ == "__main__":
    run_tap()
