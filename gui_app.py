import sys
import os
import json
import asyncio
import threading
import re
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QLabel, QLineEdit, QCheckBox, QPushButton, QTabWidget, QTextEdit
)
from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtGui import QIcon, QAction
import pystray
from PIL import Image, ImageDraw

# --- LOAD/SAVE CONFIGURATION UTILITY ---
CONFIG_FILE = "config.json"

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    return {
        "TOKEN": "", "WEBAPP_URL": "", 
        "ADMIN_KANAL_ID": 0, "SPENDEN_KANAL_ID": 0, 
        "NUR_IM_SPENDENKANAL": True, "RESOURCES_FILE": "warframe_resources.txt"
    }

def save_config(config_data):
    with open(CONFIG_FILE, "w") as f:
        json.dump(config_data, f, indent=4)

# --- CUSTOM LOG STREAM INTERCEPTOR ---
class CustomLogStream:
    def __init__(self, signal):
        self.signal = signal

    def write(self, text):
        if text.strip(): # Avoid pushing raw blank newline spacers
            self.signal.emit(text.strip())

    def flush(self):
        pass # Required placeholder for system stream conformity

# --- THREAD WORKER TO RUN DISCORD ASYNCHRONOUSLY ---
class DiscordBotThread(QThread):
    log_signal = pyqtSignal(str)
    finished_signal = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.loop = None

    def run(self):
        self.log_signal.emit("🤖 Loading configuration matrix...")
        config = load_config()
        
        if not config["TOKEN"]:
            self.log_signal.emit("❌ Error: Missing Bot Token in config.json!")
            self.finished_signal.emit()
            return
            
        try:
            # Intercept standard terminal printing streams
            sys.stdout = CustomLogStream(self.log_signal)
            sys.stderr = CustomLogStream(self.log_signal)
            
            from bot import bot
            self.log_signal.emit("🛰️ Connecting core to Discord gateways...")
            
            # Save a reference to the loop so our stop function can access it
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            self.loop.run_until_complete(bot.start(config["TOKEN"]))
        except Exception as e:
            self.log_signal.emit(f"❌ Engine stopped or disconnected: {str(e)}")
        finally:
            # Restore standard print streams on exit
            sys.stdout = sys.__stdout__
            sys.stderr = sys.__stderr__
            self.finished_signal.emit()

    def stop_gracefully(self):
        if self.loop and self.loop.is_running():
            from bot import bot
            # Inject the close coroutine into the running background loop thread safely
            asyncio.run_coroutine_threadsafe(bot.close(), self.loop)
            self.log_signal.emit("🛑 Sent shutdown signal to Discord connection layers...")

