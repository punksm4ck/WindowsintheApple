#!/usr/bin/env python3.12
# -*- coding: utf-8 -*-
"""
═══════════════════════════════════════════════════════════════════════════
  WINDOWSINTHEAPPLE  ·  v2.1  ·  PUNKS / AEGIS
  Traffic lights on the RIGHT. Covered content mirrored on the LEFT.
═══════════════════════════════════════════════════════════════════════════

  v2.1 — precision + ScreenCaptureKit:
    · LEFT MASK is now a tight rounded pill sized from the REAL AX button
      frames — covers only the traffic light cluster, nothing else.
    · RIGHT LIGHTS get a subtle rounded backing pill (titlebar-matched
      color) so they read cleanly over crowded app chrome.
    · LIVE MIRROR rebuilt on ScreenCaptureKit (macOS 14+/26): the exact
      strip our fake lights cover on the right is captured async and
      rendered inside the left mask. Legacy CGWindowListCreateImage kept
      as fallback for macOS <= 13. If neither works (no Screen Recording
      permission), degrades to solid sampled/dark mask.
    · Titlebar color sampling now rides the SCK capture too — mask and
      pill match each app's real chrome.

  Carried over from v2.0 (all battle-tested):
    · @objc.python_method decorators on all bridged-class helpers
    · setReleasedWhenClosed_(False) — dealloc-on-close segfault fix
    · RETIRE_GRACE retirement — no churn on transient focus blips
    · FRONTMOST_IGNORE hold — screenshot UI / own clicks don't nuke skins
    · Grace-tracked skin registry keyed by CGWindowNumber
    · Zero AX polling in the hot loop
    · Split logging (app log vs launchd stream log)

  Permissions (System Settings → Privacy & Security):
    · Accessibility               (button clicks)
    · Screen & System Audio Rec.  (live mirror + color sampling)

  CLI: run | --debug | --install | --uninstall
═══════════════════════════════════════════════════════════════════════════
"""

import os
import sys
import math
import time
import signal
import logging
import threading
import subprocess
from logging.handlers import RotatingFileHandler

import objc
from AppKit import (
    NSApplication, NSApplicationActivationPolicyAccessory, NSWorkspace,
    NSWindow, NSView, NSColor, NSScreen, NSBackingStoreBuffered,
    NSWindowStyleMaskBorderless, NSBezierPath, NSTrackingArea,
    NSTrackingMouseEnteredAndExited, NSTrackingActiveAlways,
    NSFloatingWindowLevel, NSImage, NSCompositingOperationSourceOver,
    NSMakeRect, NSMakePoint, NSBitmapImageRep,
    NSWindowCollectionBehaviorCanJoinAllSpaces,
    NSWindowCollectionBehaviorFullScreenAuxiliary,
    NSWindowCollectionBehaviorTransient,
)
from Foundation import NSTimer, NSObject, NSRunLoop, NSRunLoopCommonModes
import Quartz
from Quartz import (
    CGWindowListCopyWindowInfo, kCGWindowListOptionOnScreenOnly,
    kCGWindowListExcludeDesktopElements, kCGNullWindowID,
    kCGWindowListOptionIncludingWindow, CGRectNull, CGRectMake,
    CGImageGetWidth, CGImageGetHeight,
)
from ApplicationServices import (
    AXUIElementCreateApplication, AXUIElementCopyAttributeValue,
    AXUIElementPerformAction, AXIsProcessTrustedWithOptions,
    AXValueGetValue, kAXValueCGPointType, kAXValueCGSizeType,
)

# ScreenCaptureKit — the modern capture path (macOS 14+, incl. 26)
try:
    from ScreenCaptureKit import (
        SCShareableContent, SCContentFilter, SCStreamConfiguration,
        SCScreenshotManager,
    )
    SCK_AVAILABLE = True
except Exception:
    SCK_AVAILABLE = False

