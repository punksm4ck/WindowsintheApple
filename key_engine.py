import Quartz
import time
import sys
import os

sys.stderr = open(os.devnull, 'w')

class PunksEngine:
    def __init__(self):
        self.last_key_time = 0
        self.palm_threshold = 0.2
    def event_callback(self, proxy, event_type, event, refcon):
        try:
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
        except Exception:
            pass
        return event

engine = PunksEngine()
mask = (Quartz.CGEventMaskBit(Quartz.kCGEventKeyDown) | Quartz.CGEventMaskBit(Quartz.kCGEventLeftMouseDown) | Quartz.CGEventMaskBit(Quartz.kCGEventLeftMouseUp))
tap = Quartz.CGEventTapCreate(Quartz.kCGSessionEventTap, Quartz.kCGHeadInsertEventTap, 0, mask, engine.event_callback, None)
if tap:
    source = Quartz.CFMachPortCreateRunLoopSource(None, tap, 0)
    Quartz.CFRunLoopAddSource(Quartz.CFRunLoopGetCurrent(), source, Quartz.kCFRunLoopCommonModes)
    Quartz.CGEventTapEnable(tap, True)
    Quartz.CFRunLoopRun()
