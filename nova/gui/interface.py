"""
Kapitel 17 – GUI / Interface

Tkinter-basierte grafische Benutzeroberfläche für Nova.
Fällt auf Konsolenmodus zurück, wenn Tkinter nicht verfügbar ist.
"""

from __future__ import annotations

import logging
import queue
import threading
from typing import Optional

logger = logging.getLogger(__name__)

try:
    import tkinter as tk
    from tkinter import scrolledtext, ttk
    _TK_AVAILABLE = True
except ImportError:
    _TK_AVAILABLE = False
    logger.info("Tkinter nicht verfügbar – GUI deaktiviert.")


class NovaGUI:
    """
    Tkinter-GUI für Nova.

    Features:
    - Chat-Verlauf mit Farbkodierung (Nutzer / Nova)
    - Eingabefeld mit Enter-Senden
    - Status-Leiste (Modus, Emotion)
    - Sprachausgabe-Toggle
    """

    def __init__(self, nova) -> None:
        self._nova = nova
        self._root: Optional[tk.Tk] = None
        self._message_queue: queue.Queue = queue.Queue()

    # ------------------------------------------------------------------
    # GUI starten
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Startet die GUI (blockierend) oder fällt auf Konsole zurück."""
        if not _TK_AVAILABLE:
            logger.warning("GUI nicht verfügbar. Starte Konsolenmodus.")
            self._nova.main_loop.run()
            return

        self._root = tk.Tk()
        self._root.title("Nova – Persönlicher KI-Assistent")
        self._root.geometry("700x520")
        self._root.configure(bg="#1e1e2e")
        self._root.resizable(True, True)

        self._build_ui()
        self._root.after(100, self._process_message_queue)
        self._root.protocol("WM_DELETE_WINDOW", self._on_close)
        self._root.mainloop()

    # ------------------------------------------------------------------
    # UI aufbauen
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        root = self._root

        # --- Kopfzeile ---
        header = tk.Frame(root, bg="#313244", height=48)
        header.pack(fill=tk.X)
        tk.Label(
            header, text="🌟 Nova",
            font=("Segoe UI", 16, "bold"),
            fg="#cdd6f4", bg="#313244",
        ).pack(side=tk.LEFT, padx=16, pady=8)

        self._status_var = tk.StringVar(value="Bereit | Modus: normal")
        tk.Label(
            header, textvariable=self._status_var,
            font=("Segoe UI", 10),
            fg="#a6adc8", bg="#313244",
        ).pack(side=tk.RIGHT, padx=16)

        # --- Chat-Bereich ---
        chat_frame = tk.Frame(root, bg="#1e1e2e")
        chat_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        self._chat_display = scrolledtext.ScrolledText(
            chat_frame,
            wrap=tk.WORD,
            font=("Segoe UI", 11),
            bg="#181825",
            fg="#cdd6f4",
            insertbackground="#cdd6f4",
            relief=tk.FLAT,
            state=tk.DISABLED,
            padx=10,
            pady=10,
        )
        self._chat_display.pack(fill=tk.BOTH, expand=True)
        self._chat_display.tag_config("user", foreground="#89b4fa")
        self._chat_display.tag_config("nova", foreground="#a6e3a1")
        self._chat_display.tag_config("system", foreground="#6c7086")

        # --- Eingabebereich ---
        input_frame = tk.Frame(root, bg="#1e1e2e")
        input_frame.pack(fill=tk.X, padx=8, pady=(0, 8))

        self._input_var = tk.StringVar()
        self._input_field = tk.Entry(
            input_frame,
            textvariable=self._input_var,
            font=("Segoe UI", 12),
            bg="#313244",
            fg="#cdd6f4",
            insertbackground="#cdd6f4",
            relief=tk.FLAT,
        )
        self._input_field.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=8, padx=(0, 8))
        self._input_field.bind("<Return>", self._on_send)
        self._input_field.focus()

        send_btn = tk.Button(
            input_frame,
            text="Senden",
            font=("Segoe UI", 11),
            bg="#89b4fa",
            fg="#1e1e2e",
            activebackground="#74c7ec",
            relief=tk.FLAT,
            padx=16,
            command=self._on_send,
        )
        send_btn.pack(side=tk.RIGHT, ipady=8)

        # Begrüßung
        self._append_message("system", "Nova ist bereit. Wie kann ich dir helfen?")

    # ------------------------------------------------------------------
    # Nachrichten
    # ------------------------------------------------------------------

    def _on_send(self, event=None) -> None:
        text = self._input_var.get().strip()
        if not text:
            return
        self._input_var.set("")
        self._append_message("user", f"Du: {text}")

        # Verarbeitung in eigenem Thread
        threading.Thread(
            target=self._process_user_input,
            args=(text,),
            daemon=True,
        ).start()

    def _process_user_input(self, text: str) -> None:
        response = self._nova.main_loop.process(text)
        self._message_queue.put(("nova", f"Nova: {response}"))
        # Status aktualisieren
        mode = self._nova.mode_manager.name
        emotion = self._nova.emotion.current_label
        self._message_queue.put(("status", f"{emotion} | Modus: {mode}"))

    def _process_message_queue(self) -> None:
        try:
            while True:
                msg_type, content = self._message_queue.get_nowait()
                if msg_type == "status":
                    self._status_var.set(content)
                else:
                    self._append_message(msg_type, content)
        except queue.Empty:
            pass
        if self._root:
            self._root.after(100, self._process_message_queue)

    def _append_message(self, tag: str, text: str) -> None:
        self._chat_display.configure(state=tk.NORMAL)
        self._chat_display.insert(tk.END, text + "\n\n", tag)
        self._chat_display.configure(state=tk.DISABLED)
        self._chat_display.see(tk.END)

    # ------------------------------------------------------------------
    # Lebenszyklus
    # ------------------------------------------------------------------

    def _on_close(self) -> None:
        self._nova.shutdown()
        if self._root:
            self._root.destroy()