# ───────────────────────────── CONFIG ──────────────────────────────────────
class CFG:
    FAST_TICK          = 0.05
    SLOW_TICK          = 0.50
    MIN_W, MIN_H       = 250, 150
    LIGHT_DIAM         = 12.0
    LIGHT_SPACING      = 20.0
    CLUSTER_HPAD       = 7.0      # horizontal padding around light cluster
    CLUSTER_VPAD       = 5.0      # vertical padding around light cluster
    TITLEBAR_H         = 28.0
    PILL_ALPHA         = 0.94     # backing pill opacity (right lights)
    MIRROR_CONTENT     = True
    SCK_CONTENT_TTL    = 5.0      # secs between SCK window-list refreshes
    SKIN_ALL_APPS      = False
    FALLBACK_OFFSETS   = {"close": 6, "minimize": 29, "zoom": 52}
    RETIRE_GRACE       = 1.25
    FRONTMOST_IGNORE   = {"Screenshot", "screencaptureui", "Python",
                          "python3.12", "WindowsintheApple", "Dock",
                          "Control Center", "Notification Center",
                          "Spotlight"}
    IGNORED_APPS       = {"Dock", "Window Server", "Control Center",
                          "Notification Center", "Spotlight",
                          "WindowsintheApple"}
    LOG_PATH  = os.path.expanduser("~/Library/Logs/WindowsintheApple.log")
    PLIST     = os.path.expanduser(
        "~/Library/LaunchAgents/com.punks.windowsintheapple.plist")

COL_CLOSE  = (1.000, 0.373, 0.341)
COL_MIN    = (0.996, 0.737, 0.180)
COL_ZOOM   = (0.157, 0.784, 0.251)
COL_BORDER = 0.72
COL_GLYPH  = (0.30, 0.10, 0.08)
DEFAULT_BG = (0.13, 0.13, 0.14)

# ───────────────────────────── LOGGING ─────────────────────────────────────
logger = logging.getLogger("WITA")

def setup_logging(debug: bool):
    logger.setLevel(logging.DEBUG if debug else logging.INFO)
    fmt = logging.Formatter("%(asctime)s %(levelname)-7s %(message)s",
                            "%H:%M:%S")
    fh = RotatingFileHandler(CFG.LOG_PATH, maxBytes=2_000_000, backupCount=2)
    fh.setFormatter(fmt)
    sh = logging.StreamHandler()
    sh.setFormatter(fmt)
    logger.addHandler(fh)
    logger.addHandler(sh)

# ───────────────────────────── AX HELPERS ──────────────────────────────────
def ax_attr(el, name):
    err, val = AXUIElementCopyAttributeValue(el, name, None)
    return val if err == 0 else None

def ax_point(v):
    ok, pt = AXValueGetValue(v, kAXValueCGPointType, None)
    return (pt.x, pt.y) if ok else None

def ax_size(v):
    ok, sz = AXValueGetValue(v, kAXValueCGSizeType, None)
    return (sz.width, sz.height) if ok else None

def ax_frame(win):
    p = ax_attr(win, "AXPosition")
    s = ax_attr(win, "AXSize")
    if p is None or s is None:
        return None
    pos, size = ax_point(p), ax_size(s)
    if pos is None or size is None:
        return None
    return (pos[0], pos[1], size[0], size[1])   # global TOP-LEFT origin

def app_ax_windows(pid):
    app = AXUIElementCreateApplication(pid)
    wins = ax_attr(app, "AXWindows")
    return list(wins) if wins else []

def find_ax_window(pid, cg_frame, tol=8.0):
    x, y, w, h = cg_frame
    best, best_d = None, tol * 4
    for win in app_ax_windows(pid):
        f = ax_frame(win)
        if not f:
            continue
        d = abs(f[0]-x) + abs(f[1]-y) + abs(f[2]-w) + abs(f[3]-h)
        if d < best_d:
            best, best_d = win, d
    return best

def press_traffic_light(pid, cg_frame, which):
    win = find_ax_window(pid, cg_frame)
    if win is None:
        logger.warning("CLICK: no AX window match for %s", which)
        return False
    attr = {"close": "AXCloseButton",
            "minimize": "AXMinimizeButton",
            "zoom": "AXZoomButton"}[which]
    btn = ax_attr(win, attr)
    if btn is None:
        logger.warning("CLICK: window lacks %s", attr)
        return False
    err = AXUIElementPerformAction(btn, "AXPress")
    logger.info("CLICK: %s → AXPress err=%s", which, err)
    return err == 0

