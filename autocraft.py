import sys
import os
import time
import threading
import tkinter as tk
from tkinter import messagebox

import pyautogui
import cv2
import numpy as np
from PIL import ImageGrab

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _resource_path(relative: str) -> str:
    """Return absolute path to a resource, works for dev and PyInstaller."""
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, relative)


# ---------------------------------------------------------------------------
# US-002: Image recognition
# ---------------------------------------------------------------------------

def find_image(image_path: str, confidence: float = 0.8):
    """
    Locate a single occurrence of *image_path* on the screen.

    Returns (x, y) centre of the first match or None if not found.
    """
    template = cv2.imread(image_path, cv2.IMREAD_COLOR)
    if template is None:
        return None

    screenshot = np.array(ImageGrab.grab())
    screenshot_bgr = cv2.cvtColor(screenshot, cv2.COLOR_RGB2BGR)

    result = cv2.matchTemplate(screenshot_bgr, template, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, max_loc = cv2.minMaxLoc(result)

    if max_val < confidence:
        return None

    h, w = template.shape[:2]
    cx = max_loc[0] + w // 2
    cy = max_loc[1] + h // 2
    return (cx, cy)


def find_all_images(image_path: str, confidence: float = 0.8):
    """
    Locate ALL occurrences of *image_path* on the screen.

    Returns a list of (x, y) centres; empty list if none found.
    """
    template = cv2.imread(image_path, cv2.IMREAD_COLOR)
    if template is None:
        return []

    screenshot = np.array(ImageGrab.grab())
    screenshot_bgr = cv2.cvtColor(screenshot, cv2.COLOR_RGB2BGR)

    result = cv2.matchTemplate(screenshot_bgr, template, cv2.TM_CCOEFF_NORMED)
    h, w = template.shape[:2]

    locations = []
    result_copy = result.copy()

    while True:
        _, max_val, _, max_loc = cv2.minMaxLoc(result_copy)
        if max_val < confidence:
            break

        cx = max_loc[0] + w // 2
        cy = max_loc[1] + h // 2
        locations.append((cx, cy))

        # Suppress this match so the next iteration finds a different one
        top_left = max_loc
        result_copy[
            top_left[1] : top_left[1] + h,
            top_left[0] : top_left[0] + w,
        ] = 0

    return locations


# ---------------------------------------------------------------------------
# US-003: Craft logic
# ---------------------------------------------------------------------------

CLICK_DELAY = 0.1  # seconds between map clicks


def do_craft(currency_type: str):
    """
    Execute craft for *currency_type* ('alchemy' or 'scouring').

    1. Locate the currency image on screen and right-click it.
    2. Find all t16 / t16-5 maps and shift+left-click each one.
    """
    image_dir = _resource_path("image")
    currency_img = os.path.join(image_dir, f"{currency_type}.png")

    pos = find_image(currency_img, confidence=0.8)
    if pos is None:
        messagebox.showerror(
            "AutoCraft",
            f"Currency '{currency_type}' não encontrada na tela.\n"
            "Certifique-se de que o jogo está visível.",
        )
        return

    pyautogui.rightClick(pos[0], pos[1])
    time.sleep(0.3)

    # Gather all map positions
    maps = []
    for map_name in ("t16", "t16-5"):
        img_path = os.path.join(image_dir, f"{map_name}.png")
        maps.extend(find_all_images(img_path, confidence=0.8))

    if not maps:
        messagebox.showerror(
            "AutoCraft",
            "Nenhum mapa T16/T16-5 encontrado na tela.\n"
            "Certifique-se de que os mapas estão visíveis.",
        )
        return

    pyautogui.keyDown("shift")
    try:
        for mx, my in maps:
            pyautogui.click(mx, my, button="left")
            time.sleep(CLICK_DELAY)
    finally:
        pyautogui.keyUp("shift")


# ---------------------------------------------------------------------------
# US-004: GUI
# ---------------------------------------------------------------------------

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("AutoCraft")
        self.resizable(False, False)
        self.attributes("-topmost", True)

        pad = {"padx": 10, "pady": 6}

        self.btn_alchemy = tk.Button(
            self,
            text="Alchemy",
            width=14,
            bg="#c8a84b",
            fg="white",
            font=("Segoe UI", 11, "bold"),
            command=lambda: self._run("alchemy"),
        )
        self.btn_alchemy.pack(**pad)

        self.btn_scouring = tk.Button(
            self,
            text="Scouring",
            width=14,
            bg="#7b8c9c",
            fg="white",
            font=("Segoe UI", 11, "bold"),
            command=lambda: self._run("scouring"),
        )
        self.btn_scouring.pack(**pad)

        self.status = tk.Label(self, text="Pronto", font=("Segoe UI", 9))
        self.status.pack(pady=(0, 6))

    def _set_busy(self, busy: bool):
        state = tk.DISABLED if busy else tk.NORMAL
        self.btn_alchemy.config(state=state)
        self.btn_scouring.config(state=state)
        self.status.config(text="Executando..." if busy else "Pronto")

    def _run(self, currency_type: str):
        self._set_busy(True)

        def task():
            try:
                do_craft(currency_type)
            finally:
                self.after(0, lambda: self._set_busy(False))

        threading.Thread(target=task, daemon=True).start()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    app = App()
    app.mainloop()
