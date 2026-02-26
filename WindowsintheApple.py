import tkinter as tk
from Quartz import CGWindowListCopyWindowInfo, kCGWindowListOptionOnScreenOnly, kCGNullWindowID
import time

class WindowsInApple:
    def __init__(self):
        self.root = tk.Tk()
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.attributes("-transparent", True)
        # Match Chrome Dark Mode exactly
        self.chrome_gray = "#35363a"
        self.root.config(bg='systemTransparent')
        
        # Absolute click-through for 1:1 terminal responsiveness
        self.root.tk.call('tk', 'unsupported', 'MacWindowStyle', 'style', self.root._w, 'help', 'none')
        
        self.canvas = tk.Canvas(self.root, highlightthickness=0, bg='systemTransparent', bd=0)
        self.canvas.pack(fill="both", expand=True)
        self.run()

    def run(self):
        while True:
            self.canvas.delete("all")
            windows = CGWindowListCopyWindowInfo(kCGWindowListOptionOnScreenOnly, kCGNullWindowID)
            for window in windows:
                if window.get("kCGWindowLayer", 0) != 0 or not window.get("kCGWindowIsOnscreen"):
                    continue
                
                name = window.get("kCGWindowName", "")
                owner = window.get("kCGWindowOwnerName", "")
                bounds = window.get("kCGWindowBounds")
                
                if bounds:
                    x, y, w, h = bounds['X'], bounds['Y'], bounds['Width'], bounds['Height']
                    
                    # Target Chrome Specifically to mask the AI Tag
                    if "Google Chrome" in owner:
                        # Draw a masking rectangle over the top-right AI tag area
                        # Adjusted width (120px) to fully cover "AI Mode"
                        self.canvas.create_rectangle(x + w - 150, y + 5, x + w - 5, y + 35, 
                                                   fill=self.chrome_gray, outline=self.chrome_gray)
                        
                        # Windows-style buttons on top of the mask
                        self.canvas.create_oval(x + w - 45, y + 10, x + w - 25, y + 30, fill="#ff5f57") # Close
                        self.canvas.create_oval(x + w - 75, y + 10, x + w - 55, y + 30, fill="#ffbd2e") # Max
                        self.canvas.create_oval(x + w - 105, y + 10, x + w - 85, y + 30, fill="#28c940") # Min

            self.root.update_idletasks()
            self.root.update()
            time.sleep(0.008)

if __name__ == "__main__":
    WindowsInApple()