def native_lights_geometry(pid, cg_frame):
    """→ (offsets, cluster) where cluster = (a, y_off, cw, ch) is the tight
    bounding pill of the light cluster, relative to the window's top-left.
    Sized from REAL AX button frames; all-or-nothing fallback keeps
    mirrored spacing symmetric on AX-hostile apps (Steam, Electron)."""
    win = find_ax_window(pid, cg_frame)
    offsets, btn_y, btn_h = {}, None, CFG.LIGHT_DIAM
    if win is not None:
        x0, y0 = cg_frame[0], cg_frame[1]
        for label, attr in (("close", "AXCloseButton"),
                            ("minimize", "AXMinimizeButton"),
                            ("zoom", "AXZoomButton")):
            btn = ax_attr(win, attr)
            f = ax_frame(btn) if btn is not None else None
            if f:
                offsets[label] = f[0] - x0
                if btn_y is None:
                    btn_y, btn_h = f[1] - y0, f[3]
    if len(offsets) != 3:                       # all-or-nothing rule
        offsets = dict(CFG.FALLBACK_OFFSETS)
        btn_y, btn_h = (CFG.TITLEBAR_H - CFG.LIGHT_DIAM) / 2, CFG.LIGHT_DIAM
    a  = min(offsets.values()) - CFG.CLUSTER_HPAD
    cw = (max(offsets.values()) + CFG.LIGHT_DIAM + CFG.CLUSTER_HPAD) - a
    ch = btn_h + 2 * CFG.CLUSTER_VPAD
    y_off = max(0.0, btn_y - CFG.CLUSTER_VPAD)
    return offsets, (a, y_off, cw, ch)

# ─────────────────────── COORDINATES ───────────────────────────────────────
def primary_screen_h():
    return NSScreen.screens()[0].frame().size.height

def topleft_to_appkit(x, y_top, w, h):
    return NSMakeRect(x, primary_screen_h() - (y_top + h), w, h)

# ─────────────────────── CAPTURE: SCK + LEGACY ─────────────────────────────
def _avg_color_of_cgimage(cgimg):
    try:
        rep = NSBitmapImageRep.alloc().initWithCGImage_(cgimg)
        w, h = rep.pixelsWide(), rep.pixelsHigh()
        if w < 2 or h < 2:
            return None
        r = g = b = 0.0
        pts = [(int(w*0.2), int(h*0.5)), (int(w*0.5), int(h*0.15)),
               (int(w*0.8), int(h*0.5))]
        for x, y in pts:
            c = rep.colorAtX_y_(x, y)
            r += c.redComponent(); g += c.greenComponent()
            b += c.blueComponent()
        n = len(pts)
        return NSColor.colorWithSRGBRed_green_blue_alpha_(r/n, g/n, b/n, 1)
    except Exception:
        return None


