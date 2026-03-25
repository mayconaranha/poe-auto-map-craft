import sys
import os
import time
import threading
import json
import tkinter as tk

import keyboard
import pyautogui
import cv2
import numpy as np
from PIL import ImageGrab

pyautogui.PAUSE = 0.02

# ---------------------------------------------------------------------------
# Log
# ---------------------------------------------------------------------------

def _log_path():
    if getattr(sys, "frozen", False):
        base = os.path.dirname(sys.executable)
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, "autocraft_log.txt")

_log_file = None

def _log_init():
    global _log_file
    _log_file = open(_log_path(), "w", encoding="utf-8")
    _log("=== AutoCraft Log ===")

def _log(msg):
    if _log_file:
        ts = time.strftime("%H:%M:%S")
        line = f"[{ts}] {msg}"
        _log_file.write(line + "\n")
        _log_file.flush()

# ---------------------------------------------------------------------------
# Cancelamento via ESC
# ---------------------------------------------------------------------------
_cancel = False

def _on_esc():
    global _cancel
    _cancel = True

keyboard.on_press_key("esc", lambda _: _on_esc())

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

def _resource_path(relative: str) -> str:
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, relative)


def _config_path() -> str:
    if getattr(sys, "frozen", False):
        base = os.path.dirname(sys.executable)
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, "autocraft_config.json")


def _save_config(data: dict):
    with open(_config_path(), "w") as f:
        json.dump(data, f, indent=2)


def _load_config() -> dict:
    path = _config_path()
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return {}


# ---------------------------------------------------------------------------
# Image recognition (grayscale)
# ---------------------------------------------------------------------------

def _grab_screen_gray():
    return cv2.cvtColor(np.array(ImageGrab.grab()), cv2.COLOR_RGB2GRAY)


