import objc
import AppKit
import Quartz
import sys
import os

sys.stderr = open(os.devnull, 'w')

def hex_to_nscolor(hex_str):
    hex_str = hex_str.lstrip('#')
    r = int(hex_str[0:2], 16) / 255.0
    g = int(hex_str[2:4], 16) / 255.0
    b = int(hex_str[4:6], 16) / 255.0
    return AppKit.NSColor.colorWithRed_green_blue_alpha_(r, g, b, 1.0)

class GhostWindow(AppKit.NSWindow):
    def canBecomeKeyWindow(self): return False
    def canBecomeMainWindow(self): return False

class OverlayView(AppKit.NSView):
    def isFlipped(self): return True
    def acceptsFirstResponder(self): return False

    def drawRect_(self, rect):
        AppKit.NSColor.clearColor().set()
        AppKit.NSRectFill(self.bounds())
        
        active_app = AppKit.NSWorkspace.sharedWorkspace().frontmostApplication()
        if not active_app: return
        active_pid = active_app.processIdentifier()
        active_name = active_app.localizedName()
        
        if active_name in ["Window Server", "Dock", "loginwindow", "ControlCenter"]:
            return

        windows = Quartz.CGWindowListCopyWindowInfo(Quartz.kCGWindowListOptionOnScreenOnly, Quartz.kCGNullWindowID)

        max_area = 0
        main_w = None
        for w in windows:
            if w.get("kCGWindowLayer", 0) != 0: continue
            if w.get("kCGWindowOwnerPID") != active_pid: continue
            if w.get("kCGWindowAlpha", 1.0) == 0.0: continue
            
            bounds = w.get("kCGWindowBounds")
            if not bounds: continue
            
            area = bounds['Width'] * bounds['Height']
            # IGNORING DROPDOWNS: Only the single largest app window is targeted
            if area > max_area and bounds['Width'] > 250 and bounds['Height'] > 150:
                max_area = area
                main_w = w
                
        if not main_w: return
        
        owner = main_w.get("kCGWindowOwnerName", "")
        bounds = main_w.get("kCGWindowBounds")
        x = bounds['X']
        y = bounds['Y']
        w_val = bounds['Width']
        
        is_chrome = any(n in active_name for n in ["Chrome", "Gemini", "Google"])
        
        if is_chrome:
            hex_to_nscolor("#202124").set()
            
            # 1. Mask Top-Left Native Apple Buttons completely
            AppKit.NSRectFill(AppKit.NSMakeRect(x, y, 110, 45))
            
            # 2. Mask Gemini Assist Pill on the far right completely
            AppKit.NSRectFill(AppKit.NSMakeRect(x + w_val - 250, y, 250, 45))
            
            # 3. Draw the Custom Gemini Pill Shape on the Left
            pill_rect = AppKit.NSMakeRect(x + 10, y + 8, 85, 26)
            pill_path = AppKit.NSBezierPath.bezierPathWithRoundedRect_xRadius_yRadius_(pill_rect, 13, 13)
            hex_to_nscolor("#323639").set()
            pill_path.fill()
            
            # 4. Draw Green, Yellow, Red inside the custom pill
            def draw_circle(qx, qy, size, hex_color):
                hex_to_nscolor(hex_color).set()
                AppKit.NSBezierPath.bezierPathWithOvalInRect_(AppKit.NSMakeRect(qx, qy, size, size)).fill()
                
            draw_circle(x + 16, y + 14, 14, "#28c940") # Green
            draw_circle(x + 36, y + 14, 14, "#ffbd2e") # Yellow
            draw_circle(x + 56, y + 14, 14, "#ff5f57") # Red
            
        else:
            bg_color = "#1e1e1e"
            y_off_left = 12
            rx_offset = 200
            mask_size = 15
            
            if any(n in active_name for n in ["Console", "Terminal"]):
                bg_color = "#1d1d1d"
            elif "Finder" in active_name:
                bg_color = "#282828"
                y_off_left = 13
                rx_offset = 160
            elif "App Store" in active_name:
                bg_color = "#1c1c1e"
                mask_size = 17
                y_off_left = 14
            
            hex_to_nscolor(bg_color).set()
            AppKit.NSBezierPath.bezierPathWithOvalInRect_(AppKit.NSMakeRect(x + 10, y + y_off_left, mask_size + 4, mask_size)).fill()
            AppKit.NSBezierPath.bezierPathWithOvalInRect_(AppKit.NSMakeRect(x + 30, y + y_off_left, mask_size + 4, mask_size)).fill()
            AppKit.NSBezierPath.bezierPathWithOvalInRect_(AppKit.NSMakeRect(x + 50, y + y_off_left, mask_size + 4, mask_size)).fill()
            
            rx = x + w_val - rx_offset
            ry = y + 12
            
            hex_to_nscolor("#28c940").set()
            AppKit.NSBezierPath.bezierPathWithOvalInRect_(AppKit.NSMakeRect(rx, ry, 14, 14)).fill()
            hex_to_nscolor("#ffbd2e").set()
            AppKit.NSBezierPath.bezierPathWithOvalInRect_(AppKit.NSMakeRect(rx + 24, ry, 14, 14)).fill()
            hex_to_nscolor("#ff5f57").set()
            AppKit.NSBezierPath.bezierPathWithOvalInRect_(AppKit.NSMakeRect(rx + 48, ry, 14, 14)).fill()