class SCKMirror:
    """Async ScreenCaptureKit capture of a window's top-right strip.
    Caches the SCWindow list (TTL) and delivers (NSImage, NSColor)
    through a callback — never blocks the render loop."""
    def __init__(self):
        self._windows = {}          # CGWindowID → SCWindow
        self._stamp = 0.0
        self._lock = threading.Lock()
        self._dead = False
        self._fail_streak = 0
        self._refreshing = False

    def _refresh_content(self):
        if self._refreshing:
            return
        self._refreshing = True
        def handler(content, error):
            try:
                if error is not None or content is None:
                    self._fail_streak += 1
                    if self._fail_streak >= 3 and not self._dead:
                        self._dead = True
                        logger.warning(
                            "MIRROR: SCK content unavailable (Screen "
                            "Recording permission?) — solid mask fallback")
                    return
                self._fail_streak = 0
                wins = {}
                for w in content.windows():
                    wins[w.windowID()] = w
                with self._lock:
                    self._windows = wins
                    self._stamp = time.time()
            finally:
                self._refreshing = False
        try:
            SCShareableContent.\
                getShareableContentExcludingDesktopWindows_onScreenWindowsOnly_completionHandler_(
                    False, True, handler)
        except Exception as e:
            self._refreshing = False
            logger.debug("MIRROR: content refresh failed: %s", e)

    def request(self, window_id, src_rect_pts, out_w, out_h, callback):
        """src_rect_pts: (x, y, w, h) in window-content points, top-left
        origin. callback(nsimage|None, nscolor|None) from a bg thread."""
        if self._dead or not CFG.MIRROR_CONTENT:
            return
        now = time.time()
        if now - self._stamp > CFG.SCK_CONTENT_TTL:
            self._refresh_content()
        with self._lock:
            scw = self._windows.get(window_id)
        if scw is None:
            return
        try:
            filt = SCContentFilter.alloc().initWithDesktopIndependentWindow_(scw)
            cfg = SCStreamConfiguration.alloc().init()
            x, y, w, h = src_rect_pts
            cfg.setSourceRect_(CGRectMake(x, y, w, h))
            cfg.setWidth_(int(out_w * 2))     # 2x for retina crispness
            cfg.setHeight_(int(out_h * 2))
            cfg.setShowsCursor_(False)
            def done(cgimg, error):
                if error is not None or cgimg is None:
                    self._fail_streak += 1
                    if self._fail_streak >= 5 and not self._dead:
                        self._dead = True
                        logger.warning(
                            "MIRROR: SCK capture denied — grant Screen "
                            "Recording to the agent's python, then restart")
                    return
                self._fail_streak = 0
                try:
                    ns = NSImage.alloc().initWithCGImage_size_(
                        cgimg, NSMakeRect(0, 0, out_w, out_h).size)
                except Exception:
                    ns = None
                callback(ns, _avg_color_of_cgimage(cgimg))
            SCScreenshotManager.\
                captureImageWithFilter_configuration_completionHandler_(
                    filt, cfg, done)
        except Exception as e:
            logger.debug("MIRROR: SCK request failed: %s", e)

SCK = SCKMirror() if SCK_AVAILABLE else None

_legacy_dead = False

def legacy_capture_strip(window_id, win_w, src_rect_pts, out_w, out_h):
    """CGWindowListCreateImage path for macOS <= 13. → (img, color)."""
    global _legacy_dead
    if _legacy_dead or not CFG.MIRROR_CONTENT:
        return None, None
    try:
        img = Quartz.CGWindowListCreateImage(
            CGRectNull, kCGWindowListOptionIncludingWindow,
            window_id, Quartz.kCGWindowImageBoundsIgnoreFraming)
        if img is None:
            _legacy_dead = True
            logger.warning("MIRROR: legacy capture unavailable — "
                           "solid mask fallback")
            return None, None
        iw = CGImageGetWidth(img)
        scale = iw / max(win_w, 1.0)
        x, y, w, h = src_rect_pts
        sub = Quartz.CGImageCreateWithImageInRect(
            img, CGRectMake(x*scale, y*scale, w*scale, h*scale))
        if sub is None:
            return None, None
        ns = NSImage.alloc().initWithCGImage_size_(
            sub, NSMakeRect(0, 0, out_w, out_h).size)
        return ns, _avg_color_of_cgimage(sub)
    except Exception as e:
        logger.debug("MIRROR: legacy capture failed: %s", e)
        return None, None

# ───────────────────────────── VIEWS ───────────────────────────────────────
class MaskView(NSView):
    """Tight rounded pill over the native lights; renders the live-mirrored
    right-strip content inside it."""
    def initWithFrame_(self, frame):
        self = objc.super(MaskView, self).initWithFrame_(frame)
        if self is None:
            return None
        self.bg = NSColor.colorWithSRGBRed_green_blue_alpha_(*DEFAULT_BG, 1)
        self.mirror = None
        return self

    def drawRect_(self, rect):
        b = self.bounds()
        rad = b.size.height / 2.0
        pill = NSBezierPath.bezierPathWithRoundedRect_xRadius_yRadius_(
            b, rad, rad)
        pill.addClip()
        self.bg.setFill()
        NSBezierPath.fillRect_(b)
        if self.mirror is not None:
            self.mirror.drawInRect_fromRect_operation_fraction_(
                b, NSMakeRect(0, 0, 0, 0),
                NSCompositingOperationSourceOver, 1.0)

    def mouseDown_(self, event):  pass
    def mouseUp_(self, event):    pass


