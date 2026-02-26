#!/usr/bin/env python3
import tkinter as tk
from AppKit import NSApp, NSApplicationActivationPolicyAccessory
import Quartz
import os
import subprocess
import sys

sys.stderr = open(os.devnull, 'w')

def get_all_windows():
    options = Quartz.kCGWindowListOptionOnScreenOnly | Quartz.kCGWindowListExcludeDesktopElements
    window_list = Quartz.CGWindowListCopyWindowInfo(options, Quartz.kCGNullWindowID)
    valid = []
    for win in window_list:
        if win.get('kCGWindowLayer') == 0 and win.get('kCGWindowOwnerName') not in ['Python', 'Window Server', 'Finder', 'Dock', 'ControlCenter']:
            bounds = win.get('kCGWindowBounds')
            if bounds and bounds.get('Width', 0) > 150:
                valid.append(win)
    return valid

def execute_action(pid, action_type):
    if action_type == 'close':
        cmd = 'keystroke "w" using command down'
    elif action_type == 'min':
        cmd = 'keystroke "m" using command down'
    elif action_type == 'max':
        cmd = 'keystroke "f" using {command down, control down}'
        
    code = f'''
    tell application "System Events"
        set theProc to first process whose unix id is {pid}
        if "{action_type}" is "min" then
            try
                set theWin to first window of theProc
                if value of attribute "AXFullScreen" of theWin is true then
                    set value of attribute "AXFullScreen" of theWin to false
                    delay 0.4
                end if
            end try
        end if
        set frontmost of theProc to true
    end tell
    delay 0.05
    tell application "System Events"
        {cmd}
    end tell
    '''
    subprocess.Popen(['osascript', '-e', code], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

class GlobalOverlayManager:
    def __init__(self):
        self.current_pid = os.getpid()
        self.root = tk.Tk()
        self.root.withdraw()
        NSApp.setActivationPolicy_(NSApplicationActivationPolicyAccessory)
        self.overlays = {}
        self.update_loop()
        self.root.mainloop()

    def elevate_nswindow(self, tk_win, unique_title, is_mask=False):
        tk_win.wm_title(unique_title)
        tk_win.update_idletasks()
        try:
            for nsw in NSApp.windows():
                if str(nsw.title()) == unique_title:
                    nsw.setLevel_(Quartz.kCGFloatingWindowLevel)
                    nsw.setCollectionBehavior_(Quartz.NSWindowCollectionBehaviorCanJoinAllSpaces | Quartz.NSWindowCollectionBehaviorFullScreenAuxiliary)
                    nsw.setHasShadow_(False)
                    if is_mask:
                        nsw.setIgnoresMouseEvents_(True)
                    else:
                        nsw.setIgnoresMouseEvents_(False)
                    return nsw
        except: pass
        return None

    def force_cleanup(self, wid):
        if wid in self.overlays:
            self.overlays[wid]['btn'].destroy()
            self.overlays[wid]['mask'].destroy()
            del self.overlays[wid]

    def update_loop(self):
        windows = get_all_windows()
        current_wids = set()

        for i, win in enumerate(windows):
            wid = win.get('kCGWindowNumber')
            pid = win.get('kCGWindowOwnerPID')
            b = win.get('kCGWindowBounds')
            
            if not wid or not pid or not b:
                continue
                
            current_wids.add(wid)

            if wid not in self.overlays:
                btn = tk.Toplevel(self.root)
                mask = tk.Toplevel(self.root)
                theme_bg = '#262626'
                
                btn.overrideredirect(True)
                btn.configure(bg=theme_bg)
                btn_nsw = self.elevate_nswindow(btn, f"btn_{wid}", is_mask=False)
                
                mask.overrideredirect(True)
                mask.configure(bg=theme_bg)
                mask_nsw = self.elevate_nswindow(mask, f"mask_{wid}", is_mask=True)
                
                c = tk.Canvas(btn, width=80, height=28, bg=theme_bg, highlightthickness=0, bd=0)
                c.pack()
                
                b_max = c.create_oval(10, 8, 22, 20, fill="#27c93f", outline="#1aab29")
                c.tag_bind(b_max, '<Button-1>', lambda e, p=pid: execute_action(p, 'max'))
                
                b_min = c.create_oval(34, 8, 46, 20, fill="#ffbd2e", outline="#dea123")
                c.tag_bind(b_min, '<Button-1>', lambda e, p=pid: execute_action(p, 'min'))
                
                b_cls = c.create_oval(58, 8, 70, 20, fill="#ff5f56", outline="#e0443e")
                c.tag_bind(b_cls, '<Button-1>', lambda e, p=pid: execute_action(p, 'close'))
                
                self.overlays[wid] = {'btn': btn, 'mask': mask, 'btn_nsw': btn_nsw, 'mask_nsw': mask_nsw}

            btn_x = int(b['X'] + b['Width'] - 85)
            btn_y = int(b['Y'])
            mask_x = int(b['X'])
            mask_y = int(b['Y'])

            btn_bx1, btn_bx2 = btn_x, btn_x + 80
            btn_by1, btn_by2 = btn_y, btn_y + 28
            mask_mx1, mask_mx2 = mask_x, mask_x + 75
            mask_my1, mask_my2 = mask_y, mask_y + 28

            is_occluded = False
            for j in range(i):
                top_w = windows[j]
                if top_w.get('kCGWindowOwnerPID') == self.current_pid:
                    continue
                tb = top_w.get('kCGWindowBounds')
                if not tb:
                    continue
                tx1, ty1 = tb['X'], tb['Y']
                tx2, ty2 = tx1 + tb['Width'], ty1 + tb['Height']

                if not (tx1 > btn_bx2 or tx2 < btn_bx1 or ty1 > btn_by2 or ty2 < btn_by1):
                    is_occluded = True
                    break
                if not (tx1 > mask_mx2 or tx2 < mask_mx1 or ty1 > mask_my2 or ty2 < mask_my1):
                    is_occluded = True
                    break

            try:
                self.overlays[wid]['btn'].geometry(f"80x28+{btn_x}+{btn_y}")
                self.overlays[wid]['mask'].geometry(f"75x28+{mask_x}+{mask_y}")
                
                if self.overlays[wid]['btn_nsw']:
                    self.overlays[wid]['btn_nsw'].setAlphaValue_(0.0 if is_occluded else 1.0)
                if self.overlays[wid]['mask_nsw']:
                    self.overlays[wid]['mask_nsw'].setAlphaValue_(0.0 if is_occluded else 1.0)
            except: pass

        for wid in list(self.overlays.keys()):
            if wid not in current_wids:
                self.force_cleanup(wid)

        self.root.after(4, self.update_loop)

if __name__ == "__main__":
    GlobalOverlayManager()
