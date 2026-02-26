import tkinter as tk
from Quartz import CGWindowListCopyWindowInfo, kCGWindowListOptionOnScreenOnly, kCGNullWindowID
import time

class WindowsInApple:
    def __init__(self):
        self.root = tk.Tk()
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.attributes("-transparent", True)
        self.root.config(bg='systemTransparent')
        
        self.root.tk.call('tk', 'unsupported', 'MacWindowStyle', 'style', self.root._w, 'help', 'none')
        
        self.canvas = tk.Canvas(self.root, highlightthickness=0, bd=0, insertwidth=0, bg='systemTransparent', bd=0)
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
                    
                    if "Google Chrome" in owner:
                        self.canvas.create_rectangle(x - 20, y - 20, x + w + 20, y + 50, 
                                                   fill=self.chrome_gray, outline=self.chrome_gray)
                        

            self.root.update_idletasks()
            self.root.update()
            self.root.update(); self.root.update(); time.sleep(0.008)

if __name__ == "__main__":
    WindowsInApple()