class LightsView(NSView):
    """Fake lights on a subtle titlebar-matched backing pill.
    Circle positions are the exact horizontal mirror of the native
    cluster geometry (close lands in the corner, Windows-style)."""
    def initWithFrame_(self, frame):
        self = objc.super(LightsView, self).initWithFrame_(frame)
        if self is None:
            return None
        self.hovered = False
        self.on_click = None
        self.pill = NSColor.colorWithSRGBRed_green_blue_alpha_(
            *DEFAULT_BG, CFG.PILL_ALPHA)
        self.offsets = dict(CFG.FALLBACK_OFFSETS)
        self.cluster_a = min(self.offsets.values()) - CFG.CLUSTER_HPAD
        self._tracking = None
        return self

    def updateTrackingAreas(self):
        if self._tracking:
            self.removeTrackingArea_(self._tracking)
        self._tracking = NSTrackingArea.alloc().\
            initWithRect_options_owner_userInfo_(
                self.bounds(),
                NSTrackingMouseEnteredAndExited | NSTrackingActiveAlways,
                self, None)
        self.addTrackingArea_(self._tracking)
        objc.super(LightsView, self).updateTrackingAreas()

    def mouseEntered_(self, e):
        self.hovered = True
        self.setNeedsDisplay_(True)

    def mouseExited_(self, e):
        self.hovered = False
        self.setNeedsDisplay_(True)

    @objc.python_method
    def _circles(self):
        b = self.bounds()
        d = CFG.LIGHT_DIAM
        cy = b.size.height / 2.0
        out = []
        for which in ("close", "minimize", "zoom"):
            native_center = self.offsets[which] - self.cluster_a + d/2.0
            cx = b.size.width - native_center      # horizontal mirror
            out.append((which, cx, cy, d/2.0))
        return out

    def drawRect_(self, rect):
        b = self.bounds()
        rad = b.size.height / 2.0
        pill = NSBezierPath.bezierPathWithRoundedRect_xRadius_yRadius_(
            b, rad, rad)
        self.pill.setFill()
        pill.fill()
        for which, cx, cy, r in self._circles():
            col = {"close": COL_CLOSE, "minimize": COL_MIN,
                   "zoom": COL_ZOOM}[which]
            circle = NSBezierPath.bezierPathWithOvalInRect_(
                NSMakeRect(cx-r, cy-r, 2*r, 2*r))
            NSColor.colorWithSRGBRed_green_blue_alpha_(*col, 1.0).setFill()
            circle.fill()
            NSColor.colorWithSRGBRed_green_blue_alpha_(
                col[0]*COL_BORDER, col[1]*COL_BORDER,
                col[2]*COL_BORDER, 1.0).setStroke()
            circle.setLineWidth_(0.5)
            circle.stroke()
            if self.hovered:
                self._glyph(which, cx, cy, r)

    @objc.python_method
    def _glyph(self, which, cx, cy, r):
        NSColor.colorWithSRGBRed_green_blue_alpha_(*COL_GLYPH, .95).setStroke()
        p = NSBezierPath.bezierPath()
        p.setLineWidth_(1.4)
        g = r * 0.42
        if which == "close":
            p.moveToPoint_(NSMakePoint(cx-g, cy-g))
            p.lineToPoint_(NSMakePoint(cx+g, cy+g))
            p.moveToPoint_(NSMakePoint(cx-g, cy+g))
            p.lineToPoint_(NSMakePoint(cx+g, cy-g))
            p.stroke()
        elif which == "minimize":
            p.moveToPoint_(NSMakePoint(cx-g, cy))
            p.lineToPoint_(NSMakePoint(cx+g, cy))
            p.stroke()
        else:
            NSColor.colorWithSRGBRed_green_blue_alpha_(*COL_GLYPH, .95).setFill()
            t = NSBezierPath.bezierPath()
            t.moveToPoint_(NSMakePoint(cx-g, cy+g*0.2))
            t.lineToPoint_(NSMakePoint(cx-g, cy+g))
            t.lineToPoint_(NSMakePoint(cx-g*0.2, cy+g))
            t.closePath(); t.fill()
            t2 = NSBezierPath.bezierPath()
            t2.moveToPoint_(NSMakePoint(cx+g, cy-g*0.2))
            t2.lineToPoint_(NSMakePoint(cx+g, cy-g))
            t2.lineToPoint_(NSMakePoint(cx+g*0.2, cy-g))
            t2.closePath(); t2.fill()

    def mouseDown_(self, e):
        pt = self.convertPoint_fromView_(e.locationInWindow(), None)
        for which, cx, cy, r in self._circles():
            if math.hypot(pt.x - cx, pt.y - cy) <= r + 3:
                if self.on_click:
                    self.on_click(which)
                return

