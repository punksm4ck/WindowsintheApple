import tkinter as tk
from Quartz import CGWindowListCopyWindowInfo, kCGWindowListOptionOnScreenOnly, kCGNullWindowID
import AppKit
import time

class WindowsInApple:
    def __init__(self):
        self.root = tk.Tk()
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.attributes("-transparent", True)
        self.root.config(bg='systemTransparent')
        # This line is the key: it ignores ALL mouse events on the window itself
        self.root.tk.call('tk', 'unsupported', 'MacWindowStyle', 'style', self.root._w, 'help', 'none')
        
        self.canvas = tk.Canvas(self.root, highlightthickness=0, bg='systemTransparent', bd=0)
        self.canvas.pack(fill="both", expand=True)
        
        self.run()

    def get_windows(self):
        # Only grab windows that are actually on screen
        options = kCGWindowListOptionOnScreenOnly
        return CGWindowListCopyWindowInfo(options, kCGNullWindowID)

    def run(self):
        while True:
            self.canvas.delete("all")
            windows = self.get_windows()
            for window in windows:
                # Visibility and Ghosting Guard
                if not window.get("kCGWindowIsOnscreen") or window.get("kCGWindowLayer", 0) != 0:
                    continue
                
                bounds = window.get("kCGWindowBounds")
                if bounds:
                    # Draw your buttons here based on bounds
                    # (Simplified for logic verification)
                    pass
            
            self.root.update_idletasks()
            self.root.update()
            time.sleep(0.008) # 125Hz - Perfect balance

if __name__ == "__main__":
    WindowsInApple()