class AppDelegate(AppKit.NSObject):
    def applicationDidFinishLaunching_(self, notification):
        screen_frame = AppKit.NSScreen.screens()[0].frame()
        self.window = GhostWindow.alloc().initWithContentRect_styleMask_backing_defer_(
            screen_frame, 0, 2, False
        )
        self.window.setLevel_(AppKit.NSFloatingWindowLevel)
        self.window.setHasShadow_(False)
        self.window.setOpaque_(False)
        self.window.setBackgroundColor_(AppKit.NSColor.clearColor())
        self.window.setIgnoresMouseEvents_(True)
        self.window.setCollectionBehavior_(1 | 16 | 64) 
        
        self.view = OverlayView.alloc().initWithFrame_(screen_frame)
        self.window.setContentView_(self.view)
        
        self.window.orderFrontRegardless()

        self.last_state = ""
        self.timer = AppKit.NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
            0.15, self, objc.selector(self.updateUI_, signature=b'v@:@'), None, True
        )

    def updateUI_(self, timer):
        try:
            active_app = AppKit.NSWorkspace.sharedWorkspace().frontmostApplication()
            if not active_app: return
            active_pid = active_app.processIdentifier()
            active_name = active_app.localizedName()
            
            if active_name in ["Window Server", "Dock", "loginwindow", "ControlCenter"]:
                if self.last_state != "":
                    self.last_state = ""
                    self.view.setNeedsDisplay_(True)
                return

            windows = Quartz.CGWindowListCopyWindowInfo(Quartz.kCGWindowListOptionOnScreenOnly, Quartz.kCGNullWindowID)
            
            max_area = 0
            main_w = None
            for w in windows:
                if w.get("kCGWindowLayer", 0) != 0: continue
                if w.get("kCGWindowOwnerPID") != active_pid: continue
                if w.get("kCGWindowAlpha", 1.0) == 0.0: continue
                bounds = w.get("kCGWindowBounds")
                if not bounds: continue
                area = bounds['Width'] * bounds['Height']
                if area > max_area and bounds['Width'] > 250 and bounds['Height'] > 150:
                    max_area = area
                    main_w = w
                    
            if main_w:
                bounds = main_w.get("kCGWindowBounds")
                # ABSOLUTE FOCUS LOCK: Only tracks the X/Y of the single largest window
                state = f"{active_pid}_{bounds['X']}_{bounds['Y']}_{bounds['Width']}_{bounds['Height']}"
                if state != self.last_state:
                    self.last_state = state
                    self.view.setNeedsDisplay_(True)
            else:
                if self.last_state != "":
                    self.last_state = ""
                    self.view.setNeedsDisplay_(True)
        except Exception:
            pass

if __name__ == "__main__":
    app = AppKit.NSApplication.sharedApplication()
    app.setActivationPolicy_(AppKit.NSApplicationActivationPolicyAccessory)
    delegate = AppDelegate.alloc().init()
    app.setDelegate_(delegate)
    AppKit.NSApp().run()