# ───────────────────────────── OVERLAY PAIR ────────────────────────────────
def _make_overlay_window(rect):
    w = NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
        rect, NSWindowStyleMaskBorderless, NSBackingStoreBuffered, False)
    w.setOpaque_(False)
    w.setReleasedWhenClosed_(False)   # CRITICAL: dealloc-on-close fix
    w.setBackgroundColor_(NSColor.clearColor())
    w.setLevel_(NSFloatingWindowLevel)
    w.setHasShadow_(False)
    w.setCollectionBehavior_(
        NSWindowCollectionBehaviorCanJoinAllSpaces |
        NSWindowCollectionBehaviorFullScreenAuxiliary |
        NSWindowCollectionBehaviorTransient)
    w.setTitle_("WITA_OVERLAY")
    return w


class OverlayPair:
    def __init__(self, pid, window_id):
        self.pid = pid
        self.window_id = window_id
        self.cg_frame = None
        self.offsets = dict(CFG.FALLBACK_OFFSETS)
        self.cluster = (min(self.offsets.values()) - CFG.CLUSTER_HPAD,
                        (CFG.TITLEBAR_H - CFG.LIGHT_DIAM)/2 - CFG.CLUSTER_VPAD,
                        (max(self.offsets.values()) + CFG.LIGHT_DIAM +
                         CFG.CLUSTER_HPAD) -
                        (min(self.offsets.values()) - CFG.CLUSTER_HPAD),
                        CFG.LIGHT_DIAM + 2*CFG.CLUSTER_VPAD)
        self.last_seen = time.time()
        self._pending = None          # (NSImage|None, NSColor|None)

        a, y_off, cw, ch = self.cluster
        r = NSMakeRect(0, 0, cw, ch)
        self.mask_win = _make_overlay_window(r)
        self.mask_view = MaskView.alloc().initWithFrame_(r)
        self.mask_win.setContentView_(self.mask_view)

        self.lights_win = _make_overlay_window(r)
        self.lights_view = LightsView.alloc().initWithFrame_(r)
        self.lights_view.on_click = self._clicked
        self.lights_win.setContentView_(self.lights_view)
        self.lights_win.setIgnoresMouseEvents_(False)
        self.mask_win.setIgnoresMouseEvents_(False)

    def _clicked(self, which):
        if self.cg_frame:
            press_traffic_light(self.pid, self.cg_frame, which)

    # fast tick: reposition (cluster-precise geometry, mirrored on right)
    def track(self, cg_frame):
        self.cg_frame = cg_frame
        x, y, w, h = cg_frame
        a, y_off, cw, ch = self.cluster
        mask_rect   = topleft_to_appkit(x + a,          y + y_off, cw, ch)
        lights_rect = topleft_to_appkit(x + w - a - cw, y + y_off, cw, ch)
        self.mask_win.setFrame_display_(mask_rect, False)
        self.lights_win.setFrame_display_(lights_rect, False)
        if not self.mask_win.isVisible():
            self.mask_win.orderFrontRegardless()
            self.lights_win.orderFrontRegardless()

    # slow tick: geometry from AX, async mirror capture
    def refresh(self):
        if not self.cg_frame:
            return
        self.offsets, self.cluster = native_lights_geometry(
            self.pid, self.cg_frame)
        a, y_off, cw, ch = self.cluster
        self.lights_view.offsets = self.offsets
        self.lights_view.cluster_a = a
        W = self.cg_frame[2]
        src = (W - a - cw, y_off, cw, ch)     # exact region lights cover
        if SCK is not None:
            SCK.request(self.window_id, src, cw, ch, self._mirror_arrived)
        else:
            img, col = legacy_capture_strip(
                self.window_id, W, src, cw, ch)
            if img is not None or col is not None:
                self._pending = (img, col)
        self.mask_view.setNeedsDisplay_(True)
        self.lights_view.setNeedsDisplay_(True)

    def _mirror_arrived(self, img, col):      # bg thread: stash only
        self._pending = (img, col)

    def apply_pending(self):                  # main thread: paint
        if self._pending is None:
            return
        img, col = self._pending
        self._pending = None
        if img is not None:
            self.mask_view.mirror = img
        if col is not None:
            self.mask_view.bg = col
            self.lights_view.pill = col.colorWithAlphaComponent_(
                CFG.PILL_ALPHA)
        self.mask_view.setNeedsDisplay_(True)
        self.lights_view.setNeedsDisplay_(True)

    def hide(self):
        self.mask_win.orderOut_(None)
        self.lights_win.orderOut_(None)

    def destroy(self):
        self.hide()
        self.lights_view.on_click = None
        self.mask_win.setContentView_(None)
        self.lights_win.setContentView_(None)
        self.mask_win.close()
        self.lights_win.close()

