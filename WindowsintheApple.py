import Quartz
from AppKit import NSWorkspace
import time

class PunksEngine:
    def __init__(self):
        self.last_key_time = 0
        self.palm_threshold = 0.2

    def event_callback(self, proxy, event_type, event, refcon):
        current_time = time.time()
        flags = Quartz.CGEventGetFlags(event)
        
        # 1. Palm Rejection: Kill trackpad clicks during active typing
        if event_type in [Quartz.kCGEventLeftMouseDown, Quartz.kCGEventLeftMouseUp]:
            if (current_time - self.last_key_time) < self.palm_threshold:
                return None

        # 2. Update last key time
        if event_type in [Quartz.kCGEventKeyDown]:
            self.last_key_time = current_time
            keycode = Quartz.CGEventGetIntegerPropertyValue(event, Quartz.kCGKeyboardEventKeycode)

            # 3. Surgical Remapping (Ctrl -> Cmd)
            if keycode in [8, 9, 7, 6, 0] and (flags & Quartz.kCGEventFlagMaskControl):
                flags &= ~Quartz.kCGEventFlagMaskControl
                flags |= Quartz.kCGEventFlagMaskCommand
                Quartz.CGEventSetFlags(event, flags)

            # 4. Alt-Tab Recovery (Cmd+Tab on Mac)
            # If Tab (0x30) is pressed with Cmd (mapped from Alt), un-minimize target
            if keycode == 48 and (flags & Quartz.kCGEventFlagMaskCommand):
                active_app = NSWorkspace.sharedWorkspace().frontmostApplication()
                if active_app:
                    active_app.activateWithOptions_(AppKit.NSApplicationActivateIgnoringOtherApps)

        return event

def run_tap():
    engine = PunksEngine()
    event_tap = Quartz.CGEventTapCreate(
        Quartz.kCGSessionEventTap,
        Quartz.kCGHeadInsertEventTap,
        Quartz.kCGEventTapOptionDefault,
        Quartz.kCGEventMaskForAllEvents,
        engine.event_callback,
        None
    )
    if not event_tap: return
    run_loop_source = Quartz.CFMachPortCreateRunLoopSource(None, event_tap, 0)
    Quartz.CFRunLoopAddSource(Quartz.CFRunLoopGetCurrent(), run_loop_source, Quartz.kCFRunLoopCommonModes)
    Quartz.CGEventTapEnable(event_tap, True)
    Quartz.CFRunLoopRun()

if __name__ == "__main__":
    run_tap()
