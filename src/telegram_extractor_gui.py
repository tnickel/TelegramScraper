#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Telegram Chat & Forex File Extractor - GUI
===========================================
Diese grafische Benutzeroberfläche ermöglicht es Benutzern, Telegram-Chat-Exporte (JSON)
zu verarbeiten oder sich direkt über die Telegram-API (Telethon) einzuloggen, um Chats 
live herunterzuladen.

Bietet:
1. Methode A: Offline JSON-Export Parser
2. Methode B: Live API-Downloader (Telethon) - mit automatischer Pip-Installationsmöglichkeit.
"""

import os
import sys
import json
import queue
import shutil
import threading
import asyncio
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
from datetime import datetime

# Projekt-Wurzelverzeichnis definieren
PROJECT_ROOT = Path(__file__).parent.parent.resolve()

# Kernfunktionen importieren
try:
    from telegram_extractor import parse_telegram_json, DEFAULT_EXTENSIONS
except ImportError:
    DEFAULT_EXTENSIONS = {".mq4", ".mq5", ".ex4", ".ex5", ".set"}
    def parse_telegram_json(*args, **kwargs):
        pass

from backtest_data import (
    determine_periods_list as determine_backtest_periods,
    determine_symbols_list as determine_backtest_symbols,
    get_backtester_root,
    load_backtest_robots_from_db,
    resolve_backtest_assets,
)

# DPI-Awareness für Windows
try:
    import ctypes
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    pass


class AsyncLoopThread(threading.Thread):
    """Eigener Thread für den Asyncio-Event-Loop von Telethon."""
    def __init__(self):
        super().__init__(daemon=True)
        self.loop = None
        self.ready = threading.Event()

    def run(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.ready.set()
        self.loop.run_forever()

    def run_coro(self, coro):
        self.ready.wait()
        future = asyncio.run_coroutine_threadsafe(coro, self.loop)
        return future.result()


class ExtractorGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Telegram Chat & Forex Extractor")
        self.root.geometry("1100x780")
        self.root.minsize(950, 700)
        self.root.configure(bg="#f3f4f6")
        
        # Grid-Gewichtung des Hauptfensters
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)  # Notebook (Tabs)
        self.root.rowconfigure(1, weight=0)  # Console Label
        self.root.rowconfigure(2, weight=0)  # Console Textbox (feste Höhe)
        self.root.rowconfigure(3, weight=0)  # Buttons nach Abschluss
        
        # State-Variablen
        self.json_path_var = tk.StringVar()
        self.out_dir_var = tk.StringVar(value=str(PROJECT_ROOT / "extracted_data"))
        self.chunk_size_var = tk.StringVar(value="500")
        self.exts_var = tk.StringVar(value=".mq4, .mq5, .ex4, .ex5, .set")
        self.status_var = tk.StringVar(value="Bereit. Bitte wählen Sie eine Methode.")
        
        # API State-Variablen
        self.api_id_var = tk.StringVar(value=os.environ.get("TELEGRAM_API_ID", ""))
        self.api_hash_var = tk.StringVar(value=os.environ.get("TELEGRAM_API_HASH", ""))
        self.phone_var = tk.StringVar(value="")
        self.selected_chat_var = tk.StringVar()
        
        # Versuche lokale Konfigurationsdatei zu laden
        self.load_local_config()
        
        # Interner Status
        self.log_queue = queue.Queue()
        self.extraction_running = False
        self.telethon_available = False
        self.async_thread = None
        self.downloader = None
        self.loaded_chats = []
        
        # Styles erstellen
        self.create_styles()
        
        # Notebook (Tabbed Interface)
        self.notebook = ttk.Notebook(self.root)
        self.notebook.grid(row=0, column=0, sticky="nsew", padx=15, pady=(15, 5))
        
        # Tab-Frames erstellen
        self.tab_json = ttk.Frame(self.notebook)
        self.tab_api = ttk.Frame(self.notebook)
        self.tab_backtest = ttk.Frame(self.notebook)
        
        self.notebook.add(self.tab_json, text="  Methode A: JSON-Export Parser (Offline)  ")
        self.notebook.add(self.tab_api, text="  Methode B: Direkt-Download (API Online)  ")
        self.notebook.add(self.tab_backtest, text="  Batch Backtester (MT5)  ")
        
        # Tabs aufbauen
        self.build_json_tab()
        self.build_api_tab()
        self.build_backtest_tab()
        
        # Gemeinsame Konsole am unteren Rand aufbauen
        self.build_console_pane()
        
        # Log-Polling und Telethon-Prüfung starten
        self.poll_logs()
        self.check_telethon_installation()
        
        # Automatisch im aktuellen Ordner nach result.json suchen (für Methode A)
        default_json = PROJECT_ROOT / "result.json"
        if default_json.exists():
            self.json_path_var.set(str(default_json))
            self.log("INFO: 'result.json' im Projektordner gefunden. (Methode A)")
            self.status_var.set("Lokale result.json geladen. Bereit zur Extraktion.")
            
        # Log-Meldung für geladene Konfig
        if (PROJECT_ROOT / "config.local.json").exists():
            self.log("INFO: Lokale Konfiguration 'config.local.json' erfolgreich geladen (Telefonnummer & API-Daten voreingestellt).")

    def load_local_config(self):
        config_path = PROJECT_ROOT / "config.local.json"
        if config_path.exists():
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    config = json.load(f)
                if "phone" in config:
                    self.phone_var.set(config["phone"])
                if "api_id" in config:
                    self.api_id_var.set(str(config["api_id"]))
                if "api_hash" in config:
                    self.api_hash_var.set(config["api_hash"])
            except Exception as e:
                print(f"[-] Fehler beim Laden von config.local.json: {e}")

    def create_styles(self):
        self.style = ttk.Style()
        self.style.theme_use("vista" if "vista" in self.style.theme_names() else "clam")
        
        # Allgemeines Design
        self.style.configure(".", font=("Segoe UI", 10))
        self.style.configure("TFrame", background="#f3f4f6")
        self.style.configure("TNotebook", background="#f3f4f6", borderwidth=0)
        self.style.configure("TNotebook.Tab", font=("Segoe UI", 10, "bold"), padding=(15, 6))
        
        # Karten-Design
        self.style.configure("Card.TFrame", background="#ffffff", relief="flat", borderwidth=0)
        self.style.configure("InnerCard.TFrame", background="#ffffff")
        
        # Labels
        self.style.configure("Title.TLabel", font=("Segoe UI", 14, "bold"), background="#ffffff", foreground="#1f2937")
        self.style.configure("Sub.TLabel", font=("Segoe UI", 9, "italic"), background="#ffffff", foreground="#6b7280")
        self.style.configure("Step.TLabel", font=("Segoe UI", 10, "bold"), background="#ffffff", foreground="#111827")
        self.style.configure("Warning.TLabel", font=("Segoe UI", 10, "bold"), background="#fee2e2", foreground="#991b1b")
        
        # Buttons
        self.style.configure("Accent.TButton", font=("Segoe UI", 10, "bold"), background="#1a73e8", foreground="#ffffff")
        self.style.map("Accent.TButton",
                       background=[("active", "#1557b0"), ("disabled", "#d1d5db")],
                       foreground=[("disabled", "#9ca3af")])
        
        self.style.configure("Secondary.TButton", font=("Segoe UI", 9), background="#ffffff", foreground="#374151")
        self.style.map("Secondary.TButton",
                       background=[("active", "#f3f4f6")])

    # ----------------------------------------------------
    # TAB 1: JSON EXPORT PARSER
    # ----------------------------------------------------
    def build_json_tab(self):
        self.tab_json.columnconfigure(0, weight=4)
        self.tab_json.columnconfigure(1, weight=5)
        self.tab_json.rowconfigure(0, weight=1)
        
        # --- LINKE SPALTE (Anleitung JSON) ---
        left_frame = ttk.Frame(self.tab_json, padding=(10, 10, 5, 10))
        left_frame.grid(row=0, column=0, sticky="nsew")
        left_frame.columnconfigure(0, weight=1)
        left_frame.rowconfigure(0, weight=1)
        
        card_left = ttk.Frame(left_frame, style="Card.TFrame", padding=15)
        card_left.grid(row=0, column=0, sticky="nsew")
        card_left.columnconfigure(0, weight=1)
        
        ttk.Label(card_left, text="Anleitung: JSON-Export", style="Title.TLabel").pack(anchor="w")
        ttk.Label(card_left, text="Manuelles Exportieren über Telegram Desktop", style="Sub.TLabel").pack(anchor="w", pady=(0, 10))
        ttk.Separator(card_left, orient="horizontal").pack(fill="x", pady=(0, 10))
        
        # Anleitungstext
        steps_box = tk.Text(card_left, wrap="word", bg="#ffffff", bd=0, highlightthickness=0, font=("Segoe UI", 10), fg="#374151")
        steps_box.pack(fill="both", expand=True)
        
        instructions = (
            "1. Öffnen Sie Telegram Desktop auf Ihrem PC.\n\n"
            "2. Gehen Sie in den gewünschten Chat (Gruppe oder Kanal).\n\n"
            "3. Klicken Sie oben rechts auf das Menü-Symbol (drei Punkte ⋮) und wählen Sie 'Chatverlauf exportieren'.\n\n"
            "4. SEHR WICHTIG: Ändern Sie das Format von HTML auf JSON!\n\n"
            "5. Erhöhen Sie das Dateigrößenlimit (Schieberegler ganz nach rechts schieben) und aktivieren Sie den Haken bei 'Dateien' bzw. 'Dokumente'.\n\n"
            "6. Klicken Sie auf 'Exportieren'.\n\n"
            "7. Wählen Sie danach im rechten Bereich die exportierte Datei 'result.json' aus und starten Sie die Extraktion."
        )
        steps_box.insert("1.0", instructions)
        steps_box.configure(state="disabled")
        
        # --- RECHTE SPALTE (Steuerung JSON) ---
        right_frame = ttk.Frame(self.tab_json, padding=(5, 10, 10, 10))
        right_frame.grid(row=0, column=1, sticky="nsew")
        right_frame.columnconfigure(0, weight=1)
        right_frame.rowconfigure(0, weight=1)
        
        card_right = ttk.Frame(right_frame, style="Card.TFrame", padding=15)
        card_right.grid(row=0, column=0, sticky="nsew")
        card_right.columnconfigure(0, weight=1)
        
        ttk.Label(card_right, text="Optionen & Start", style="Title.TLabel").pack(anchor="w")
        ttk.Label(card_right, text="Lokalen Chat-Export einlesen", style="Sub.TLabel").pack(anchor="w", pady=(0, 10))
        ttk.Separator(card_right, orient="horizontal").pack(fill="x", pady=(0, 15))
        
        # Formularfelder
        form = ttk.Frame(card_right, style="InnerCard.TFrame")
        form.pack(fill="x", pady=(0, 15))
        form.columnconfigure(0, weight=1)
        
        # JSON-Pfad
        ttk.Label(form, text="Telegram Export (result.json):", font=("Segoe UI", 10, "bold"), background="#ffffff").grid(row=0, column=0, sticky="w", pady=(5, 2))
        entry_json = ttk.Entry(form, textvariable=self.json_path_var, font=("Segoe UI", 10))
        entry_json.grid(row=1, column=0, sticky="ew", pady=(0, 5), padx=(0, 95))
        btn_json = ttk.Button(form, text="Durchsuchen...", style="Secondary.TButton", command=self.browse_json)
        btn_json.grid(row=1, column=0, sticky="e", pady=(0, 5))
        
        # Ausgabe-Pfad
        ttk.Label(form, text="Ausgabeordner:", font=("Segoe UI", 10, "bold"), background="#ffffff").grid(row=2, column=0, sticky="w", pady=(5, 2))
        entry_out = ttk.Entry(form, textvariable=self.out_dir_var, font=("Segoe UI", 10))
        entry_out.grid(row=3, column=0, sticky="ew", pady=(0, 5), padx=(0, 95))
        btn_out = ttk.Button(form, text="Durchsuchen...", style="Secondary.TButton", command=self.browse_out_dir)
        btn_out.grid(row=3, column=0, sticky="e", pady=(0, 5))
        
        # Parameter
        param_grid = ttk.Frame(form, style="InnerCard.TFrame")
        param_grid.grid(row=4, column=0, sticky="ew", pady=(10, 0))
        param_grid.columnconfigure(0, weight=1)
        param_grid.columnconfigure(1, weight=1)
        
        ttk.Label(param_grid, text="Nachrichten pro KI-Chunk:", font=("Segoe UI", 10, "bold"), background="#ffffff").grid(row=0, column=0, sticky="w")
        ttk.Entry(param_grid, textvariable=self.chunk_size_var, width=15).grid(row=1, column=0, sticky="w", pady=(2, 0))
        
        ttk.Label(param_grid, text="Forex-Dateiendungen:", font=("Segoe UI", 10, "bold"), background="#ffffff").grid(row=0, column=1, sticky="w")
        ttk.Entry(param_grid, textvariable=self.exts_var, width=25).grid(row=1, column=1, sticky="ew", pady=(2, 0))
        
        # Button Start
        self.btn_run_json = tk.Button(
            card_right,
            text="▶  JSON-Extraktion starten",
            bg="#1a73e8",
            fg="#ffffff",
            activebackground="#1557b0",
            activeforeground="#ffffff",
            disabledforeground="#9ca3af",
            bd=0,
            pady=8,
            font=("Segoe UI", 10, "bold"),
            command=self.start_json_extraction,
            cursor="hand2"
        )
        self.btn_run_json.pack(fill="x", side="bottom", pady=(10, 0))

    # ----------------------------------------------------
    # TAB 2: TELEGRAM API DOWNLOADER (TELETHON)
    # ----------------------------------------------------
    def build_api_tab(self):
        self.tab_api.columnconfigure(0, weight=4)
        self.tab_api.columnconfigure(1, weight=5)
        self.tab_api.rowconfigure(0, weight=1)
        
        # --- LINKE SPALTE (Anleitung API) ---
        left_frame = ttk.Frame(self.tab_api, padding=(10, 10, 5, 10))
        left_frame.grid(row=0, column=0, sticky="nsew")
        left_frame.columnconfigure(0, weight=1)
        left_frame.rowconfigure(0, weight=1)
        
        card_left = ttk.Frame(left_frame, style="Card.TFrame", padding=15)
        card_left.grid(row=0, column=0, sticky="nsew")
        card_left.columnconfigure(0, weight=1)
        
        ttk.Label(card_left, text="Anleitung: Direkt-Download", style="Title.TLabel").pack(anchor="w")
        ttk.Label(card_left, text="Direkte Verbindung zu den Telegram-Servern", style="Sub.TLabel").pack(anchor="w", pady=(0, 10))
        ttk.Separator(card_left, orient="horizontal").pack(fill="x", pady=(0, 10))
        
        # Anleitungstext
        steps_box = tk.Text(card_left, wrap="word", bg="#ffffff", bd=0, highlightthickness=0, font=("Segoe UI", 10), fg="#374151")
        steps_box.pack(fill="both", expand=True)
        
        instructions = (
            "1. Geben Sie Ihre Telefonnummer im internationalen Format ein (z.B. +491701234567).\n\n"
            "2. Die API-Zugangsdaten Ihrer App wurden bereits automatisch für Sie eingetragen.\n\n"
            "3. Klicken Sie auf '1. Anmelden & Chats laden'.\n\n"
            "4. Sie erhalten einen Login-Code direkt in Ihrer Telegram-App. Geben Sie diesen in das erscheinende Abfragefenster ein.\n\n"
            "   (Falls 2FA aktiv ist, fragt das Programm danach zusätzlich nach Ihrem Passwort).\n\n"
            "5. Nach der Anmeldung können Sie Ihren gewünschten Forex-Chat aus der Liste auswählen.\n\n"
            "6. Klicken Sie auf '2. Download & Extraktion starten'. Das Programm lädt den Chatverlauf live herunter und verarbeitet ihn."
        )
        steps_box.insert("1.0", instructions)
        steps_box.configure(state="disabled")
        
        # --- RECHTE SPALTE (Steuerung API) ---
        right_frame = ttk.Frame(self.tab_api, padding=(5, 10, 10, 10))
        right_frame.grid(row=0, column=1, sticky="nsew")
        right_frame.columnconfigure(0, weight=1)
        right_frame.rowconfigure(0, weight=1)
        
        self.card_api_right = ttk.Frame(right_frame, style="Card.TFrame", padding=15)
        self.card_api_right.grid(row=0, column=0, sticky="nsew")
        self.card_api_right.columnconfigure(0, weight=1)
        
        ttk.Label(self.card_api_right, text="API Konfiguration & Verbindung", style="Title.TLabel").pack(anchor="w")
        ttk.Label(self.card_api_right, text="Direktverbindung einrichten", style="Sub.TLabel").pack(anchor="w", pady=(0, 10))
        ttk.Separator(self.card_api_right, orient="horizontal").pack(fill="x", pady=(10, 10))
        
        # Telethon Warnungs-Frame (wird angezeigt, wenn Telethon fehlt)
        self.telethon_warning_frame = tk.Frame(self.card_api_right, bg="#fee2e2", padx=10, pady=10)
        self.telethon_warning_frame.pack(fill="x", pady=(0, 10))
        
        lbl_warning = tk.Label(
            self.telethon_warning_frame, 
            text="⚠️ Die Bibliothek 'telethon' fehlt.\nBitte installieren Sie sie, um den API-Download zu nutzen.", 
            font=("Segoe UI", 10, "bold"), bg="#fee2e2", fg="#991b1b", justify="left"
        )
        lbl_warning.pack(side="left", fill="x", expand=True)
        
        self.btn_install_telethon = tk.Button(
            self.telethon_warning_frame, 
            text="Jetzt installieren", 
            bg="#991b1b", 
            fg="#ffffff", 
            activebackground="#7f1d1d", 
            activeforeground="#ffffff", 
            bd=0, 
            padx=12, 
            pady=6, 
            font=("Segoe UI", 9, "bold"), 
            command=self.install_telethon,
            cursor="hand2"
        )
        self.btn_install_telethon.pack(side="right", padx=5)
        
        # Steuerungsbereich (wird bei fehlendem Telethon deaktiviert)
        self.api_controls_frame = ttk.Frame(self.card_api_right, style="InnerCard.TFrame")
        self.api_controls_frame.pack(fill="both", expand=True)
        self.api_controls_frame.columnconfigure(0, weight=1)
        
        # Formularfelder API
        # 1. API ID & Hash
        api_creds_frame = ttk.Frame(self.api_controls_frame, style="InnerCard.TFrame")
        api_creds_frame.pack(fill="x", pady=(0, 5))
        api_creds_frame.columnconfigure(0, weight=1)
        api_creds_frame.columnconfigure(1, weight=1)
        
        ttk.Label(api_creds_frame, text="App API ID:", font=("Segoe UI", 9, "bold"), background="#ffffff").grid(row=0, column=0, sticky="w")
        self.entry_api_id = ttk.Entry(api_creds_frame, textvariable=self.api_id_var, width=15)
        self.entry_api_id.grid(row=1, column=0, sticky="w", pady=(2, 0))
        
        ttk.Label(api_creds_frame, text="App API Hash:", font=("Segoe UI", 9, "bold"), background="#ffffff").grid(row=0, column=1, sticky="w")
        self.entry_api_hash = ttk.Entry(api_creds_frame, textvariable=self.api_hash_var, width=30)
        self.entry_api_hash.grid(row=1, column=1, sticky="ew", pady=(2, 0))
        
        # 2. Telefonnummer
        ttk.Label(self.api_controls_frame, text="Telefonnummer (z. B. +491701234567):", font=("Segoe UI", 10, "bold"), background="#ffffff").pack(anchor="w", pady=(5, 2))
        self.entry_phone = ttk.Entry(self.api_controls_frame, textvariable=self.phone_var, font=("Segoe UI", 10))
        self.entry_phone.pack(fill="x", pady=(0, 5))
        
        # Login Button
        self.btn_api_login = tk.Button(
            self.api_controls_frame, 
            text="1. Anmelden & Chats laden", 
            bg="#1a73e8", 
            fg="#ffffff", 
            activebackground="#1557b0", 
            activeforeground="#ffffff", 
            disabledforeground="#9ca3af", 
            bd=0, 
            pady=8, 
            font=("Segoe UI", 10, "bold"), 
            command=self.start_api_login,
            cursor="hand2"
        )
        self.btn_api_login.pack(fill="x", pady=(5, 10))
        
        # Separator
        ttk.Separator(self.api_controls_frame, orient="horizontal").pack(fill="x", pady=5)
        
        # 3. Chatverzeichnis Dropdown
        ttk.Label(self.api_controls_frame, text="Verfügbare Telegram-Chats:", font=("Segoe UI", 10, "bold"), background="#ffffff").pack(anchor="w", pady=(5, 2))
        self.chat_combobox = ttk.Combobox(self.api_controls_frame, state="disabled", textvariable=self.selected_chat_var, font=("Segoe UI", 10))
        self.chat_combobox.pack(fill="x", pady=(0, 10))
        
        # 4. Parameter (Ausgabe, Chunks etc. - geteilt, aber separat steuerbar)
        api_form_params = ttk.Frame(self.api_controls_frame, style="InnerCard.TFrame")
        api_form_params.pack(fill="x", pady=(0, 10))
        api_form_params.columnconfigure(0, weight=1)
        
        ttk.Label(api_form_params, text="Ausgabeordner:", font=("Segoe UI", 10, "bold"), background="#ffffff").grid(row=0, column=0, sticky="w", pady=(2, 2))
        self.entry_api_out = ttk.Entry(api_form_params, textvariable=self.out_dir_var, font=("Segoe UI", 10))
        self.entry_api_out.grid(row=1, column=0, sticky="ew", pady=(0, 5), padx=(0, 95))
        self.btn_api_out = ttk.Button(api_form_params, text="Durchsuchen...", style="Secondary.TButton", command=self.browse_out_dir)
        self.btn_api_out.grid(row=1, column=0, sticky="e", pady=(0, 5))
        
        # 5. Buttons & Actions
        self.btn_run_api = tk.Button(
            self.api_controls_frame, 
            text="▶  2. Download & Extraktion starten", 
            bg="#1a73e8", 
            fg="#ffffff", 
            activebackground="#1557b0", 
            activeforeground="#ffffff", 
            disabledforeground="#9ca3af", 
            bd=0, 
            pady=8, 
            font=("Segoe UI", 10, "bold"), 
            command=self.start_api_download, 
            state="disabled",
            cursor="hand2"
        )
        self.btn_run_api.pack(fill="x", side="bottom", pady=(10, 0))

    # ----------------------------------------------------
    # GEMEINSAME KONSOLE & FOOTER
    # ----------------------------------------------------
    def build_console_pane(self):
        # Console Label
        lbl_console = ttk.Label(self.root, text="Verlauf / Protokoll:", font=("Segoe UI", 10, "bold"))
        lbl_console.grid(row=1, column=0, sticky="w", padx=15, pady=(5, 2))
        
        # Console Card Frame
        card_console = ttk.Frame(self.root, style="Card.TFrame", padding=10)
        card_console.grid(row=2, column=0, sticky="nsew", padx=15, pady=(0, 5))
        card_console.columnconfigure(0, weight=1)
        card_console.rowconfigure(0, weight=1)
        
        # Text-Widget
        self.console = tk.Text(card_console, height=7, font=("Consolas", 9), bg="#1e1e1e", fg="#d4d4d4", wrap="word", state="disabled")
        self.console.grid(row=0, column=0, sticky="nsew")
        
        # Scrollbar
        console_scroll = ttk.Scrollbar(card_console, orient="vertical", command=self.console.yview)
        self.console.configure(yscrollcommand=console_scroll.set)
        console_scroll.grid(row=0, column=1, sticky="ns")
        
        # Status & Progress Area
        self.status_progress_frame = ttk.Frame(self.root, padding=(15, 2))
        self.status_progress_frame.grid(row=3, column=0, sticky="ew")
        self.status_progress_frame.columnconfigure(0, weight=1)
        
        self.lbl_status = ttk.Label(self.status_progress_frame, textvariable=self.status_var, font=("Segoe UI", 10, "bold"), foreground="#1a73e8")
        self.lbl_status.grid(row=0, column=0, sticky="w", pady=2)
        
        self.progress = ttk.Progressbar(self.status_progress_frame, mode="indeterminate")
        self.progress.grid(row=1, column=0, sticky="ew", pady=(2, 5))
        self.progress.grid_remove()
        
        # After Action Buttons (Folder & Report)
        self.after_action_frame = ttk.Frame(self.root, padding=(15, 5, 15, 15))
        self.after_action_frame.grid(row=4, column=0, sticky="ew")
        self.after_action_frame.columnconfigure(0, weight=1)
        self.after_action_frame.columnconfigure(1, weight=1)
        
        self.btn_open_folder = ttk.Button(self.after_action_frame, text="📁 Ausgabeordner im Explorer öffnen", style="Secondary.TButton", command=self.open_output_folder)
        self.btn_open_folder.grid(row=0, column=0, sticky="ew", padx=(0, 5))
        
        self.btn_open_report = ttk.Button(self.after_action_frame, text="📄 Forex-Bericht (.md) anzeigen", style="Secondary.TButton", command=self.open_report_file)
        self.btn_open_report.grid(row=0, column=1, sticky="ew", padx=(5, 0))
        
        self.after_action_frame.grid_remove()

    # ----------------------------------------------------
    # BROWSE ACTIONS & UTILS
    # ----------------------------------------------------
    def browse_json(self):
        filename = filedialog.askopenfilename(
            title="result.json von Telegram auswählen",
            filetypes=[("JSON-Dateien", "*.json"), ("Alle Dateien", "*.*")]
        )
        if filename:
            self.json_path_var.set(filename)
            self.status_var.set("result.json ausgewählt. Bereit zur Extraktion.")
            self.log(f"Ausgewählte JSON: {filename}")

    def browse_out_dir(self):
        directory = filedialog.askdirectory(
            title="Ausgabeordner für extrahierte Daten wählen"
        )
        if directory:
            self.out_dir_var.set(directory)
            self.log(f"Ausgewählter Ausgabeordner: {directory}")

    def log(self, message):
        self.log_queue.put(message)
        
        # Schreibe in Logdatei
        try:
            log_dir = PROJECT_ROOT / "log"
            log_dir.mkdir(parents=True, exist_ok=True)
            log_file = log_dir / "telegram_scraper.log"
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(f"[{timestamp}] {message}\n")
        except Exception:
            pass

    def write_to_console(self, text):
        self.console.configure(state="normal")
        self.console.insert("end", f"{text}\n")
        self.console.see("end")
        self.console.configure(state="disabled")

    def poll_logs(self):
        try:
            while True:
                msg = self.log_queue.get_nowait()
                self.write_to_console(msg)
        except queue.Empty:
            pass
        self.root.after(100, self.poll_logs)

    def open_output_folder(self):
        out_path = Path(self.out_dir_var.get())
        if out_path.exists():
            try:
                os.startfile(out_path)
            except Exception as e:
                messagebox.showerror("Fehler", f"Ordner konnte nicht geöffnet werden: {e}")
        else:
            messagebox.showwarning("Warnung", "Ausgabeordner existiert noch nicht.")

    def open_report_file(self):
        report_path = Path(self.out_dir_var.get()) / "forex_report.md"
        if report_path.exists():
            try:
                os.startfile(report_path)
            except Exception as e:
                messagebox.showerror("Fehler", f"Bericht konnte nicht geöffnet werden: {e}")
        else:
            messagebox.showwarning("Warnung", "Bericht-Datei existiert noch nicht.")

    # ----------------------------------------------------
    # TELETHON DEPENDENCY MANAGEMENT
    # ----------------------------------------------------
    def check_telethon_installation(self):
        """Prüft, ob telethon importiert werden kann."""
        try:
            import telethon
            self.telethon_available = True
            self.telethon_warning_frame.pack_forget() # Warnung ausblenden
            self.enable_api_tab()
        except ImportError:
            self.telethon_available = False
            self.telethon_warning_frame.pack(fill="x", before=self.api_controls_frame, pady=(0, 10))
            self.disable_api_tab()

    def install_telethon(self):
        self.log("[*] Installiere Telethon über pip...")
        self.btn_install_telethon.configure(state="disabled")
        
        def run_pip():
            import subprocess
            try:
                # Installiert Telethon in das aktuelle Python-Environment
                res = subprocess.run([sys.executable, "-m", "pip", "install", "telethon"], capture_output=True, text=True)
                if res.returncode == 0:
                    self.log("[+] Telethon erfolgreich installiert!")
                    self.root.after(0, self.check_telethon_installation)
                else:
                    self.log(f"[-] Installation fehlgeschlagen:\n{res.stderr}")
                    self.root.after(0, lambda: messagebox.showerror("Fehler", f"Installation fehlgeschlagen:\n{res.stderr}"))
                    self.root.after(0, lambda: self.btn_install_telethon.configure(state="normal"))
            except Exception as e:
                self.log(f"[-] Fehler bei Installation: {e}")
                self.root.after(0, lambda: messagebox.showerror("Fehler", f"Installation fehlgeschlagen: {e}"))
                self.root.after(0, lambda: self.btn_install_telethon.configure(state="normal"))
                
        threading.Thread(target=run_pip, daemon=True).start()

    def disable_api_tab(self):
        """Deaktiviert alle Steuerelemente auf dem API-Tab."""
        for child in self.api_controls_frame.winfo_children():
            self.set_state_recursive(child, "disabled")

    def enable_api_tab(self):
        """Aktiviert die Steuerelemente auf dem API-Tab."""
        for child in self.api_controls_frame.winfo_children():
            self.set_state_recursive(child, "normal")
        # Combobox und Start-Button separat sperren, da noch keine Chats geladen sind
        self.chat_combobox.configure(state="disabled")
        self.btn_run_api.configure(state="disabled")

    def set_state_recursive(self, widget, state):
        try:
            widget.configure(state=state)
        except tk.TclError:
            pass
        for child in widget.winfo_children():
            self.set_state_recursive(child, state)

    # ----------------------------------------------------
    # METHODE A: EXTRAKTION AUS JSON-EXPORT
    # ----------------------------------------------------
    def start_json_extraction(self):
        if self.extraction_running:
            return
        
        json_path = self.json_path_var.get()
        out_dir = self.out_dir_var.get()
        chunk_size_str = self.chunk_size_var.get()
        exts_str = self.exts_var.get()
        
        if not json_path:
            messagebox.showerror("Fehler", "Bitte wählen Sie die result.json-Datei aus.")
            return
        if not out_dir:
            messagebox.showerror("Fehler", "Bitte wählen Sie einen Ausgabeordner aus.")
            return
        
        try:
            chunk_size = int(chunk_size_str)
            if chunk_size <= 0:
                raise ValueError()
        except ValueError:
            messagebox.showerror("Fehler", "Die Nachrichtenanzahl pro Chunk muss eine positive Zahl sein.")
            return
            
        extensions = {ext.strip().lower() for ext in exts_str.split(",")}
        extensions = {ext if ext.startswith(".") else f".{ext}" for ext in extensions if ext}
        
        if not extensions:
            messagebox.showerror("Fehler", "Bitte geben Sie mindestens eine Dateiendung ein (z.B. .ex4).")
            return
            
        self.lock_gui_for_run()
        
        self.log("=== EXTRAKTION AUS JSON GESTARTET ===")
        self.log(f"JSON-Datei: {json_path}")
        self.log(f"Ausgabe: {out_dir}")
        self.log(f"Chunk-Größe: {chunk_size} Nachrichten")
        self.log(f"Ziel-Endungen: {', '.join(extensions)}")
        self.log("-----------------------------------------")
        
        thread = threading.Thread(
            target=self.run_json_extraction_thread,
            args=(json_path, out_dir, chunk_size, extensions),
            daemon=True
        )
        thread.start()

    def run_json_extraction_thread(self, json_path, out_dir, chunk_size, extensions):
        class ThreadSafeLogger:
            def __init__(self, log_func):
                self.log_func = log_func
            def write(self, msg):
                clean_msg = msg.strip()
                if clean_msg:
                    self.log_func(clean_msg)
            def flush(self):
                pass
                
        old_stdout = sys.stdout
        sys.stdout = ThreadSafeLogger(self.log)
        
        success = False
        try:
            success = parse_telegram_json(
                json_path=json_path,
                output_dir=out_dir,
                chunk_size=chunk_size,
                target_extensions=extensions
            )
        except Exception as e:
            self.log(f"[-] KRITISCHER FEHLER: {e}")
        finally:
            sys.stdout = old_stdout
            
        self.root.after(0, lambda: self.on_extraction_finished(success))

    # ----------------------------------------------------
    # METHODE B: API DOWNLOADER
    # ----------------------------------------------------
    def start_api_login(self):
        phone = self.phone_var.get().strip()
        api_id_str = self.api_id_var.get().strip()
        api_hash = self.api_hash_var.get().strip()
        
        if not phone:
            messagebox.showerror("Fehler", "Bitte geben Sie Ihre Telefonnummer ein (inkl. Ländervorwahl, z.B. +491701234567).")
            return
        if not api_id_str or not api_hash:
            messagebox.showerror("Fehler", "API ID und API Hash dürfen nicht leer sein.")
            return
            
        try:
            api_id = int(api_id_str)
        except ValueError:
            messagebox.showerror("Fehler", "Die API ID muss eine Zahl sein.")
            return

        self.btn_api_login.configure(state="disabled")
        self.progress.grid()
        self.progress.start(10)
        self.status_var.set("Verbinde mit Telegram... Bitte warten.")
        
        # Start Login Thread
        threading.Thread(target=self.api_login_worker, args=(api_id, api_hash, phone), daemon=True).start()

    def get_input_threadsafe(self, title, prompt, is_password=False):
        """Zeigt ein modales Eingabefenster thread-sicher im Haupt-Thread an."""
        result = {"value": None, "done": False}
        
        def show():
            dialog = tk.Toplevel(self.root)
            dialog.title(title)
            dialog.geometry("380x160")
            dialog.transient(self.root)
            dialog.grab_set()
            dialog.configure(bg="#ffffff")
            
            # Zentrieren über dem Hauptfenster
            x = self.root.winfo_rootx() + (self.root.winfo_width() // 2) - 190
            y = self.root.winfo_rooty() + (self.root.winfo_height() // 2) - 80
            dialog.geometry(f"+{x}+{y}")
            
            lbl = ttk.Label(dialog, text=prompt, font=("Segoe UI", 10), background="#ffffff", wrap=340)
            lbl.pack(fill="x", padx=20, pady=(20, 5))
            
            entry = ttk.Entry(dialog, font=("Segoe UI", 10))
            if is_password:
                entry.configure(show="*")
            entry.pack(fill="x", padx=20, pady=5)
            entry.focus_set()
            
            def on_ok(event=None):
                result["value"] = entry.get()
                result["done"] = True
                dialog.destroy()
                
            def on_cancel():
                result["done"] = True
                dialog.destroy()
                
            btn_frame = ttk.Frame(dialog, style="Card.TFrame")
            btn_frame.pack(fill="x", padx=20, pady=(15, 10))
            
            btn_ok = ttk.Button(btn_frame, text="OK", style="Accent.TButton", command=on_ok)
            btn_ok.pack(side="right", padx=(5, 0))
            
            btn_cancel = ttk.Button(btn_frame, text="Abbrechen", style="Secondary.TButton", command=on_cancel)
            btn_cancel.pack(side="right")
            
            entry.bind("<Return>", on_ok)
            dialog.protocol("WM_DELETE_WINDOW", on_cancel)
            
        self.root.after(0, show)
        import time
        while not result["done"]:
            time.sleep(0.1)
        return result["value"]

    def api_login_worker(self, api_id, api_hash, phone):
        try:
            self.log("[*] Initialisiere API Loop...")
            if not self.async_thread:
                self.async_thread = AsyncLoopThread()
                self.async_thread.start()
                
            if not self.downloader:
                from telegram_api_downloader import TelegramAPIDownloader
                self.downloader = TelegramAPIDownloader(api_id=api_id, api_hash=api_hash)
                self.async_thread.run_coro(asyncio.sleep(0.1)) # Kurze Pause
                self.downloader.initialize_client(self.async_thread.loop)
                
            self.log("[*] Verbinde mit Telegram Servern...")
            self.async_thread.run_coro(self.downloader.connect())
            
            authorized = self.async_thread.run_coro(self.downloader.is_authorized())
            if not authorized:
                self.log("[*] Anmeldung erforderlich. Code wird gesendet...")
                sent_code = self.async_thread.run_coro(self.downloader.send_code(phone))
                phone_code_hash = sent_code.phone_code_hash
                
                # Code erfragen
                code = self.get_input_threadsafe(
                    "Telegram Anmeldecode", 
                    "Geben Sie den Bestätigungscode ein, den Sie in Telegram erhalten haben:"
                )
                if not code:
                    self.log("[-] Code-Eingabe abgebrochen.")
                    return
                    
                try:
                    self.async_thread.run_coro(self.downloader.sign_in(phone, code, phone_code_hash=phone_code_hash))
                except Exception as e:
                    # Prüfen auf 2FA Passwort
                    if "SessionPasswordNeededError" in str(type(e)):
                        self.log("[*] Zweistufige Verifizierung (2FA) ist aktiv. Passwort erforderlich...")
                        pwd = self.get_input_threadsafe(
                            "Telegram 2FA Passwort", 
                            "Geben Sie Ihr Passwort für die zweistufige Verifizierung ein:",
                            is_password=True
                        )
                        if not pwd:
                            self.log("[-] Passwort-Eingabe abgebrochen.")
                            return
                        self.async_thread.run_coro(self.downloader.sign_in(password=pwd))
                    else:
                        raise e
                        
            self.log("[+] Erfolgreich bei Telegram angemeldet!")
            
            # Chats laden
            self.log("[*] Lade Chat-Liste...")
            chats = self.async_thread.run_coro(self.downloader.get_chat_list())
            
            # Dropdown aktualisieren im Hauptthread
            self.root.after(0, lambda: self.update_chat_dropdown(chats))
            
        except Exception as e:
            err_msg = str(e)
            self.log(f"[-] Login-Fehler: {err_msg}")
            self.root.after(0, lambda: messagebox.showerror("Fehler", f"Verbindung schlug fehl: {err_msg}"))
        finally:
            self.root.after(0, self.stop_api_progress)

    def update_chat_dropdown(self, chats):
        self.loaded_chats = chats
        if not chats:
            self.status_var.set("⚠️ Keine Chats gefunden.")
            self.chat_combobox.configure(state="disabled")
            self.btn_run_api.configure(state="disabled")
            return
            
        # Formatierte Liste für die Combobox
        display_names = []
        for c in chats:
            username_str = f" (@{c['username']})" if c['username'] else ""
            display_names.append(f"{c['name']} [{c['type']}]{username_str}")
            
        self.chat_combobox.configure(state="readonly", values=display_names)
        
        # Finde standardmäßig die FXCracked Gruppe
        default_index = 0
        for idx, c in enumerate(chats):
            if c.get("username") == "fxcracked_backup" or c.get("name") == "FXCracked - Group Chat":
                default_index = idx
                break
                
        self.chat_combobox.current(default_index)
        self.btn_run_api.configure(state="normal")
        self.status_var.set("Anmeldung erfolgreich. Wählen Sie einen Chat und starten Sie.")
        self.btn_api_login.configure(text="🔄 Chats neu laden")
        self.log(f"[+] {len(chats)} Chats erfolgreich geladen.")

    def stop_api_progress(self):
        self.progress.stop()
        self.progress.grid_remove()
        self.btn_api_login.configure(state="normal")

    def start_api_download(self):
        if self.extraction_running:
            return
            
        # Validierung
        selected_idx = self.chat_combobox.current()
        if selected_idx < 0:
            messagebox.showerror("Fehler", "Bitte wählen Sie einen Chat aus der Liste aus.")
            return
            
        out_dir = self.out_dir_var.get()
        chunk_size_str = self.chunk_size_var.get()
        exts_str = self.exts_var.get()
        
        if not out_dir:
            messagebox.showerror("Fehler", "Bitte wählen Sie einen Ausgabeordner aus.")
            return
            
        try:
            chunk_size = int(chunk_size_str)
            if chunk_size <= 0:
                raise ValueError()
        except ValueError:
            messagebox.showerror("Fehler", "Die Nachrichtenanzahl pro Chunk muss eine positive Zahl sein.")
            return
            
        extensions = {ext.strip().lower() for ext in exts_str.split(",")}
        extensions = {ext if ext.startswith(".") else f".{ext}" for ext in extensions if ext}
        
        if not extensions:
            messagebox.showerror("Fehler", "Bitte geben Sie mindestens eine Dateiendung ein (z.B. .ex4).")
            return
            
        self.lock_gui_for_run()
        
        chat_info = self.loaded_chats[selected_idx]
        
        thread = threading.Thread(
            target=self.run_api_download_thread,
            args=(chat_info, out_dir, chunk_size, extensions),
            daemon=True
        )
        thread.start()

    def run_api_download_thread(self, chat_info, out_dir, chunk_size, extensions):
        try:
            def progress_cb(status_msg, current, total):
                self.log(f"[*] {status_msg}")
                if total > 0:
                    pct = int((current / total) * 100)
                    self.status_var.set(f"Download läuft: {pct}% ({current}/{total} Nachrichten)")
            
            # Starte Download über Telethon im LoopThread
            files_count, msg_count = self.async_thread.run_coro(
                self.downloader.download_history(
                    chat_id=chat_info["id"],
                    output_dir=out_dir,
                    chunk_size=chunk_size,
                    target_extensions=extensions,
                    progress_callback=progress_cb
                )
            )
            
            self.log("=========================================")
            self.log(f"[+] Download & Extraktion abgeschlossen!")
            self.log(f"  - Verarbeitete Nachrichten: {msg_count}")
            self.log(f"  - Extrahierte Forex-Dateien: {files_count}")
            
            self.root.after(0, lambda: self.on_extraction_finished(True))
        except Exception as e:
            self.log(f"[-] Fehler beim Herunterladen: {e}")
            self.root.after(0, lambda: self.on_extraction_finished(False))

    # ----------------------------------------------------
    # GEMEINSAME VERARBEITUNG & GUI SPERREN
    # ----------------------------------------------------
    def lock_gui_for_run(self):
        self.extraction_running = True
        self.btn_run_json.configure(state="disabled")
        self.btn_run_api.configure(state="disabled")
        self.chat_combobox.configure(state="disabled")
        self.btn_api_login.configure(state="disabled")
        
        try:
            self.btn_bt_scan.configure(state="disabled")
            self.btn_run_backtest.configure(state="disabled")
            self.btn_select_all.configure(state="disabled")
            self.btn_deselect_all.configure(state="disabled")
        except AttributeError:
            pass
            
        self.progress.grid()
        self.progress.start(10)
        self.status_var.set("Aktion läuft... Bitte warten.")
        self.after_action_frame.grid_remove()
        
        # Konsole löschen
        self.console.configure(state="normal")
        self.console.delete("1.0", "end")
        self.console.configure(state="disabled")

    def on_extraction_finished(self, success):
        self.extraction_running = False
        self.btn_run_json.configure(state="normal")
        self.progress.stop()
        self.progress.grid_remove()
        
        # API-Elemente re-aktivieren, falls wir eingeloggt sind
        if self.loaded_chats:
            self.chat_combobox.configure(state="readonly")
            self.btn_run_api.configure(state="normal")
        self.btn_api_login.configure(state="normal")
        
        # Re-enable backtest controls
        try:
            self.btn_bt_scan.configure(state="normal")
            if self.candidates_data:
                self.btn_run_backtest.configure(state="normal")
            self.btn_select_all.configure(state="normal")
            self.btn_deselect_all.configure(state="normal")
        except AttributeError:
            pass
        
        if success:
            self.status_var.set("✅ Aktion erfolgreich abgeschlossen!")
            self.log("=========================================")
            self.log("✅ FERTIG! Alle Aktionen erfolgreich ausgeführt.")
            self.after_action_frame.grid()
            
            if messagebox.askyesno("Erfolg", "Die Aktion war erfolgreich!\nMöchten Sie den Ordner jetzt öffnen?"):
                self.open_output_folder()
        else:
            self.status_var.set("❌ Aktion fehlgeschlagen. Details im Verlauf.")
            self.log("=========================================")
            self.log("❌ FEHLER: Aktion konnte nicht abgeschlossen werden.")
            messagebox.showerror("Fehler", "Die Aktion ist fehlgeschlagen. Bitte überprüfen Sie das Protokoll.")

    # ----------------------------------------------------
    # TAB 3: BATCH BACKTESTER (MT5)
    # ----------------------------------------------------
    def build_backtest_tab(self):
        self.tab_backtest.columnconfigure(0, weight=1)
        self.tab_backtest.columnconfigure(1, weight=1)
        self.tab_backtest.rowconfigure(0, weight=1)

        # Variables specific to backtesting
        self.bt_min_score_var = tk.StringVar(value="50")
        self.bt_symbol_var = tk.StringVar(value="None")
        self.bt_period_var = tk.StringVar(value="None")
        self.bt_from_var = tk.StringVar(value="2025-01-01")
        self.bt_to_var = tk.StringVar(value="2026-06-01")
        self.bt_limit_var = tk.StringVar(value="")
        self.bt_model_var = tk.StringVar(value="1 minute OHLC")

        # Left Column: Configuration Card
        left_frame = ttk.Frame(self.tab_backtest, padding=(10, 10, 5, 10))
        left_frame.grid(row=0, column=0, sticky="nsew")
        left_frame.columnconfigure(0, weight=1)
        left_frame.rowconfigure(0, weight=1)

        card_left = ttk.Frame(left_frame, style="Card.TFrame", padding=15)
        card_left.grid(row=0, column=0, sticky="nsew")
        card_left.columnconfigure(0, weight=1)

        ttk.Label(card_left, text="Backtest Einstellungen", style="Title.TLabel").pack(anchor="w")
        ttk.Label(card_left, text="Filter & Parameter für MetaTrader 5", style="Sub.TLabel").pack(anchor="w", pady=(0, 10))
        ttk.Separator(card_left, orient="horizontal").pack(fill="x", pady=(0, 15))

        form = ttk.Frame(card_left, style="InnerCard.TFrame")
        form.pack(fill="both", expand=True)
        form.columnconfigure(0, weight=1)

        # Filters
        ttk.Label(form, text="Mindest-Score im Dashboard:", font=("Segoe UI", 9, "bold"), background="#ffffff").pack(anchor="w", pady=(2, 2))
        ttk.Entry(form, textvariable=self.bt_min_score_var).pack(fill="x", pady=(0, 5))

        ttk.Label(form, text="Erzwinge Währungspaar (Symbol):", font=("Segoe UI", 9, "bold"), background="#ffffff").pack(anchor="w", pady=(2, 2))
        self.bt_symbol_cb = ttk.Combobox(form, textvariable=self.bt_symbol_var, state="readonly")
        self.bt_symbol_cb["values"] = ["None", "EURUSD", "XAUUSD", "GBPUSD", "USDJPY", "AUDCAD", "AUDCHF", "AUDJPY", "AUDNZD", "AUDUSD", "CADCHF", "CADJPY", "EURAUD", "EURCHF", "EURGBP", "EURJPY", "GBPCHF", "GBPJPY", "NZDJPY", "NZDUSD", "USDCAD", "USDCHF", "XAGUSD", "XAUUSD", "XTIUSD"]
        self.bt_symbol_cb.pack(fill="x", pady=(0, 5))

        ttk.Label(form, text="Erzwinge Zeiteinheit (Period):", font=("Segoe UI", 9, "bold"), background="#ffffff").pack(anchor="w", pady=(2, 2))
        self.bt_period_cb = ttk.Combobox(form, textvariable=self.bt_period_var, state="readonly")
        self.bt_period_cb["values"] = ["None", "M1", "M5", "M15", "M30", "H1", "H4", "D1"]
        self.bt_period_cb.pack(fill="x", pady=(0, 5))

        # Dates
        dates_frame = ttk.Frame(form, style="InnerCard.TFrame")
        dates_frame.pack(fill="x", pady=(5, 5))
        dates_frame.columnconfigure(0, weight=1)
        dates_frame.columnconfigure(1, weight=1)

        ttk.Label(dates_frame, text="Startdatum (YYYY-MM-DD):", font=("Segoe UI", 9, "bold"), background="#ffffff").grid(row=0, column=0, sticky="w")
        ttk.Entry(dates_frame, textvariable=self.bt_from_var, width=15).grid(row=1, column=0, sticky="w", pady=(2, 0))

        ttk.Label(dates_frame, text="Enddatum (YYYY-MM-DD):", font=("Segoe UI", 9, "bold"), background="#ffffff").grid(row=0, column=1, sticky="w")
        ttk.Entry(dates_frame, textvariable=self.bt_to_var, width=15).grid(row=1, column=1, sticky="w", pady=(2, 0))

        # Model & Limit
        params_frame = ttk.Frame(form, style="InnerCard.TFrame")
        params_frame.pack(fill="x", pady=(5, 5))
        params_frame.columnconfigure(0, weight=1)
        params_frame.columnconfigure(1, weight=1)

        ttk.Label(params_frame, text="Tick-Modell:", font=("Segoe UI", 9, "bold"), background="#ffffff").grid(row=0, column=0, sticky="w")
        self.bt_model_cb = ttk.Combobox(params_frame, textvariable=self.bt_model_var, state="readonly", width=20)
        self.bt_model_cb["values"] = ["Every tick", "1 minute OHLC", "Open price only", "Every tick (real ticks)"]
        self.bt_model_cb.grid(row=1, column=0, sticky="w", pady=(2, 0))

        ttk.Label(params_frame, text="Limitierung (Max Runs):", font=("Segoe UI", 9, "bold"), background="#ffffff").grid(row=0, column=1, sticky="w")
        ttk.Entry(params_frame, textvariable=self.bt_limit_var, width=10).grid(row=1, column=1, sticky="w", pady=(2, 0))

        # Button Scan
        self.btn_bt_scan = tk.Button(
            card_left,
            text="🔍  1. Roboter scannen & auflisten",
            bg="#1a73e8",
            fg="#ffffff",
            activebackground="#1557b0",
            activeforeground="#ffffff",
            bd=0,
            pady=8,
            font=("Segoe UI", 10, "bold"),
            command=self.scan_backtest_candidates,
            cursor="hand2"
        )
        self.btn_bt_scan.pack(fill="x", side="bottom", pady=(10, 0))

        # Right Column: Candidates Card
        right_frame = ttk.Frame(self.tab_backtest, padding=(5, 10, 10, 10))
        right_frame.grid(row=0, column=1, sticky="nsew")
        right_frame.columnconfigure(0, weight=1)
        right_frame.rowconfigure(0, weight=1)

        card_right = ttk.Frame(right_frame, style="Card.TFrame", padding=15)
        card_right.grid(row=0, column=0, sticky="nsew")
        card_right.columnconfigure(0, weight=1)
        card_right.rowconfigure(3, weight=1) # Listbox gets row weight

        ttk.Label(card_right, text="Kandidaten zur Auswertung", style="Title.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(card_right, text="Wählen Sie EAs aus, die Sie backtesten möchten", style="Sub.TLabel").grid(row=1, column=0, sticky="w", pady=(0, 10))
        ttk.Separator(card_right, orient="horizontal").grid(row=2, column=0, sticky="ew", pady=(0, 10))

        # Listbox for candidates
        list_container = ttk.Frame(card_right, style="InnerCard.TFrame")
        list_container.grid(row=3, column=0, sticky="nsew", pady=(0, 10))
        list_container.columnconfigure(0, weight=1)
        list_container.rowconfigure(0, weight=1)

        self.candidate_listbox = tk.Listbox(
            list_container, 
            selectmode="multiple", 
            font=("Segoe UI", 10), 
            bg="#f9fafb", 
            fg="#374151",
            highlightcolor="#1a73e8", 
            highlightthickness=1, 
            bd=0
        )
        self.candidate_listbox.grid(row=0, column=0, sticky="nsew")

        scrollbar = ttk.Scrollbar(list_container, orient="vertical", command=self.candidate_listbox.yview)
        self.candidate_listbox.configure(yscrollcommand=scrollbar.set)
        scrollbar.grid(row=0, column=1, sticky="ns")

        # Select buttons
        btn_select_frame = ttk.Frame(card_right, style="InnerCard.TFrame")
        btn_select_frame.grid(row=4, column=0, sticky="ew", pady=(0, 10))
        
        self.btn_select_all = ttk.Button(btn_select_frame, text="Alle auswählen", style="Secondary.TButton", command=self.select_all_candidates)
        self.btn_select_all.pack(side="left", padx=(0, 5))

        self.btn_deselect_all = ttk.Button(btn_select_frame, text="Auswahl aufheben", style="Secondary.TButton", command=self.deselect_all_candidates)
        self.btn_deselect_all.pack(side="left")

        # Start button
        self.btn_run_backtest = tk.Button(
            card_right,
            text="▶  2. Batch-Backtest starten",
            bg="#10b981",
            fg="#ffffff",
            activebackground="#059669",
            activeforeground="#ffffff",
            bd=0,
            pady=8,
            font=("Segoe UI", 10, "bold"),
            command=self.start_batch_backtests,
            state="disabled",
            cursor="hand2"
        )
        self.btn_run_backtest.grid(row=5, column=0, sticky="ew")
        # Show Results button
        self.btn_show_results = tk.Button(
            card_right,
            text="📊  3. Backtest-Ergebnisse anzeigen",
            bg="#3b82f6",
            fg="#ffffff",
            activebackground="#2563eb",
            activeforeground="#ffffff",
            bd=0,
            pady=8,
            font=("Segoe UI", 10, "bold"),
            command=self.show_backtest_results,
            cursor="hand2"
        )
        self.btn_show_results.grid(row=6, column=0, sticky="ew", pady=(10, 0))        # Info text explaining what the batch backtester does
        info_text = (
            "💡 Was macht dieser Button?\n"
            "1. Erstellt eine Konfiguration (batch_config.json) für alle ausgewählten EAs.\n"
            "2. Startet den Java-Backtester, welcher EAs & Presets (.set) kopiert.\n"
            "3. Führt MetaTrader 5 für alle Währungs-/Zeiteinheiten im Hintergrund aus.\n"
            "4. Liest Testergebnisse (Profit, Drawdown) in eine H2-Datenbank ein."
        )
        self.lbl_bt_info = ttk.Label(
            card_right,
            text=info_text,
            font=("Segoe UI", 8, "italic"),
            foreground="#4b5563",
            justify="left",
            wraplength=340
        )
        self.lbl_bt_info.grid(row=7, column=0, sticky="w", pady=(12, 0))
        # Candidates state
        self.candidates_data = []

    def select_all_candidates(self):
        for i in range(self.candidate_listbox.size()):
            self.candidate_listbox.select_set(i)

    def deselect_all_candidates(self):
        self.candidate_listbox.selection_clear(0, tk.END)

    def determine_symbols_list(self, pairs_str):
        if not pairs_str:
            return ["EURUSD"]
        pairs_upper = pairs_str.upper()
        
        # Check for general keywords
        if any(k in pairs_upper for k in ["HAUPTWÄHRUNG", "FOREX", "MAJOR", "HAUPTPAARE", "FX"]):
            return ["EURUSD", "GBPUSD", "USDJPY"]
            
        matched = []
        for sym in [
            "AUDCAD", "AUDCHF", "AUDJPY", "AUDNZD", "AUDUSD",
            "CADCHF", "CADJPY", "EURAUD", "EURCHF", "EURGBP",
            "EURJPY", "EURUSD", "GBPCHF", "GBPJPY", "GBPUSD",
            "NZDJPY", "NZDUSD", "USDCAD", "USDCHF", "USDJPY",
            "XAGUSD", "XAUUSD", "XTIUSD"
        ]:
            if sym in pairs_upper:
                matched.append(sym)
        if not matched:
            if "GOLD" in pairs_upper:
                return ["XAUUSD"]
            return ["EURUSD"]
        return matched

    def determine_periods_list(self, timeframe_str):
        if not timeframe_str:
            return ["M15"]
        timeframe_upper = timeframe_str.upper()
        matched = []
        for tf in ["M1", "M5", "M15", "M30", "H1", "H4", "D1"]:
            if tf in timeframe_upper:
                matched.append(tf)
        if not matched:
            return ["M15"]
        return matched

    def scan_backtest_candidates(self):
        try:
            min_score = int(self.bt_min_score_var.get())
        except ValueError:
            messagebox.showerror("Fehler", "Mindest-Score muss eine Zahl sein.")
            return

        self.log("[*] Scanne Dashboard-Datenbank für Backtest-Kandidaten...")
        try:
            robots = load_backtest_robots_from_db(PROJECT_ROOT)
        except Exception as e:
            messagebox.showerror("Fehler", f"Fehler beim Lesen der Dashboard-Datenbank:\n{e}\n\nBitte zuerst das Dashboard aktualisieren.")
            return

        self.candidates_data = []
        self.candidate_listbox.delete(0, tk.END)

        for r in robots:
            if r.get("score", 0) < min_score:
                continue
            if "scam" in str(r.get("risk", "")).lower():
                continue

            exec_path, set_path = resolve_backtest_assets(PROJECT_ROOT, r)
            if not exec_path:
                continue

            ext_info = "MT5" if exec_path.suffix.lower() == ".ex5" else "MT4"

            run_symbols = determine_backtest_symbols(r.get("pairs"))
            run_periods = determine_backtest_periods(r.get("timeframe"))

            self.candidates_data.append({
                "id": r["id"],
                "name": f"{r['name']} ({ext_info})",
                "score": r["score"],
                "expert_path": str(exec_path.resolve()),
                "set_file_path": str(set_path.resolve()) if set_path else "",
                "symbols": run_symbols,
                "periods": run_periods
            })

        if not self.candidates_data:
            self.status_var.set("⚠️ Keine EAs mit .ex5- oder .ex4-Dateien gefunden.")
            self.btn_run_backtest.configure(state="disabled")
            self.log("[-] Keine EAs mit EX5- oder EX4-Dateien gefunden.")
            messagebox.showinfo("Scanner", "Keine EAs mit .ex5- oder .ex4-Dateien für die Kriterien gefunden.")
            return

        for idx, c in enumerate(self.candidates_data):
            set_info = " (+ Set)" if c["set_file_path"] else ""
            symbols_str = ", ".join(c["symbols"])
            periods_str = ", ".join(c["periods"])
            self.candidate_listbox.insert(
                tk.END, 
                f"{c['name']} (Score: {c['score']}) - [{symbols_str}] @ [{periods_str}]{set_info}"
            )
            self.candidate_listbox.select_set(idx)

        self.btn_run_backtest.configure(state="normal")
        self.status_var.set(f"🔍 {len(self.candidates_data)} Kandidaten gefunden. Bitte wählen und Backtest starten.")
        self.log(f"[+] {len(self.candidates_data)} MT4/MT5-Kandidaten gefunden und gelistet.")
    def start_batch_backtests(self):
        if self.extraction_running:
            return

        selected_indices = self.candidate_listbox.curselection()
        if not selected_indices:
            messagebox.showerror("Fehler", "Bitte wählen Sie mindestens einen Roboter aus der Liste aus.")
            return

        from_date = self.bt_from_var.get().strip()
        to_date = self.bt_to_var.get().strip()
        limit_str = self.bt_limit_var.get().strip()
        forced_symbol = self.bt_symbol_var.get()
        forced_period = self.bt_period_var.get()
        model_name = self.bt_model_var.get()

        model_map = {
            "Every tick": 0,
            "1 minute OHLC": 1,
            "Open price only": 2,
            "Every tick (real ticks)": 4
        }
        model_int = model_map.get(model_name, 1)

        runs = []
        for idx in selected_indices:
            c = self.candidates_data[idx]
            run_symbols = [forced_symbol] if forced_symbol != "None" else c["symbols"]
            run_periods = [forced_period] if forced_period != "None" else c["periods"]
            
            for sym in run_symbols:
                for prd in run_periods:
                    runs.append({
                        "expert_name": f"{c['name']}_{sym}_{prd}",
                        "expert_path": c["expert_path"],
                        "symbol": sym,
                        "period": prd,
                        "set_file_path": c["set_file_path"]
                    })

        if limit_str:
            try:
                limit = int(limit_str)
                runs = runs[:limit]
            except ValueError:
                pass

        backtester_root = get_backtester_root(PROJECT_ROOT)
        batch_config = {
            "output_directory": str((backtester_root / "backtest_reports" / "batch_runs").resolve()),
            "settings": {
                "from_date": from_date,
                "to_date": to_date,
                "deposit": 10000,
                "currency": "USD",
                "leverage": "1:100",
                "model": model_int,
                "use_virtual_desktop": True,
                "auto_kill_mt5": True
            },
            "runs": runs
        }

        config_path = PROJECT_ROOT / "batch_config.json"
        try:
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(batch_config, f, indent=2)
            self.log(f"[+] Konfiguration geschrieben nach: {config_path}")
        except Exception as e:
            messagebox.showerror("Fehler", f"Konnte Konfigurationsdatei nicht schreiben: {e}")
            return

        self.lock_gui_for_run()

        self.log("=== BATCH-BACKTEST AUS GUI GESTARTET ===")
        self.log(f"Anzahl EAs: {len(runs)}")
        self.log(f"Testzeitraum: {from_date} bis {to_date}")
        self.log("-----------------------------------------")

        thread = threading.Thread(
            target=self.run_backtest_thread,
            args=(config_path, backtester_root),
            daemon=True
        )
        thread.start()

    def show_backtest_results(self):
        try:
            self.log("[*] Aktualisiere Backtest-Ergebnis-Dashboard...")
            sys.path.append(str(PROJECT_ROOT / "src"))
            import generate_backtest_dashboard
            generate_backtest_dashboard.main()
            
            report_file = PROJECT_ROOT / "report" / "backtest_results.html"
            if report_file.exists():
                self.log(f"[+] Öffne {report_file.name} im Standardbrowser.")
                os.startfile(report_file)
            else:
                messagebox.showerror("Fehler", "Dashboard-Datei nicht gefunden.")
        except Exception as e:
            self.log(f"[-] Fehler beim Generieren des Dashboards: {e}")
            messagebox.showerror("Fehler", f"Fehler beim Generieren des Dashboards: {e}")

    def run_backtest_thread(self, config_path, backtester_root):
        backtester_target = backtester_root / "target"
        
        if not backtester_target.exists():
            self.log("[!] Target-Verzeichnis nicht gefunden. Bitte zuerst das Java-Projekt bauen.")
            self.root.after(0, lambda: self.on_extraction_finished(False))
            return

        jars = list(backtester_target.glob("mt5-backtester-*.jar"))
        if not jars:
            self.log("[!] Kein compiled JAR im target-Verzeichnis gefunden.")
            self.root.after(0, lambda: self.on_extraction_finished(False))
            return

        jar_path = jars[0].resolve()
        self.log(f"[*] Verwende Backtester-JAR: {jar_path}")

        cmd = ["java", "-jar", str(jar_path), "--cli", str(config_path)]
        self.log(f"[>] Startbefehl: {' '.join(cmd)}")

        success = False
        try:
            import subprocess
            process = subprocess.Popen(
                cmd, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.STDOUT, 
                text=True, 
                encoding="utf-8", 
                errors="replace",
                bufsize=1, 
                cwd=str(backtester_root)
            )

            for line in process.stdout:
                self.log(line.strip())

            process.wait()
            success = (process.returncode == 0)

        except Exception as e:
            self.log(f"[-] Fehler beim Ausführen des Backtests: {e}")
        
        self.root.after(0, lambda: self.on_extraction_finished(success))


if __name__ == "__main__":
    root = tk.Tk()
    app = ExtractorGUI(root)
    root.mainloop()
