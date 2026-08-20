import io
import os
import queue
import sys
import threading
import tkinter as tk

try:
    from PIL import Image
    HAS_PIL = True
except Exception:
    HAS_PIL = False

ASSETS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "assets")

SPRITES = {
    "active": ["SpriteActive.png"],
    "blocked": ["Spriteblocked.png"],
    "issue": ["Spriteissue.png"],
    "offline": ["Spriteoffline.png", "SpriteOffline.png"],
}

ICON_SIZE = 32
BG = "#FF00FF"

if sys.platform == "win32":
    import ctypes
    user32 = ctypes.windll.user32
    GWL_EXSTYLE = -20
    WS_EX_LAYERED = 0x00080000
    WS_EX_TRANSPARENT = 0x00000020
    WS_EX_NOACTIVATE = 0x08000000


class OverlayService:
    def __init__(self):
        self.enabled = False
        self.state = "offline"
        self._queue = queue.Queue()
        self._thread = None
        self._root = None
        self._label = None
        self._images = {}

    def set_enabled(self, enabled):
        self.enabled = bool(enabled)
        if self.enabled and self._thread is None:
            self._thread = threading.Thread(target=self._run, daemon=True)
            self._thread.start()
        self._queue.put(("enabled", self.enabled))

    def set_state(self, state):
        if state not in SPRITES:
            return
        self.state = state
        self._queue.put(("state", state))

    def _prepare(self, pil_img):
        img = pil_img.resize((ICON_SIZE, ICON_SIZE), Image.LANCZOS).convert("RGBA")
        alpha = img.getchannel("A").point(lambda v: 255 if v >= 128 else 0)
        img.putalpha(alpha)
        bg = Image.new("RGBA", (ICON_SIZE, ICON_SIZE), (255, 0, 255, 255))
        comp = Image.alpha_composite(bg, img).convert("RGB")
        buf = io.BytesIO()
        comp.save(buf, format="PNG")
        return tk.PhotoImage(data=buf.getvalue())

    def _load_native(self, path):
        img = tk.PhotoImage(file=path)
        fx = max(1, round(img.width() / ICON_SIZE))
        fy = max(1, round(img.height() / ICON_SIZE))
        if fx > 1 or fy > 1:
            img = img.subsample(fx, fy)
        return img

    def _load_images(self):
        for key, candidates in SPRITES.items():
            self._images[key] = None
            for fname in candidates:
                path = os.path.join(ASSETS_DIR, fname)
                if not os.path.exists(path):
                    continue
                if HAS_PIL:
                    try:
                        self._images[key] = self._prepare(Image.open(path))
                        break
                    except Exception:
                        pass
                try:
                    self._images[key] = self._load_native(path)
                    break
                except tk.TclError:
                    continue
            if self._images[key] is None and key == "offline":
                blocked_path = os.path.join(ASSETS_DIR, SPRITES["blocked"][0])
                if os.path.exists(blocked_path):
                    if HAS_PIL:
                        try:
                            base = Image.open(blocked_path).convert("RGBA")
                            l = base.convert("L")
                            gray = Image.merge("RGBA", (l, l, l, base.getchannel("A")))
                            self._images[key] = self._prepare(gray)
                        except Exception:
                            pass
                    if self._images[key] is None:
                        try:
                            self._images[key] = self._load_native(blocked_path)
                        except tk.TclError:
                            pass

    def _run(self):
        root = tk.Tk()
        self._root = root
        root.title("voice-overlay")
        root.overrideredirect(True)
        root.attributes("-topmost", True)
        try:
            root.attributes("-toolwindow", True)
        except tk.TclError:
            pass
        root.config(bg=BG)
        label = tk.Label(root, bg=BG, bd=0, highlightthickness=0)
        label.pack()
        self._label = label
        try:
            root.attributes("-transparentcolor", BG)
        except tk.TclError:
            pass
        self._load_images()
        self._apply()
        self._position()
        root.update()
        if not self.enabled:
            root.withdraw()
        else:
            self._make_click_through()
        root.after(80, self._poll)
        root.mainloop()

    def _make_click_through(self):
        if sys.platform != "win32":
            return
        try:
            self._root.update()
            hwnd = int(self._root.wm_frame(), 16)
            ex = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            ex |= WS_EX_LAYERED | WS_EX_TRANSPARENT | WS_EX_NOACTIVATE
            user32.SetWindowLongW(hwnd, GWL_EXSTYLE, ex)
        except Exception:
            pass

    def _poll(self):
        try:
            while True:
                kind, value = self._queue.get_nowait()
                if kind == "enabled":
                    if value:
                        self._apply()
                        self._position()
                        self._root.deiconify()
                        self._make_click_through()
                    else:
                        self._root.withdraw()
                elif kind == "state":
                    if self.enabled:
                        self._apply()
                        self._position()
        except queue.Empty:
            pass
        self._root.after(80, self._poll)

    def _apply(self):
        img = self._images.get(self.state)
        if img is not None and self._label is not None:
            self._label.config(image=img)
            self._label.image = img

    def _position(self):
        root = self._root
        root.update_idletasks()
        w = root.winfo_width()
        h = root.winfo_height()
        x = (root.winfo_screenwidth() - w) // 2
        y = int(root.winfo_screenheight() * 0.72) - h // 2
        root.geometry(f"+{x}+{y}")