# ───────────────────────────── ENGINE ──────────────────────────────────────
class Engine(NSObject):
    def init(self):
        self = objc.super(Engine, self).init()
        if self is None:
            return None
        self.pairs = {}
        self.last_front_pid = -1
        self._slow_accum = 0.0
        return self

    @objc.python_method
    def start(self):
        t = NSTimer.timerWithTimeInterval_target_selector_userInfo_repeats_(
            CFG.FAST_TICK, self, "tick:", None, True)
        NSRunLoop.currentRunLoop().addTimer_forMode_(t, NSRunLoopCommonModes)
        logger.info("ENGINE: started · fast=%.0fms slow=%.0fms mirror=%s "
                    "sck=%s", CFG.FAST_TICK*1000, CFG.SLOW_TICK*1000,
                    CFG.MIRROR_CONTENT, SCK_AVAILABLE)

    @objc.python_method
    def _eligible_windows(self):
        ws = NSWorkspace.sharedWorkspace()
        front = ws.frontmostApplication()
        front_pid = front.processIdentifier() if front else -1
        front_name = front.localizedName() if front else ""
        if front is None or front_name in CFG.FRONTMOST_IGNORE \
                or front_pid == os.getpid():
            front_pid = self.last_front_pid      # hold previous focus
        else:
            self.last_front_pid = front_pid
        own_pid = os.getpid()
        out = {}
        infos = CGWindowListCopyWindowInfo(
            kCGWindowListOptionOnScreenOnly |
            kCGWindowListExcludeDesktopElements, kCGNullWindowID) or []
        scr = NSScreen.screens()[0].frame()
        for info in infos:
            pid = info.get("kCGWindowOwnerPID", -1)
            if pid == own_pid:
                continue
            if not CFG.SKIN_ALL_APPS and pid != front_pid:
                continue
            if info.get("kCGWindowLayer", 1) != 0:
                continue
            owner = info.get("kCGWindowOwnerName", "")
            if owner in CFG.IGNORED_APPS:
                continue
            if info.get("kCGWindowAlpha", 1) <= 0.05:
                continue
            b = info.get("kCGWindowBounds", {})
            x, y = b.get("X", 0), b.get("Y", 0)
            w, h = b.get("Width", 0), b.get("Height", 0)
            if w < CFG.MIN_W or h < CFG.MIN_H:
                continue
            if (w >= scr.size.width - 2 and h >= scr.size.height - 2
                    and x <= 1 and y <= 1):
                continue
            out[info["kCGWindowNumber"]] = (pid, (x, y, w, h))
        return out

    def tick_(self, timer):
        try:
            self._tick()
        except Exception:
            logger.exception("TICK: unhandled")

    @objc.python_method
    def _tick(self):
        eligible = self._eligible_windows()
        now = time.time()

        for wid in list(self.pairs):
            pair = self.pairs[wid]
            if wid in eligible:
                pair.last_seen = now
            elif now - pair.last_seen > CFG.RETIRE_GRACE:
                self.pairs.pop(wid).destroy()
                logger.debug("SKIN: -window id=%s retired", wid)

        slow = False
        self._slow_accum += CFG.FAST_TICK
        if self._slow_accum >= CFG.SLOW_TICK:
            self._slow_accum = 0.0
            slow = True

        for wid, (pid, frame) in eligible.items():
            pair = self.pairs.get(wid)
            if pair is None:
                pair = OverlayPair(pid, wid)
                pair.last_seen = now
                self.pairs[wid] = pair
                pair.refresh()                # AX geometry first,
                pair.track(frame)             # then position with it
                mf, lf = pair.mask_win.frame(), pair.lights_win.frame()
                logger.info("SKIN: +window id=%s pid=%s w=%d h=%d", wid,
                            pid, frame[2], frame[3])
                logger.debug("SKIN: mask=(%.0f,%.0f %dx%d) "
                             "lights=(%.0f,%.0f %dx%d)",
                             mf.origin.x, mf.origin.y,
                             mf.size.width, mf.size.height,
                             lf.origin.x, lf.origin.y,
                             lf.size.width, lf.size.height)
                continue
            pair.track(frame)
            pair.apply_pending()
            if slow:
                pair.refresh()

    @objc.python_method
    def shutdown(self):
        for pair in self.pairs.values():
            pair.destroy()
        self.pairs.clear()

