import json
import os
import queue
import subprocess
import sys
import threading
import random
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from tkinter.scrolledtext import ScrolledText


PROJECT_ROOT = Path(__file__).resolve().parent
MAIN_SCRIPT = PROJECT_ROOT / "main.py"
if getattr(sys, 'frozen', False):
    CONFIG_PATH = Path(sys.executable).resolve().parent / ".aegis_ui_config.json"
else:
    CONFIG_PATH = PROJECT_ROOT / ".aegis_ui_config.json"


class NeonProgress(tk.Canvas):
    def __init__(self, master, **kwargs):
        super().__init__(master, bg="#070A11", highlightthickness=1, highlightbackground="#1A2639", **kwargs)
        self.running = False
        self.offset = -100
        self.colors = ["#00F0FF", "#BC13FE", "#FF003C", "#39FF14"]
        self.c_idx = 0
        self.bind("<Configure>", lambda e: self._draw_idle(), add="+")

    def start(self, interval=10):
        if self.running: return
        self.running = True
        self.offset = -100
        self._animate()

    def stop(self):
        self.running = False
        self.delete("all")
        self._draw_idle()

    def _draw_idle(self):
        if not self.running:
            self.delete("all")
            w = self.winfo_width()
            h = self.winfo_height()
            self.create_text(w/2, h/2, text="[ SYSTEM IDLE ]", fill="#567189", font=("Consolas", 10, "bold"))

    def _animate(self):
        if not self.running: return
        self.delete("all")
        w = self.winfo_width() or 200
        h = self.winfo_height() or 24
        
        self.offset += 8
        if self.offset > w + 100:
            self.offset = -100
            self.c_idx = (self.c_idx + 1) % len(self.colors)
            
        for i in range(0, w, 10):
            self.create_line(i, 0, i, h, fill="#1A2639")
            
        x1, x2 = max(0, self.offset), min(w, self.offset + 100)
        if x2 > x1:
            self.create_rectangle(x1, 0, x2, h, fill=self.colors[self.c_idx], outline="")
            
        glitch = "".join(random.choices("01*X#%", k=4))
        self.create_text(w/2, h/2, text=f"// AUDIT RUNNING {glitch} //", fill="#FFFFFF", font=("Consolas", 10, "bold"))
        self.after(30, self._animate)


DEFAULT_CONFIG = {
    "target": "",
    "ai_provider": "auto",
    "ai_provider_order": "mistral,gemini",
    "ai_enable_fallback": True,
    "mistral_models": "mistral-small-latest,mistral-large-latest",
    "gemini_models": "gemini-2.5-flash-lite,gemini-2.0-flash-lite-001,gemini-2.0-flash-lite",
    "mistral_api_key": os.getenv("MISTRAL_API_KEY", ""),
    "gemini_api_key": os.getenv("GEMINI_API_KEY", ""),
}


class AegisUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Aegis Security Console")
        self.geometry("1220x760")
        self.minsize(980, 620)

        self.process = None
        self.reader_thread = None
        self.output_queue = queue.Queue()
        self.polling_after_id = None

        self.colors = {
            "bg": "#030508",
            "panel": "#0A0D14",
            "card": "#101520",
            "accent": "#00F0FF",
            "accent_soft": "#00A3FF",
            "text": "#E2F1FF",
            "muted": "#567189",
            "danger": "#FF003C",
            "ok": "#39FF14",
            "border": "#1A2639",
            "input": "#070A11"
        }

        self._init_style()
        self._init_bg_animation()
        self._init_vars()
        self._build_layout()
        self._load_config(initial=True)
        self._update_provider_hint()

        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _init_bg_animation(self):
        self.bg_canvas = tk.Canvas(self, bg="#020306", highlightthickness=0)
        self.bg_canvas.place(x=0, y=0, relwidth=1, relheight=1)

        self.particles = []
        self.lines = []
        for i in range(30):
            y = i * 40
            line_id = self.bg_canvas.create_line(0, y, 2000, y, fill="#0A1526", width=1)
            self.lines.append({"id": line_id, "y": y})

        for _ in range(120):
            x, y = random.randint(0, 2000), random.randint(0, 1000)
            p_id = self.bg_canvas.create_oval(x, y, x+1, y+1, fill="#1A2639", outline="")
            self.particles.append({"id": p_id, "sx": -0.1, "sy": 0.05, "type": "star"})

        for _ in range(60):
            x, y = random.randint(0, 2000), random.randint(0, 1000)
            color = random.choice(["#00F0FF", "#BC13FE", "#567189"])
            p_id = self.bg_canvas.create_oval(x, y, x+2, y+2, fill=color, outline="")
            self.particles.append({"id": p_id, "sx": -0.4, "sy": 0.2, "type": "star"})

        for _ in range(10):
            x, y = random.randint(0, 2000), random.randint(0, 1000)
            p_id = self.bg_canvas.create_line(x, y, x+15, y-15, fill="#FFFFFF", width=2)
            self.particles.append({"id": p_id, "sx": -4.0, "sy": 4.0, "type": "comet"})

        self.bind("<Motion>", self._on_mouse_move)
        self._animate_particles()

    def _on_mouse_move(self, event):
        x = event.x_root - self.winfo_rootx()
        y = event.y_root - self.winfo_rooty()
        size = random.uniform(2.0, 5.0)
        color = random.choice([self.colors["accent"], "#BC13FE", "#FFFFFF", "#39FF14"])
        p_id = self.bg_canvas.create_oval(x, y, x+size, y+size, fill=color, outline="")
        self.particles.append({
            "id": p_id, 
            "sx": random.uniform(-1.0, 1.0), 
            "sy": random.uniform(1.0, 3.0), 
            "life": 15
        })

    def _animate_particles(self):
        width = self.winfo_width() or 1220
        height = self.winfo_height() or 760
        
        for l in self.lines:
            self.bg_canvas.move(l["id"], 0, 0.5)
            pos = self.bg_canvas.coords(l["id"])
            if pos and pos[1] > height:
                self.bg_canvas.move(l["id"], 0, -height - 40)

        active_particles = []
        for p in self.particles:
            self.bg_canvas.move(p["id"], p["sx"], p["sy"])
            
            if "life" in p:
                p["life"] -= 1
                if p["life"] <= 0:
                    self.bg_canvas.delete(p["id"])
                    continue
            else:
                pos = self.bg_canvas.coords(p["id"])
                if not pos: continue
                if len(pos) == 4:
                    x1, y1, x2, y2 = pos
                    if x2 < 0: self.bg_canvas.move(p["id"], width, 0)
                    elif x1 > width: self.bg_canvas.move(p["id"], -width, 0)
                    if y2 < 0: self.bg_canvas.move(p["id"], 0, height)
                    elif y1 > height: self.bg_canvas.move(p["id"], 0, -height)
                
            active_particles.append(p)

        self.particles = active_particles
        self.after(35, self._animate_particles)

    def _init_style(self):
        self.configure(bg=self.colors["bg"], cursor="star")
        style = ttk.Style(self)
        style.theme_use("clam")

        style.configure("App.TFrame", background=self.colors["bg"])
        style.configure("Header.TFrame", background=self.colors["bg"])
        style.configure("Card.TFrame", background=self.colors["card"])

        style.configure(
            "Title.TLabel",
            background=self.colors["bg"],
            foreground=self.colors["text"],
            font=("Consolas", 26, "bold"),
        )
        style.configure(
            "Subtitle.TLabel",
            background=self.colors["bg"],
            foreground=self.colors["muted"],
            font=("Consolas", 11),
        )
        style.configure(
            "Card.TLabel",
            background=self.colors["card"],
            foreground=self.colors["text"],
            font=("Consolas", 11),
        )
        style.configure(
            "Hint.TLabel",
            background=self.colors["card"],
            foreground=self.colors["muted"],
            font=("Consolas", 10),
        )
        style.configure(
            "Status.TLabel",
            background=self.colors["bg"],
            foreground=self.colors["muted"],
            font=("Consolas", 10),
        )

        style.configure(
            "Primary.TButton",
            background=self.colors["input"],
            foreground=self.colors["accent"],
            bordercolor=self.colors["accent"],
            lightcolor=self.colors["accent"],
            darkcolor=self.colors["accent"],
            borderwidth=1,
            focuscolor=self.colors["input"],
            padding=(20, 10),
            font=("Consolas", 12, "bold"),
        )
        style.map(
            "Primary.TButton",
            background=[("active", self.colors["accent"]), ("disabled", "#1A2639")],
            foreground=[("active", "#000000"), ("disabled", "#567189")],
        )

        style.configure(
            "Secondary.TButton",
            background=self.colors["input"],
            foreground=self.colors["text"],
            bordercolor=self.colors["muted"],
            lightcolor=self.colors["muted"],
            darkcolor=self.colors["muted"],
            borderwidth=1,
            focuscolor=self.colors["input"],
            padding=(16, 10),
            font=("Consolas", 11),
        )
        style.map(
            "Secondary.TButton",
            background=[("active", self.colors["border"]), ("disabled", "#070A11")],
            foreground=[("active", self.colors["accent"]), ("disabled", "#567189")],
        )

        style.configure(
            "Danger.TButton",
            background=self.colors["input"],
            foreground=self.colors["danger"],
            bordercolor=self.colors["danger"],
            lightcolor=self.colors["danger"],
            darkcolor=self.colors["danger"],
            borderwidth=1,
            focuscolor=self.colors["input"],
            padding=(16, 10),
            font=("Consolas", 11, "bold"),
        )
        style.map(
            "Danger.TButton",
            background=[("active", self.colors["danger"]), ("disabled", "#330011")],
            foreground=[("active", "#FFFFFF")]
        )

        style.configure(
            "TNotebook",
            background=self.colors["bg"],
            borderwidth=0,
            tabmargins=(0, 10, 0, 0),
        )
        style.configure(
            "TNotebook.Tab",
            background=self.colors["bg"],
            foreground=self.colors["muted"],
            padding=(20, 12),
            font=("Consolas", 12, "bold"),
            borderwidth=0,
        )
        style.map(
            "TNotebook.Tab",
            background=[("selected", self.colors["bg"]), ("active", self.colors["bg"])],
            foreground=[("selected", self.colors["accent"]), ("active", self.colors["accent_soft"])],
        )

        style.configure(
            "Card.TLabelframe",
            background=self.colors["card"],
            bordercolor=self.colors["border"],
            lightcolor=self.colors["border"],
            darkcolor=self.colors["border"],
            borderwidth=1,
        )
        style.configure(
            "Card.TLabelframe.Label",
            background=self.colors["card"],
            foreground=self.colors["accent"],
            font=("Consolas", 12, "bold"),
        )

        style.configure(
            "Card.TEntry",
            fieldbackground=self.colors["input"],
            foreground=self.colors["text"],
            insertcolor=self.colors["text"],
            bordercolor=self.colors["border"],
            lightcolor=self.colors["border"],
            darkcolor=self.colors["border"],
            padding=10,
            font=("Consolas", 11)
        )

        style.configure(
            "Card.TRadiobutton",
            background=self.colors["card"],
            foreground=self.colors["text"],
            font=("Consolas", 11),
            indicatorsize=12,
        )
        style.map("Card.TRadiobutton", background=[("active", self.colors["card"])])

        style.configure(
            "Card.TCheckbutton",
            background=self.colors["card"],
            foreground=self.colors["text"],
            font=("Consolas", 11),
            indicatorsize=12,
        )
        style.map("Card.TCheckbutton", background=[("active", self.colors["card"])])

        style.configure(
            "Card.Horizontal.TProgressbar",
            troughcolor=self.colors["input"],
            background=self.colors["accent"],
            bordercolor=self.colors["input"],
            lightcolor=self.colors["accent"],
            darkcolor=self.colors["accent"],
        )

    def _init_vars(self):
        self.target_var = tk.StringVar(value=DEFAULT_CONFIG["target"])
        self.provider_var = tk.StringVar(value=DEFAULT_CONFIG["ai_provider"])
        self.provider_order_var = tk.StringVar(value=DEFAULT_CONFIG["ai_provider_order"])
        self.fallback_var = tk.BooleanVar(value=DEFAULT_CONFIG["ai_enable_fallback"])
        self.mistral_models_var = tk.StringVar(value=DEFAULT_CONFIG["mistral_models"])
        self.gemini_models_var = tk.StringVar(value=DEFAULT_CONFIG["gemini_models"])
        self.mistral_key_var = tk.StringVar(value=DEFAULT_CONFIG["mistral_api_key"])
        self.gemini_key_var = tk.StringVar(value=DEFAULT_CONFIG["gemini_api_key"])

        self.status_var = tk.StringVar(value="Idle")
        self.provider_hint_var = tk.StringVar(value="")

        self.provider_var.trace_add("write", lambda *_: self._update_provider_hint())
        self.provider_order_var.trace_add("write", lambda *_: self._update_provider_hint())
        self.fallback_var.trace_add("write", lambda *_: self._update_provider_hint())

    def _build_layout(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        header = ttk.Frame(self, style="Header.TFrame", padding=(24, 20))
        header.grid(row=0, column=0, sticky="ew")
        header.columnconfigure(0, weight=1)

        ttk.Label(header, text="Aegis Security Console", style="Title.TLabel").grid(
            row=0, column=0, sticky="w"
        )
        ttk.Label(
            header,
            text="Autonomous API audit with dual AI providers, failover, and live execution logs.",
            style="Subtitle.TLabel",
        ).grid(row=1, column=0, sticky="w", pady=(6, 0))

        notebook = ttk.Notebook(self)
        notebook.grid(row=1, column=0, sticky="nsew", padx=20, pady=(10, 20))

        def set_notebook_cursor(event):
            try:
                if notebook.identify(event.x, event.y) == "label":
                    notebook.config(cursor="hand2")
                else:
                    notebook.config(cursor="")
            except Exception:
                pass
        notebook.bind("<Motion>", set_notebook_cursor)

        self.audit_tab = ttk.Frame(notebook, style="App.TFrame", padding=6)
        self.config_tab = ttk.Frame(notebook, style="App.TFrame", padding=6)
        self.help_tab = ttk.Frame(notebook, style="App.TFrame", padding=6)

        notebook.add(self.audit_tab, text="Audit")
        notebook.add(self.config_tab, text="Configuration")
        notebook.add(self.help_tab, text="Guide")

        self._build_audit_tab()
        self._build_config_tab()
        self._build_help_tab()

    def _build_audit_tab(self):
        self.audit_tab.columnconfigure(0, weight=1)
        self.audit_tab.rowconfigure(2, weight=1)

        top_card = ttk.Frame(self.audit_tab, style="Card.TFrame", padding=14)
        top_card.grid(row=0, column=0, sticky="ew")
        top_card.columnconfigure(1, weight=1)
        top_card.columnconfigure(6, weight=1)

        ttk.Label(top_card, text="Target", style="Card.TLabel").grid(row=0, column=0, sticky="w")
        
        self.target_entry_frame = ttk.Frame(top_card, style="Card.TFrame")
        self.target_entry_frame.grid(row=0, column=1, sticky="ew", padx=(12, 24))
        self.target_entry_frame.columnconfigure(0, weight=1)

        self.target_entry = ttk.Entry(self.target_entry_frame, textvariable=self.target_var, style="Card.TEntry")
        self.target_entry.grid(row=0, column=0, sticky="ew")

        self.placeholder_label = tk.Label(
            self.target_entry_frame, 
            text="e.g. localhost", 
            fg=self.colors["muted"], 
            bg=self.colors["input"], 
            font=("Consolas", 11),
            cursor="xterm"
        )
        self.placeholder_label.place(x=12, rely=0.5, anchor="w")
        self.placeholder_label.bind("<Button-1>", lambda e: self.target_entry.focus_set())
        
        def update_placeholder(*args):
            if self.target_var.get():
                self.placeholder_label.place_forget()
            else:
                self.placeholder_label.place(x=12, rely=0.5, anchor="w")
                
        self.target_var.trace_add("write", update_placeholder)
        self.after(50, update_placeholder)

        ttk.Label(top_card, text="AI Route", style="Card.TLabel").grid(row=0, column=2, sticky="w")
        ttk.Label(top_card, textvariable=self.provider_hint_var, style="Hint.TLabel").grid(
            row=0, column=3, sticky="w", padx=(8, 16)
        )

        self.start_btn = ttk.Button(
            top_card,
            text="Start Audit",
            style="Primary.TButton",
            command=self.start_audit,
            cursor="hand2"
        )
        self.start_btn.grid(row=0, column=4, sticky="e", padx=(0, 8))

        self.stop_btn = ttk.Button(
            top_card,
            text="Stop",
            style="Danger.TButton",
            command=self.stop_audit,
            state="disabled",
            cursor="hand2"
        )
        self.stop_btn.grid(row=0, column=5, sticky="e")

        actions = ttk.Frame(self.audit_tab, style="Card.TFrame", padding=(14, 10))
        actions.grid(row=1, column=0, sticky="ew", pady=(10, 0))
        actions.columnconfigure(1, weight=1)

        ttk.Button(actions, text="Clear Console", style="Secondary.TButton", command=self.clear_output, cursor="hand2").grid(
            row=0, column=0, sticky="w"
        )
        ttk.Button(actions, text="Export Log", style="Secondary.TButton", command=self.export_output, cursor="hand2").grid(
            row=0, column=1, sticky="w", padx=(10, 0)
        )

        self.progress = NeonProgress(actions, height=24)
        self.progress.grid(row=0, column=2, sticky="ew", padx=(14, 0))
        actions.columnconfigure(2, weight=1)

        output_card = ttk.Frame(self.audit_tab, style="Card.TFrame", padding=10)
        output_card.grid(row=2, column=0, sticky="nsew", pady=(10, 0))
        output_card.columnconfigure(0, weight=1)
        output_card.rowconfigure(0, weight=1)

        self.output_text = ScrolledText(
            output_card,
            wrap="word",
            bg="#0A0A0A",
            fg=self.colors["text"],
            insertbackground=self.colors["text"],
            selectbackground="#27272A",
            relief="flat",
            borderwidth=0,
            highlightthickness=1,
            highlightbackground=self.colors["border"],
            highlightcolor=self.colors["muted"],
            font=("Consolas", 11),
            padx=16,
            pady=16,
        )
        self.output_text.grid(row=0, column=0, sticky="nsew")
        self.output_text.configure(state="disabled")

        status_bar = ttk.Frame(self.audit_tab, style="App.TFrame", padding=(2, 8, 2, 0))
        status_bar.grid(row=3, column=0, sticky="ew")
        status_bar.columnconfigure(0, weight=1)
        ttk.Label(status_bar, textvariable=self.status_var, style="Status.TLabel").grid(row=0, column=0, sticky="w")

    def _build_config_tab(self):
        self.config_tab.columnconfigure(0, weight=1)
        self.config_tab.columnconfigure(1, weight=1)
        self.config_tab.rowconfigure(0, weight=1)

        left = ttk.LabelFrame(self.config_tab, text="Runtime Controls", style="Card.TLabelframe", padding=14)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 6), pady=(0, 8))
        left.columnconfigure(0, weight=1)

        ttk.Label(left, text="Select AI Provider", style="Card.TLabel").grid(row=0, column=0, sticky="w")
        radio_wrap = ttk.Frame(left, style="Card.TFrame")
        radio_wrap.grid(row=1, column=0, sticky="w", pady=(8, 8))

        ttk.Radiobutton(
            radio_wrap, text="Auto", variable=self.provider_var, value="auto", style="Card.TRadiobutton", cursor="hand2"
        ).grid(row=0, column=0, sticky="w")
        ttk.Radiobutton(
            radio_wrap, text="Mistral First", variable=self.provider_var, value="mistral", style="Card.TRadiobutton", cursor="hand2"
        ).grid(row=0, column=1, sticky="w", padx=(12, 0))
        ttk.Radiobutton(
            radio_wrap, text="Gemini First", variable=self.provider_var, value="gemini", style="Card.TRadiobutton", cursor="hand2"
        ).grid(row=0, column=2, sticky="w", padx=(12, 0))

        ttk.Checkbutton(
            left,
            text="Enable automatic fallback to backup provider",
            variable=self.fallback_var,
            style="Card.TCheckbutton",
            cursor="hand2"
        ).grid(row=2, column=0, sticky="w", pady=(4, 10))

        ttk.Label(left, text="Provider order (comma separated)", style="Card.TLabel").grid(
            row=3, column=0, sticky="w"
        )
        ttk.Entry(left, textvariable=self.provider_order_var, style="Card.TEntry").grid(
            row=4, column=0, sticky="ew", pady=(6, 12)
        )

        ttk.Label(left, text="Target host used by Start Audit", style="Card.TLabel").grid(row=5, column=0, sticky="w")
        
        self.config_target_frame = ttk.Frame(left, style="Card.TFrame")
        self.config_target_frame.grid(row=6, column=0, sticky="ew", pady=(6, 10))
        self.config_target_frame.columnconfigure(0, weight=1)
        
        self.config_target_entry = ttk.Entry(self.config_target_frame, textvariable=self.target_var, style="Card.TEntry")
        self.config_target_entry.grid(row=0, column=0, sticky="ew")
        
        self.config_placeholder_label = tk.Label(
            self.config_target_frame, 
            text="e.g. localhost", 
            fg=self.colors["muted"], 
            bg=self.colors["input"], 
            font=("Consolas", 11),
            cursor="xterm"
        )
        self.config_placeholder_label.place(x=12, rely=0.5, anchor="w")
        self.config_placeholder_label.bind("<Button-1>", lambda e: self.config_target_entry.focus_set())
        
        def update_config_placeholder(*args):
            if self.target_var.get():
                self.config_placeholder_label.place_forget()
            else:
                self.config_placeholder_label.place(x=12, rely=0.5, anchor="w")
                
        self.target_var.trace_add("write", update_config_placeholder)
        self.after(50, update_config_placeholder)

        right = ttk.LabelFrame(self.config_tab, text="Provider Configuration", style="Card.TLabelframe", padding=14)
        right.grid(row=0, column=1, sticky="nsew", padx=(6, 0), pady=(0, 8))
        right.columnconfigure(0, weight=1)

        ttk.Label(right, text="Mistral models", style="Card.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Entry(right, textvariable=self.mistral_models_var, style="Card.TEntry").grid(
            row=1, column=0, sticky="ew", pady=(6, 10)
        )

        ttk.Label(right, text="Gemini models", style="Card.TLabel").grid(row=2, column=0, sticky="w")
        ttk.Entry(right, textvariable=self.gemini_models_var, style="Card.TEntry").grid(
            row=3, column=0, sticky="ew", pady=(6, 10)
        )

        ttk.Label(right, text="Mistral API key", style="Card.TLabel").grid(row=4, column=0, sticky="w")
        ttk.Entry(right, textvariable=self.mistral_key_var, style="Card.TEntry", show="*").grid(
            row=5, column=0, sticky="ew", pady=(6, 10)
        )

        ttk.Label(right, text="Gemini API key", style="Card.TLabel").grid(row=6, column=0, sticky="w")
        ttk.Entry(right, textvariable=self.gemini_key_var, style="Card.TEntry", show="*").grid(
            row=7, column=0, sticky="ew", pady=(6, 14)
        )

        bottom = ttk.Frame(right, style="Card.TFrame")
        bottom.grid(row=8, column=0, sticky="ew")
        bottom.columnconfigure(2, weight=1)

        ttk.Button(bottom, text="Save Config", style="Primary.TButton", command=self.save_config, cursor="hand2").grid(
            row=0, column=0, sticky="w"
        )
        ttk.Button(bottom, text="Reset Defaults", style="Secondary.TButton", command=self.reset_defaults, cursor="hand2").grid(
            row=0, column=1, sticky="w", padx=(8, 0)
        )

    def _build_help_tab(self):
        self.help_tab.columnconfigure(0, weight=1)
        self.help_tab.rowconfigure(0, weight=1)

        info = ttk.Frame(self.help_tab, style="Card.TFrame", padding=16)
        info.grid(row=0, column=0, sticky="nsew")
        info.columnconfigure(0, weight=1)

        ttk.Label(info, text="Workflow", style="Card.TLabel", font=("Segoe UI Semibold", 11)).grid(
            row=0, column=0, sticky="w"
        )

        tips = (
            "1. Set provider mode and keys in Configuration tab.\n"
            "2. Keep fallback enabled to switch providers automatically when rate-limited.\n"
            "3. Click Start Audit in the Audit tab to run main.py with your config.\n"
            "4. Use Export Log to save console output to a text file.\n"
            "5. Full memory trail is still written to Aegis_Audit_Log.md by the core runner."
        )

        text = tk.Text(
            info,
            wrap="word",
            relief="flat",
            borderwidth=0,
            bg=self.colors["card"],
            fg=self.colors["text"],
            font=("Consolas", 11),
            height=14,
        )
        text.grid(row=1, column=0, sticky="nsew", pady=(10, 0))
        text.insert("1.0", tips)
        text.configure(state="disabled")

    def _collect_config(self):
        return {
            "target": self.target_var.get().strip() or "localhost",
            "ai_provider": self.provider_var.get().strip().lower() or "auto",
            "ai_provider_order": self.provider_order_var.get().strip().lower() or "mistral,gemini",
            "ai_enable_fallback": bool(self.fallback_var.get()),
            "mistral_models": self.mistral_models_var.get().strip(),
            "gemini_models": self.gemini_models_var.get().strip(),
            "mistral_api_key": self.mistral_key_var.get().strip(),
            "gemini_api_key": self.gemini_key_var.get().strip(),
        }

    def _load_config(self, initial=False):
        config = dict(DEFAULT_CONFIG)
        if CONFIG_PATH.exists():
            try:
                file_data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
                if isinstance(file_data, dict):
                    config.update(file_data)
            except Exception as exc:
                if not initial:
                    messagebox.showwarning("Config", f"Could not read config file:\n{exc}")

        self.target_var.set(config.get("target", DEFAULT_CONFIG["target"]))
        self.provider_var.set(config.get("ai_provider", DEFAULT_CONFIG["ai_provider"]))
        self.provider_order_var.set(config.get("ai_provider_order", DEFAULT_CONFIG["ai_provider_order"]))
        self.fallback_var.set(bool(config.get("ai_enable_fallback", DEFAULT_CONFIG["ai_enable_fallback"])))
        self.mistral_models_var.set(config.get("mistral_models", DEFAULT_CONFIG["mistral_models"]))
        self.gemini_models_var.set(config.get("gemini_models", DEFAULT_CONFIG["gemini_models"]))
        self.mistral_key_var.set(config.get("mistral_api_key", DEFAULT_CONFIG["mistral_api_key"]))
        self.gemini_key_var.set(config.get("gemini_api_key", DEFAULT_CONFIG["gemini_api_key"]))

    def save_config(self):
        self._write_config(show_dialog=True)

    def _write_config(self, show_dialog=False):
        config = self._collect_config()
        try:
            CONFIG_PATH.write_text(json.dumps(config, indent=2), encoding="utf-8")
            if show_dialog:
                messagebox.showinfo("Config", "Configuration saved.")
        except Exception as exc:
            messagebox.showerror("Config", f"Failed to save config:\n{exc}")

    def reset_defaults(self):
        self.target_var.set(DEFAULT_CONFIG["target"])
        self.provider_var.set(DEFAULT_CONFIG["ai_provider"])
        self.provider_order_var.set(DEFAULT_CONFIG["ai_provider_order"])
        self.fallback_var.set(DEFAULT_CONFIG["ai_enable_fallback"])
        self.mistral_models_var.set(DEFAULT_CONFIG["mistral_models"])
        self.gemini_models_var.set(DEFAULT_CONFIG["gemini_models"])
        self.mistral_key_var.set(DEFAULT_CONFIG["mistral_api_key"])
        self.gemini_key_var.set(DEFAULT_CONFIG["gemini_api_key"])
        self._update_provider_hint()

    def _update_provider_hint(self):
        mode = self.provider_var.get().strip().lower() or "auto"
        order = self.provider_order_var.get().strip().lower() or "mistral,gemini"
        fallback = "ON" if self.fallback_var.get() else "OFF"

        if mode == "auto":
            text = f"Auto route: {order} | Fallback {fallback}"
        elif mode == "mistral":
            text = f"Primary: Mistral | Fallback {fallback}"
        else:
            text = f"Primary: Gemini | Fallback {fallback}"

        self.provider_hint_var.set(text)

    def _append_output(self, text):
        self.output_text.configure(state="normal")
        self.output_text.insert("end", text)
        self.output_text.see("end")
        self.output_text.configure(state="disabled")

    def clear_output(self):
        self.output_text.configure(state="normal")
        self.output_text.delete("1.0", "end")
        self.output_text.configure(state="disabled")

    def export_output(self):
        content = self.output_text.get("1.0", "end").strip()
        if not content:
            messagebox.showinfo("Export", "No output available to export.")
            return

        save_path = filedialog.asksaveasfilename(
            title="Export audit output",
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
        )
        if not save_path:
            return

        try:
            Path(save_path).write_text(content + "\n", encoding="utf-8")
            messagebox.showinfo("Export", "Audit output exported successfully.")
        except Exception as exc:
            messagebox.showerror("Export", f"Failed to export output:\n{exc}")

    def _build_env(self):
        cfg = self._collect_config()
        env = os.environ.copy()
        env["AI_PROVIDER"] = cfg["ai_provider"]
        env["AI_PROVIDER_ORDER"] = cfg["ai_provider_order"]
        env["AI_ENABLE_FALLBACK"] = "1" if cfg["ai_enable_fallback"] else "0"

        if cfg["mistral_models"]:
            env["MISTRAL_MODELS"] = cfg["mistral_models"]
        if cfg["gemini_models"]:
            env["GEMINI_MODELS"] = cfg["gemini_models"]

        if cfg["mistral_api_key"]:
            env["MISTRAL_API_KEY"] = cfg["mistral_api_key"]
        if cfg["gemini_api_key"]:
            env["GEMINI_API_KEY"] = cfg["gemini_api_key"]

        return env

    def start_audit(self):
        if self.process and self.process.poll() is None:
            return

        self._write_config(show_dialog=False)
        target = self.target_var.get().strip() or "localhost"

        if getattr(sys, 'frozen', False):
            command = [sys.executable, "--run-backend", "--target", target]
        else:
            if not MAIN_SCRIPT.exists():
                messagebox.showerror("Run", "main.py not found in project root.")
                return
            command = [sys.executable, str(MAIN_SCRIPT), "--target", target]

        creationflags = 0
        if os.name == "nt":
            creationflags = subprocess.CREATE_NO_WINDOW

        try:
            self.process = subprocess.Popen(
                command,
                cwd=str(PROJECT_ROOT),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
                env=self._build_env(),
                creationflags=creationflags,
            )
        except Exception as exc:
            messagebox.showerror("Run", f"Failed to start audit:\n{exc}")
            self.process = None
            return

        self.clear_output()
        self.status_var.set(f"Running audit on {target}")
        self.start_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")
        self.progress.start(10)

        self._append_output("[UI] Launching audit process...\n")
        self._append_output(f"[UI] Command: {' '.join(command)}\n\n")

        self.reader_thread = threading.Thread(target=self._stream_process_output, daemon=True)
        self.reader_thread.start()

        if self.polling_after_id is None:
            self.polling_after_id = self.after(100, self._drain_output_queue)

    def _stream_process_output(self):
        if not self.process or not self.process.stdout:
            return

        for line in self.process.stdout:
            self.output_queue.put(("line", line))

        return_code = self.process.wait()
        self.output_queue.put(("exit", return_code))

    def _drain_output_queue(self):
        try:
            while True:
                kind, value = self.output_queue.get_nowait()
                if kind == "line":
                    self._append_output(value)
                elif kind == "exit":
                    self._on_process_exit(value)
        except queue.Empty:
            pass

        if self.process and self.process.poll() is None:
            self.polling_after_id = self.after(100, self._drain_output_queue)
        else:
            self.polling_after_id = None

    def _on_process_exit(self, return_code):
        self.progress.stop()
        self.start_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")

        if return_code == 0:
            self.status_var.set("Completed successfully")
            self._append_output("\n[UI] Audit completed successfully.\n")
        else:
            self.status_var.set(f"Process exited with code {return_code}")
            self._append_output(f"\n[UI] Audit exited with code {return_code}.\n")

        self.process = None

    def stop_audit(self):
        if not self.process or self.process.poll() is not None:
            return

        self._append_output("\n[UI] Stop requested. Terminating process...\n")
        self.status_var.set("Stopping...")

        try:
            self.process.terminate()
        except Exception as exc:
            self._append_output(f"[UI] Terminate failed: {exc}\n")

    def _on_close(self):
        if self.process and self.process.poll() is None:
            should_close = messagebox.askyesno(
                "Exit",
                "An audit is still running. Stop it and exit?",
            )
            if not should_close:
                return
            try:
                self.process.terminate()
            except Exception:
                pass

        self.destroy()


def main():
    app = AegisUI()
    app.mainloop()


if __name__ == "__main__":
    main()