def find_image(image_path: str, confidence: float = 0.7):
    """Localiza UMA ocorrência. Retorna (x,y) ou None."""
    name = os.path.basename(image_path)
    template = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    if template is None:
        _log(f"find_image({name}): template NULO, arquivo nao existe ou invalido")
        return None
    screen = _grab_screen_gray()
    result = cv2.matchTemplate(screen, template, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, max_loc = cv2.minMaxLoc(result)
    _log(f"find_image({name}): max_val={max_val:.3f} threshold={confidence} loc={max_loc}")
    if max_val < confidence:
        _log(f"find_image({name}): NAO encontrado")
        return None
    h, w = template.shape[:2]
    pos = (max_loc[0] + w // 2, max_loc[1] + h // 2)
    _log(f"find_image({name}): ENCONTRADO em {pos}")
    return pos


def find_all_images(image_path: str, confidence: float = 0.6, min_distance: int = 40,
                    region=None):
    """Localiza TODAS as ocorrências. region=(x1,y1,x2,y2) limita a busca."""
    name = os.path.basename(image_path)
    template = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    if template is None:
        _log(f"find_all({name}): template NULO")
        return []
    screen = _grab_screen_gray()
    if region:
        rx1, ry1, rx2, ry2 = region
        crop = screen[ry1:ry2, rx1:rx2]
        _log(f"find_all({name}): buscando em regiao ({rx1},{ry1})-({rx2},{ry2})")
    else:
        crop = screen
        rx1, ry1 = 0, 0
    result = cv2.matchTemplate(crop, template, cv2.TM_CCOEFF_NORMED)
    h, w = template.shape[:2]
    _log(f"find_all({name}): template {w}x{h}, area {crop.shape[1]}x{crop.shape[0]}")
    locations = []
    rc = result.copy()
    while True:
        _, mv, _, ml = cv2.minMaxLoc(rc)
        if mv < confidence:
            break
        cx, cy = ml[0] + w // 2 + rx1, ml[1] + h // 2 + ry1
        if not any(abs(cx - ex) < min_distance and abs(cy - ey) < min_distance for ex, ey in locations):
            locations.append((cx, cy))
        rc[max(ml[1], 0):min(ml[1]+h, rc.shape[0]), max(ml[0], 0):min(ml[0]+w, rc.shape[1])] = 0
    _log(f"find_all({name}): {len(locations)} encontrados -> {locations}")
    return locations


# ---------------------------------------------------------------------------
# Grid
# ---------------------------------------------------------------------------

def _generate_grid(config: dict) -> list:
    """Gera posições em ordem vertical: col1 cima→baixo, col2 cima→baixo, etc."""
    x0, y0 = config["top_left_x"], config["top_left_y"]
    cw, ch = config["cell_w"], config["cell_h"]
    _log(f"grid: origin=({x0},{y0}) cell={cw}x{ch} cols={config['cols']} rows={config['rows']}")
    positions = []
    for col in range(config["cols"]):
        for row in range(config["rows"]):
            positions.append((int(x0 + col * cw), int(y0 + row * ch)))
    _log(f"grid: {len(positions)} posicoes geradas")
    _log(f"grid: primeiras 5 = {positions[:5]}")
    _log(f"grid: ultimas 5 = {positions[-5:]}")
    return positions


def _is_red_at(screen_hsv, x, y, sample=20) -> bool:
    """Checa se a posição (x,y) tem pixels vermelhos suficientes via HSV."""
    h, w = screen_hsv.shape[:2]
    x1 = max(0, x - sample)
    y1 = max(0, y - sample)
    x2 = min(w, x + sample)
    y2 = min(h, y + sample)
    crop = screen_hsv[y1:y2, x1:x2]

    # Vermelho em HSV: H < 10 ou H > 170, S > 80, V > 80
    mask_low = cv2.inRange(crop, np.array([0, 80, 80]), np.array([10, 255, 255]))
    mask_high = cv2.inRange(crop, np.array([170, 80, 80]), np.array([180, 255, 255]))
    mask = mask_low | mask_high

    total_pixels = crop.shape[0] * crop.shape[1]
    red_pixels = cv2.countNonZero(mask)
    ratio = red_pixels / total_pixels if total_pixels > 0 else 0
    return ratio > 0.08  # 8% de pixels vermelhos = mapa vermelho


def _find_non_red_positions(config: dict, grid: list) -> list:
    """Retorna posições da grid que NAO são mapas vermelhos (detecção por cor)."""
    _log("--- _find_non_red_positions (HSV) ---")
    screen = np.array(ImageGrab.grab())
    screen_bgr = cv2.cvtColor(screen, cv2.COLOR_RGB2BGR)
    screen_hsv = cv2.cvtColor(screen_bgr, cv2.COLOR_BGR2HSV)

    non_red = []
    red_count = 0
    for gx, gy in grid:
        if _is_red_at(screen_hsv, gx, gy):
            red_count += 1
            _log(f"  ({gx},{gy}): VERMELHO")
        else:
            non_red.append((gx, gy))
            _log(f"  ({gx},{gy}): cinza")

    _log(f"  resultado: {red_count} vermelhos, {len(non_red)} cinzas")
    return non_red


# ---------------------------------------------------------------------------
# Craft logic
# ---------------------------------------------------------------------------

CLICK_DELAY = 0.18


def _pick_alchemy() -> bool:
    """RIGHT-click na alchemy pra pegar. Retorna True se encontrou."""
    _log("--- _pick_alchemy ---")
    alchemy_img = os.path.join(_resource_path("image"), "alchemy.png")
    pos = find_image(alchemy_img, confidence=0.6)
    if pos is None:
        _log("_pick_alchemy: FALHOU - alchemy nao encontrada")
        return False
    _log(f"_pick_alchemy: RIGHT-click em ({pos[0]}, {pos[1]})")
    pyautogui.click(pos[0], pos[1], button="right")
    time.sleep(0.5)
    return True


def _click_maps(positions: list, status_cb=None, label="") -> int:
    """LEFT-click em cada posição (shift já deve estar pressionado)."""
    global _cancel
    clicked = 0
    total = len(positions)
    for mx, my in positions:
        if _cancel:
            _log(f"  CANCELADO em {clicked}/{total}")
            break
        if status_cb:
            status_cb(f"{label} {clicked+1}/{total}")
        _log(f"  LEFT-click #{clicked+1}/{total} em ({mx}, {my})")
        pyautogui.click(mx, my, button="left")
        clicked += 1
        time.sleep(CLICK_DELAY)
    return clicked


def do_loop(status_callback=None, stats_callback=None) -> str:
    """
    Loop alternado:
    Ciclo impar — Alchemy: detecta cinzas → right-click alchemy → shift+left nos cinzas
    Ciclo par   — Scouring: detecta cinzas → right-click alchemy → shift+alt+left nos cinzas
    Repete até todos vermelhos.
    """
    _log("========== do_loop START ==========")
    config = _load_config()
    _log(f"config: {json.dumps(config, indent=2)}")
    if "cell_w" not in config:
        _log("ERRO: grid nao calibrada")
        return "Calibre a grid primeiro!"

    global _cancel
    _cancel = False
    cycle = 0
    grid = _generate_grid(config)
    total_maps = len(grid)
    _log(f"grid total: {total_maps} posicoes")

    while not _cancel:
        cycle += 1
        is_scouring = (cycle % 2 == 0)
        phase = "Scouring" if is_scouring else "Alchemy"
        _log(f"\n====== CICLO {cycle} — {phase} ======")

        # --- Detectar cinzas (sem shift, tela limpa) ---
        _log(f"Detectando cinzas (HSV)...")
        non_red = _find_non_red_positions(config, grid)
        red_count = total_maps - len(non_red)

        if stats_callback:
            stats_callback(cycle, total_maps, red_count, len(non_red))

        if not non_red:
            msg = f"Completo! {total_maps} mapas vermelhos em {cycle - 1} ciclos"
            _log(msg)
            return msg

        if status_callback:
            status_callback(f"Ciclo {cycle} — {phase} em {len(non_red)}...")

        # --- Pegar alchemy ---
        if not _pick_alchemy():
            return "Alchemy nao encontrada"

        # --- Aplicar ---
        pyautogui.keyDown("shift")
        if is_scouring:
            pyautogui.keyDown("alt")
        _log(f"SHIFT DOWN | ALT {'ON' if is_scouring else 'OFF'}")

        _click_maps(non_red, status_cb=status_callback, label=phase)

        if is_scouring:
            pyautogui.keyUp("alt")
        pyautogui.keyUp("shift")
        _log(f"SHIFT UP | {phase} done — {len(non_red)} clicados")

        if _cancel:
            return f"Cancelado no ciclo {cycle}"

        time.sleep(0.5)
        _log(f"====== FIM CICLO {cycle} ======")

    _log(f"Loop cancelado no ciclo {cycle}")
    return f"Cancelado no ciclo {cycle}"


# ---------------------------------------------------------------------------
# GUI — Chieftain Theme
# ---------------------------------------------------------------------------

# Palette: dark volcanic + fire + tribal gold
BG_DARK = "#0d0a08"
BG_PANEL = "#171210"
BG_SECTION = "#1e1814"
FG_TITLE = "#e8c87a"
FG_MAIN = "#d4c8a0"
FG_SECONDARY = "#a89878"
FG_DIM = "#5e5548"
BORDER_COLOR = "#2e2218"
BORDER_FIRE = "#4a2a10"

# Accent colors
FIRE_ORANGE = "#d4641e"
FIRE_GLOW = "#f08030"
EMBER_RED = "#a03018"
GOLD = "#c8a84e"
GOLD_DIM = "#8a7a40"
ASH_GREEN = "#4a7a4a"
ASH_GREEN_H = "#5a9a5a"
RITUAL_PURPLE = "#6a4eb0"
RITUAL_PURPLE_H = "#7e60c8"

# Phase colors
PHASE_ALCHEMY = "#d4941e"
PHASE_SCOURING = "#5888c0"
PHASE_IDLE = "#5e5548"

STATUS_OK = "#5a9e5a"
STATUS_ERR = "#c75050"

BTN_W = 240
BTN_H = 38
BTN_H_BIG = 50

CAPTURE_STEPS = [
    ("alchemy", "F2 na Orb of Alchemy"),
    ("t16_gray", "F2 num mapa T16 CINZA (normal)"),
    ("t16_red", "F2 num mapa T16 VERMELHO (craftado)"),
]

GRID_STEPS = [
    ("top_left", "F2 no PRIMEIRO mapa (superior esquerdo)"),
    ("second_col", "F2 no mapa ao LADO (segunda coluna, mesma linha)"),
    ("last_map", "F2 no ULTIMO mapa (inferior direito)"),
]


class HoverButton(tk.Canvas):
    def __init__(self, parent, text, color, hover_color, command,
                 width=BTN_W, height=BTN_H, font_size=10, parent_bg=BG_PANEL, **kw):
        super().__init__(parent, width=width, height=height, bg=parent_bg,
                         highlightthickness=0, cursor="hand2", **kw)
        self._text, self._color, self._hover_color = text, color, hover_color
        self._command, self._disabled = command, False
        self._bw, self._bh, self._font_size, self._pbg = width, height, font_size, parent_bg
        self._draw(color)
        self.bind("<Enter>", lambda e: not self._disabled and self._draw(self._hover_color))
        self.bind("<Leave>", lambda e: self._draw(self._color if not self._disabled else "#2a2220"))
        self.bind("<ButtonRelease-1>", lambda e: not self._disabled and self._command and self._command())

    def _draw(self, fill):
        self.delete("all")
        w, h, r = self._bw, self._bh, 6
        # Border glow
        for (ax, ay, bx, by, s) in [
            (0, 0, r*2, r*2, 90), (w-r*2, 0, w, r*2, 0),
            (0, h-r*2, r*2, h, 180), (w-r*2, h-r*2, w, h, 270),
        ]:
            self.create_arc(ax, ay, bx, by, start=s, extent=90, fill=fill, outline="")
        self.create_rectangle(r, 0, w-r, h, fill=fill, outline="")
        self.create_rectangle(0, r, w, h-r, fill=fill, outline="")
        fg = "#120e0c" if not self._disabled else "#4a4440"
        self.create_text(w // 2, h // 2, text=self._text,
                         fill=fg, font=("Segoe UI", self._font_size, "bold"))

    def set_disabled(self, d):
        self._disabled = d
        self._draw("#2a2220" if d else self._color)
        self.config(cursor="" if d else "hand2")


def _tribal_divider(parent, bg, width=240):
    """Draws a tribal-style divider with diamond center."""
    c = tk.Canvas(parent, width=width, height=12, bg=bg, highlightthickness=0)
    mid = width // 2
    y = 6
    c.create_line(8, y, mid - 12, y, fill=BORDER_FIRE, width=1)
    c.create_line(mid + 12, y, width - 8, y, fill=BORDER_FIRE, width=1)
    # diamond
    c.create_polygon(mid, y-4, mid+5, y, mid, y+4, mid-5, y,
                     fill=GOLD_DIM, outline="")
    return c


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("PoE - Auto Map Craft")
        self.resizable(False, False)
        self.attributes("-topmost", True)
        self.configure(bg=BG_DARK)
        self._cycle_count = 0
        self._maps_crafted = 0

        pad = 14

        # ── Header ──
        header = tk.Frame(self, bg=BG_DARK)
        header.pack(fill="x", padx=pad, pady=(pad, 0))

        title_frame = tk.Frame(header, bg=BG_DARK)
        title_frame.pack(anchor="w")

        tk.Label(title_frame, text="AUTO MAP CRAFT",
                 font=("Segoe UI", 15, "bold"),
                 fg=FG_TITLE, bg=BG_DARK).pack(side="left")

        tk.Label(header, text="Path of Exile",
                 font=("Segoe UI", 8), fg=FG_DIM, bg=BG_DARK).pack(anchor="w", pady=(2, 0))

        # ── Phase indicator panel ──
        phase_panel = tk.Frame(self, bg=BG_SECTION, highlightthickness=1,
                               highlightbackground=BORDER_FIRE)
        phase_panel.pack(fill="x", padx=pad, pady=(10, 0))

        phase_inner = tk.Frame(phase_panel, bg=BG_SECTION)
        phase_inner.pack(fill="x", padx=12, pady=10)

        # Phase label
        pf_top = tk.Frame(phase_inner, bg=BG_SECTION)
        pf_top.pack(fill="x")

        self.phase_label = tk.Label(pf_top, text="AGUARDANDO",
                                     font=("Segoe UI", 11, "bold"),
                                     fg=PHASE_IDLE, bg=BG_SECTION)
        self.phase_label.pack(side="left")

        self.cycle_label = tk.Label(pf_top, text="",
                                     font=("Segoe UI", 9),
                                     fg=FG_DIM, bg=BG_SECTION)
        self.cycle_label.pack(side="right")

        # Progress detail
        self.phase_detail = tk.Label(phase_inner, text="Pronto para iniciar",
                                      font=("Segoe UI", 9),
                                      fg=FG_SECONDARY, bg=BG_SECTION, anchor="w")
        self.phase_detail.pack(fill="x", pady=(4, 0))

        # Stats row
        stats = tk.Frame(phase_inner, bg=BG_SECTION)
        stats.pack(fill="x", pady=(8, 0))

        self.stat_maps = tk.Label(stats, text="Maps: --",
                                   font=("Segoe UI", 8),
                                   fg=FG_DIM, bg=BG_SECTION)
        self.stat_maps.pack(side="left")

        self.stat_red = tk.Label(stats, text="Vermelhos: --",
                                  font=("Segoe UI", 8),
                                  fg=FG_DIM, bg=BG_SECTION)
        self.stat_red.pack(side="left", padx=(16, 0))

        self.stat_gray = tk.Label(stats, text="Cinzas: --",
                                   font=("Segoe UI", 8),
                                   fg=FG_DIM, bg=BG_SECTION)
        self.stat_gray.pack(side="left", padx=(16, 0))

        # ── Main panel ──
        panel = tk.Frame(self, bg=BG_PANEL, highlightthickness=1,
                         highlightbackground=BORDER_COLOR)
        panel.pack(fill="x", padx=pad, pady=(8, 0))
        inner = tk.Frame(panel, bg=BG_PANEL)
        inner.pack(padx=14, pady=12)

        # -- Craft button (primary action) --
        self.btn_loop = HoverButton(inner, "INICIAR CRAFT",
                                     FIRE_ORANGE, FIRE_GLOW, self._run_loop,
                                     height=BTN_H_BIG, font_size=13)
        self.btn_loop.pack(pady=(0, 4))

        tk.Label(inner, text="ESC para cancelar",
                 font=("Segoe UI", 8), fg=FG_DIM, bg=BG_PANEL).pack()

        _tribal_divider(inner, BG_PANEL).pack(pady=(10, 8))

        # -- Setup section --
        tk.Label(inner, text="SETUP", font=("Segoe UI", 8, "bold"),
                 fg=GOLD_DIM, bg=BG_PANEL).pack(anchor="w", padx=4, pady=(0, 6))

        row1 = tk.Frame(inner, bg=BG_PANEL)
        row1.pack(fill="x", pady=(0, 6))

        self.btn_capture = HoverButton(row1, "Capturar Templates",
                                        RITUAL_PURPLE, RITUAL_PURPLE_H,
                                        self._start_capture, width=BTN_W)
        self.btn_capture.pack()

        row2 = tk.Frame(inner, bg=BG_PANEL)
        row2.pack(fill="x", pady=(0, 6))

        half_w = (BTN_W - 8) // 2

        self.btn_grid = HoverButton(row2, "Calibrar Grid",
                                     ASH_GREEN, ASH_GREEN_H,
                                     self._start_grid, width=half_w)
        self.btn_grid.pack(side="left")

        tk.Frame(row2, width=8, bg=BG_PANEL).pack(side="left")

        self.btn_test = HoverButton(row2, "Testar Grid",
                                     ASH_GREEN, ASH_GREEN_H,
                                     self._test_grid, width=half_w)
        self.btn_test.pack(side="left")

        # Grid info
        config = _load_config()
        gt = "Grid nao calibrada"
        if "cols" in config:
            gt = f"Grid {config['cols']}x{config['rows']}  |  celula {config['cell_w']}px"
        self.grid_label = tk.Label(inner, text=gt, font=("Segoe UI", 8),
                                   fg=FG_DIM, bg=BG_PANEL)
        self.grid_label.pack(pady=(4, 0))

        # ── Status bar ──
        sbar = tk.Frame(self, bg=BG_DARK)
        sbar.pack(fill="x", padx=pad, pady=(8, pad))

        self.status_dot = tk.Canvas(sbar, width=8, height=8, bg=BG_DARK, highlightthickness=0)
        self.status_dot.create_oval(0, 0, 8, 8, fill=STATUS_OK, outline="")
        self.status_dot.pack(side="left", pady=(1, 0))

        self.status = tk.Label(sbar, text="Pronto", font=("Segoe UI", 8),
                               fg=FG_DIM, bg=BG_DARK, anchor="w")
        self.status.pack(side="left", padx=(6, 0))

        self._all_btns = [self.btn_loop, self.btn_grid, self.btn_test, self.btn_capture]

    # --- UI helpers ---
    def _set_all(self, d):
        for b in self._all_btns:
            b.set_disabled(d)

    def _dot(self, c):
        self.status_dot.delete("all")
        self.status_dot.create_oval(0, 0, 8, 8, fill=c, outline="")

    def _set_status(self, msg, color=None):
        self.status.config(text=msg, fg=color or FG_DIM)
        self._dot(color or STATUS_OK)

    def _set_result(self, msg, err=False):
        c = STATUS_ERR if err else STATUS_OK
        self.status.config(text=msg, fg=c)
        self._dot(c)

    def _set_phase(self, phase, detail="", cycle=0, total=0, red=0, gray=0):
        colors = {"ALCHEMY": PHASE_ALCHEMY, "SCOURING": PHASE_SCOURING,
                  "DETECTANDO": GOLD_DIM, "COMPLETO": STATUS_OK,
                  "AGUARDANDO": PHASE_IDLE, "ERRO": STATUS_ERR}
        c = colors.get(phase, PHASE_IDLE)
        self.phase_label.config(text=phase, fg=c)
        if detail:
            self.phase_detail.config(text=detail, fg=FG_SECONDARY)
        if cycle > 0:
            self.cycle_label.config(text=f"Ciclo {cycle}", fg=FG_DIM)
        if total > 0:
            self.stat_maps.config(text=f"Maps: {total}")
            self.stat_red.config(text=f"Vermelhos: {red}", fg=FIRE_ORANGE if red > 0 else FG_DIM)
            self.stat_gray.config(text=f"Cinzas: {gray}", fg=PHASE_SCOURING if gray > 0 else FG_DIM)

    # --- Loop ---
    def _run_loop(self):
        self._set_all(True)
        self._cycle_count = 0

        def cb(msg):
            # Parse info from callback message
            if "Alchemy" in msg:
                phase = "ALCHEMY"
            elif "Scouring" in msg:
                phase = "SCOURING"
            else:
                phase = "DETECTANDO"

            # Extract cycle number
            cycle = self._cycle_count

            self.after(0, lambda: self._set_phase(phase, msg, cycle=cycle))
            self.after(0, lambda: self._set_status(msg, PHASE_ALCHEMY if "Alchemy" in msg else PHASE_SCOURING))

        def stats_cb(cycle, total, red, gray):
            self._cycle_count = cycle
            self.after(0, lambda: self._set_phase("DETECTANDO",
                       f"Analisando mapas...", cycle=cycle, total=total, red=red, gray=gray))

        def task():
            try:
                r = do_loop(status_callback=cb, stats_callback=stats_cb)
                err = "nao encontrada" in r or "Cancelado" in r
                if not err:
                    self.after(0, lambda: self._set_phase("COMPLETO", r,
                               cycle=self._cycle_count))
                else:
                    self.after(0, lambda: self._set_phase("AGUARDANDO", r))
                self.after(0, lambda: self._set_result(r, err=err))
            except Exception as e:
                self.after(0, lambda: self._set_phase("ERRO", str(e)))
                self.after(0, lambda: self._set_result(str(e), err=True))
            finally:
                self.after(0, lambda: self._set_all(False))

        threading.Thread(target=task, daemon=True).start()

    # --- Grid Calibration ---
    def _start_grid(self):
        self._grid_pts = {}
        self._grid_i = 0
        self._do_grid_step()

    def _do_grid_step(self):
        if self._grid_i >= len(GRID_STEPS):
            self._finish_grid()
            return
        name, msg = GRID_STEPS[self._grid_i]
        self._set_status(f"[{self._grid_i+1}/3] {msg}", ASH_GREEN)

        def wait():
            keyboard.wait("f2")
            x, y = pyautogui.position()
            self._grid_pts[name] = (x, y)
            self._grid_i += 1
            self.after(0, lambda: self._set_status(f"Salvo: ({x},{y})", STATUS_OK))
            time.sleep(0.3)
            self.after(0, self._do_grid_step)

        threading.Thread(target=wait, daemon=True).start()

    def _finish_grid(self):
        p = self._grid_pts
        x1, y1 = p["top_left"]
        x2, _ = p["second_col"]
        x3, y3 = p["last_map"]

        cw = abs(x2 - x1)
        ch = cw
        cols = round(abs(x3 - x1) / cw) + 1
        rows = round(abs(y3 - y1) / ch) + 1

        config = _load_config()
        config.update({"top_left_x": x1, "top_left_y": y1,
                       "cell_w": cw, "cell_h": ch, "cols": cols, "rows": rows})
        _save_config(config)

        self.grid_label.config(text=f"Grid {cols}x{rows}  |  celula {cw}px")
        self._set_result(f"Grid: {cols}x{rows} = {cols*rows} slots")

    # --- Test Grid ---
    def _test_grid(self):
        config = _load_config()
        if "cell_w" not in config:
            self._set_result("Calibre a grid primeiro!", err=True)
            return
        self._set_all(True)

        def task():
            try:
                global _cancel
                _cancel = False
                positions = _generate_grid(config)
                total = len(positions)
                for i, (x, y) in enumerate(positions):
                    if _cancel:
                        self.after(0, lambda: self._set_result(f"Teste cancelado em {i}/{total}"))
                        return
                    self.after(0, lambda i=i: self._set_status(
                        f"Testando {i+1}/{total}...", ASH_GREEN))
                    pyautogui.moveTo(x, y, duration=0.05)
                    time.sleep(0.15)
                self.after(0, lambda: self._set_result(f"Grid OK: {total} posicoes"))
            except Exception as e:
                self.after(0, lambda: self._set_result(str(e), err=True))
            finally:
                self.after(0, lambda: self._set_all(False))

        threading.Thread(target=task, daemon=True).start()

    # --- Capture Templates ---
    def _start_capture(self):
        self._cap_i = 0
        self._do_capture_step()

    def _do_capture_step(self):
        total = len(CAPTURE_STEPS)
        if self._cap_i >= total:
            self._set_result("Templates capturados!")
            return
        name, msg = CAPTURE_STEPS[self._cap_i]
        self._set_status(f"[{self._cap_i+1}/{total}] {msg}", RITUAL_PURPLE)

        def wait():
            keyboard.wait("f2")
            x, y = pyautogui.position()
            size = 30
            shot = cv2.cvtColor(np.array(ImageGrab.grab()), cv2.COLOR_RGB2BGR)
            crop = shot[max(y-size,0):min(y+size,shot.shape[0]),
                        max(x-size,0):min(x+size,shot.shape[1])]
            path = os.path.join(_resource_path("image"), f"{name}.png")
            cv2.imwrite(path, crop)
            dim = f"{crop.shape[1]}x{crop.shape[0]}"
            self._cap_i += 1
            self.after(0, lambda: self._set_result(f"{name}.png ({dim})"))
            time.sleep(0.5)
            self.after(0, self._do_capture_step)

        threading.Thread(target=wait, daemon=True).start()


if __name__ == "__main__":
    _log_init()
    app = App()
    app.mainloop()
