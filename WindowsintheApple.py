import Quartz
from AppKit import NSWorkspace
import time

def event_callback(proxy, event_type, event, refcon):
    flags = Quartz.CGEventGetFlags(event)
    keycode = Quartz.CGEventGetIntegerPropertyValue(event, Quartz.kCGKeyboardEventKeycode)
    
    # Surgical Remapping: CTRL (0x3b) to CMD (0x3a) for standard shortcuts
    # 0x08=C, 0x09=V, 0x07=X, 0x06=Z, 0x00=A
    if keycode in [8, 9, 7, 6, 0] and (flags & Quartz.kCGEventFlagMaskControl):
        flags &= ~Quartz.kCGEventFlagMaskControl
        flags |= Quartz.kCGEventFlagMaskCommand
        Quartz.CGEventSetFlags(event, flags)
        
    return event

def run_tap():
    event_tap = Quartz.CGEventTapCreate(
        Quartz.kCGSessionEventTap,
        Quartz.kCGHeadInsertEventTap,
        Quartz.kCGEventTapOptionDefault,
        Quartz.kCGEventMaskForAllEvents,
        event_callback,
        None
    )
    
    if not event_tap:
        return

    run_loop_source = Quartz.CFMachPortCreateRunLoopSource(None, event_tap, 0)
    Quartz.CFRunLoopAddSource(Quartz.CFRunLoopGetCurrent(), run_loop_source, Quartz.kCFRunLoopCommonModes)
    Quartz.CGEventTapEnable(event_tap, True)
    Quartz.CFRunLoopRun()

if __name__ == "__main__":
    run_tap()