# --- MAIN WINDOW INTERFACE DESIGN ---
class BotDashboard(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Warframe Clan Vault Management System")
        self.resize(650, 450)
        
        self.config = load_config()
        self.bot_thread = None
        
        self.init_ui()
        self.create_tray_icon()
        
    def init_ui(self):
        tabs = QTabWidget()
        self.setCentralWidget(tabs)
        
        # ==========================================
        # TAB 1: CORE CONTROL DASHBOARD
        # ==========================================
        control_tab = QWidget()
        control_layout = QVBoxLayout()
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.append("💡 System Ready. Press 'Start Bot Engine' to initialize channel links.")
        
        # Action Buttons side by side
        btn_layout = QHBoxLayout()
        self.start_btn = QPushButton("🚀 Start Bot Engine")
        self.start_btn.clicked.connect(self.start_bot)
        
        self.stop_btn = QPushButton("🛑 Stop Bot Engine")
        self.stop_btn.setEnabled(False) 
        self.stop_btn.clicked.connect(self.stop_bot)
        
        btn_layout.addWidget(self.start_btn)
        btn_layout.addWidget(self.stop_btn)
        
        control_layout.addWidget(QLabel("📰 **System Engine Status Logs:**"))
        control_layout.addWidget(self.log_output)
        control_layout.addLayout(btn_layout)
        control_tab.setLayout(control_layout)
        
        # ==========================================
        # TAB 2: PARAMETER SETTINGS MANAGER
        # ==========================================
        settings_tab = QWidget()
        settings_layout = QVBoxLayout()
        
        self.token_input = QLineEdit(self.config["TOKEN"])
        self.token_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.url_input = QLineEdit(self.config["WEBAPP_URL"])
        self.admin_chan_input = QLineEdit(str(self.config["ADMIN_KANAL_ID"]))
        self.spend_chan_input = QLineEdit(str(self.config["SPENDEN_KANAL_ID"]))
        self.restrict_cb = QCheckBox("Enforce strict channel lockdown rules (NUR_IM_SPENDENKANAL)")
        self.restrict_cb.setChecked(self.config["NUR_IM_SPENDENKANAL"])
        
        settings_layout.addWidget(QLabel("🔑 **Discord Bot Token:**"))
        settings_layout.addWidget(self.token_input)
        settings_layout.addWidget(QLabel("🌐 **Google Webapp URL Script Endpoint:**"))
        settings_layout.addWidget(self.url_input)
        settings_layout.addWidget(QLabel("🛡️ **Admin Channel ID:**"))
        settings_layout.addWidget(self.admin_chan_input)
        settings_layout.addWidget(QLabel("💰 **Public Donation Tracking Channel ID:**"))
        settings_layout.addWidget(self.spend_chan_input)
        settings_layout.addWidget(self.restrict_cb)
        
        save_btn = QPushButton("💾 Commit Configuration Settings Changes")
        save_btn.clicked.connect(self.commit_settings)
        settings_layout.addWidget(save_btn)
        settings_tab.setLayout(settings_layout)
        
        # ==========================================
        # TAB 3: COMMAND REFERENCE GUIDE
        # ==========================================
        guide_tab = QTextEdit()
        guide_tab.setReadOnly(True)
        guide_tab.setHtml("""
            <h3>📘 Vault Operational Command Matrix Quick-Reference Guide</h3>
            <hr>
            <h4>👥 Public Donation Tracking Channel Rules</h4>
            <ul>
                <li><b>@BotName Donated 1000 oxide</b> - Automatically evaluates inventory text streams, addresses case typos, and aggregates lines to Google Sheets.</li>
                <li><b>@BotName [Attached Image Snapshot]</b> - Processes game UI screenshots using the internal OCR layer.</li>
            </ul>
            <h4>🛡️ Admin Channel Executive Controls</h4>
            <ul>
                <li><b>!sync [limit]</b> - Scans back through public text timelines, isolates historical missed mentions, and updates entries cleanly with historical timestamps.</li>
                <li><b>!vaultsync</b> - Overwrites the master baseline tab in your spreadsheet using a raw screenshot of current in-game numbers.</li>
                <li><b>!vaultconsume [item parameters]</b> - Deducts materials used for room builds/decorations directly from live balance sheets.</li>
                <li><b>!clanstatus [optional filter settings]</b> - Powerful analytical tool. Supports <i>global</i>, <i>player=Name</i>, and date constraints (e.g., <code>start=2026-06-01</code>).</li>
            </ul>
        """)
        
        # Add all tabs cleanly to the central layout matrix
        tabs.addTab(control_tab, "🎮 Core Control Dashboard")
        tabs.addTab(settings_tab, "⚙️ Parameter Matrix Settings")
        tabs.addTab(guide_tab, "📖 Operational Commands Guide")

    def start_bot(self):
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        
        self.bot_thread = DiscordBotThread()
        self.bot_thread.log_signal.connect(self.update_console_log)
        self.bot_thread.finished_signal.connect(self.on_bot_finished)
        self.bot_thread.start()

    def stop_bot(self):
        self.stop_btn.setEnabled(False)
        if self.bot_thread:
            self.bot_thread.stop_gracefully()

    def on_bot_finished(self):
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.log_output.append("🏁 Bot engine thread fully closed. Safe to modify configurations or restart.")

    def update_console_log(self, text):
        self.log_output.append(text)

    def commit_settings(self):
        try:
            self.config["TOKEN"] = self.token_input.text().strip()
            self.config["WEBAPP_URL"] = self.url_input.text().strip()
            self.config["ADMIN_KANAL_ID"] = int(self.admin_chan_input.text().strip())
            self.config["SPENDEN_KANAL_ID"] = int(self.spend_chan_input.text().strip())
            self.config["NUR_IM_SPENDENKANAL"] = self.restrict_cb.isChecked()
            
            save_config(self.config)
            self.update_console_log("💾 System settings applied and saved to config.json.")
        except ValueError:
            self.update_console_log("❌ Error saving settings: Channel IDs must be valid numeric values!")

    # --- MINIMIZE TO SYSTEM TRAY FUNCTIONALITY ---
    def changeEvent(self, event):
        if self.isMinimized():
            self.hide() 
            event.ignore()

    def create_tray_icon(self):
        image = Image.new('RGB', (64, 64), color=(41, 128, 185))
        d = ImageDraw.Draw(image)
        d.text((20, 24), "🚀", fill=(255, 255, 255))
        
        def on_clicked(icon, item):
            if str(item) == "Restore Dashboard Window":
                self.showNormal()
                self.activateWindow()
            elif str(item) == "Shutdown Framework":
                icon.stop()
                QApplication.quit()
                os._exit(0) 

        menu = pystray.Menu(
            pystray.MenuItem("Restore Dashboard Window", on_clicked),
            pystray.MenuItem("Shutdown Framework", on_clicked)
        )
        
        self.tray_icon = pystray.Icon("vault_bot_tray", image, "Warframe Vault Controller", menu)
        threading.Thread(target=self.tray_icon.run, daemon=True).start()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = BotDashboard()
    window.show()
    sys.exit(app.exec())