# ─────────────────────── PERMISSIONS / LAUNCHD ─────────────────────────────
def ensure_ax_permission():
    opts = {"AXTrustedCheckOptionPrompt": True}
    trusted = AXIsProcessTrustedWithOptions(opts)
    if not trusted:
        logger.error("PERM: Accessibility not granted — clicks will fail. "
                     "System Settings → Privacy & Security → Accessibility")
    return trusted

PLIST_BODY = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
 "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>com.punks.windowsintheapple</string>
  <key>ProgramArguments</key><array>
    <string>{python}</string>
    <string>{script}</string>
  </array>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
  <key>StandardOutPath</key><string>{log}.launchd</string>
  <key>StandardErrorPath</key><string>{log}.launchd</string>
</dict></plist>
"""

def install_agent():
    script = os.path.abspath(__file__)
    python = sys.executable
    body = PLIST_BODY.format(python=python, script=script, log=CFG.LOG_PATH)
    os.makedirs(os.path.dirname(CFG.PLIST), exist_ok=True)
    with open(CFG.PLIST, "w") as f:
        f.write(body)
    subprocess.run(["launchctl", "unload", CFG.PLIST],
                   capture_output=True)
    subprocess.run(["launchctl", "load", CFG.PLIST], check=True)
    print(f"✓ launchd agent installed + loaded: {CFG.PLIST}")

def uninstall_agent():
    subprocess.run(["launchctl", "unload", CFG.PLIST], capture_output=True)
    if os.path.exists(CFG.PLIST):
        os.remove(CFG.PLIST)
    print("✓ launchd agent unloaded + removed")

# ───────────────────────────── MAIN ────────────────────────────────────────
def main():
    if "--install" in sys.argv:
        install_agent(); return
    if "--uninstall" in sys.argv:
        uninstall_agent(); return

    setup_logging("--debug" in sys.argv)
    logger.info("═" * 60)
    logger.info("WINDOWSINTHEAPPLE v2.1 · pid=%s · python=%s · sck=%s",
                os.getpid(), sys.version.split()[0], SCK_AVAILABLE)
    ensure_ax_permission()

    app = NSApplication.sharedApplication()
    app.setActivationPolicy_(NSApplicationActivationPolicyAccessory)

    engine = Engine.alloc().init()
    engine.start()

    def _bye(sig, frm):
        logger.info("ENGINE: signal %s — cleaning up", sig)
        engine.shutdown()
        os._exit(0)
    signal.signal(signal.SIGINT, _bye)
    signal.signal(signal.SIGTERM, _bye)

    app.run()

if __name__ == "__main__":
    main()
