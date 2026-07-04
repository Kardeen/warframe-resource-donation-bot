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
import subprocess

# 🔥 FIX: Safely force standard streams to use UTF-8 if they exist on Windows
if sys.platform == "win32":
    if sys.stdout is not None:
        sys.stdout.reconfigure(encoding="utf-8")
    if sys.stderr is not None:
        sys.stderr.reconfigure(encoding="utf-8")

# --- LOAD/SAVE CONFIGURATION UTILITY ---

CONFIG_FILE = "config.json"
DEFAULT_RESOURCES_FILE = "warframe_resources.txt"

# 🔄 Dynamic path calculation for PyInstaller embedded assets
if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
    # Running inside the compiled PyInstaller .exe bundle environment
    WIKI_SCRAPER_SCRIPT = os.path.join(sys._MEIPASS, "extract_wiki.py")
else:
    # Running locally inside your normal code editor / poetry development environment
    WIKI_SCRAPER_SCRIPT = "extract_wiki.py"

# Absolute safety net list if the wiki script cannot run and no file exists
HARDCODED_RESOURCE_FALLBACK = [
    "35mm Film", 
    "Adramal Alloy", "Advances Debt-Bond", "Aggristone", "Agnovidisc", "Alloy Plate", "Animo Nav Beacon", "Anomaly Shard", "Argon Burger Meal", "Argon Crystal", "Ascaris Prime", "Asterite", "Atmo Systems", "Atramentum", "Ayatan Amber Star", "Ayatan Cyan Star",     "Beating Heartstrings", "Bellow Voca", "Belric Crystal Fragment", "Big Bytes Pizza", "Bile", 
    "Bioplasma", "Biotic Filter", "Biotics", "Blister Stalk", "Blueprint", "Borica", "Bountiful Seed", "Breath Of The Eidolon", "Brilliant Eidolon Shard", 
    "Calda Toroid", "Calx", "Cetus Wisp", "Cheddar Crowns Cereal", "Chitinous Husk", "Chroma Mark", "Chroma Signal", "Chromatic Atramentum", "Chuggin' Along Sixpack", "Circuits", "Condroc Wing", "Connla Sprout", "Control Module", "Corrupted Holokey", "Cortichrome", "Cosmic Specter Regiment", "Credits", "Crisma Toroid", "Cryotic", 
    "Damaged Necramech Casing", "Damaged Necramech Engine", "Damaged Necramech Pod", "Damaged Necramech Weapon Barrel", "Damaged Necramech Weapon Pod", "Damaged Necramech Weapon Receiver", "Damaged Necramech Weapon Stock", "Datum", "Daughter Token", "Defender Insignia", "Devil's Cap", "Dominus Aureus", "Dracroot", "Dull Button", 
    "Echo Voca", "Eevani", "Efervon Sample", "Eidolon Lens", "Eidolon Madurai Lens", "Eidolon Naramon Lens", "Eidolon Shard", "Eidolon Unairu Lens", "Eidolon Vazarin Lens", "Eidolon Zenurik Lens", "Enigma Gyrum", "Entrati Lanthorn", "Entrati Obols", "Entratifragmentbase", "Exalted Mark", "Executive Quittance", "Exemplar Granum Crown", "Experimental Arc-Relay", 
    "Familial Debt-Bond", "Fass Residue", "Fate Pearl", "Father Token", "Fergolyte", "Ferrite", "Ferrofungus", "Flawless Seed", "Flawless Sentient Core", "Focus Lens", "Force Specter Regiment", "Forma", "Frostcap", 
    "Gallium", "Gamma Berry", "Ganglion", "General Insignia", "Generic Dojo Color Pigment", "Genius Datum", "Gorgaricus Spore", "Grandmother Token", "Granum Crown", "Greater Focus Lens", "Greater Madurai Lens", "Greater Naramon Lens", "Greater Unairu Lens", "Greater Vazarin Lens", "Greater Zenurik Lens", "Grokdrul", "Gyromag Systems", 
    "Hexenon", "Honored Mark", "Höllvanian Pitchweave Fragment", 
    "Ignia", "Incubator Power Core", "Infected Palpators", "Insignia", "Intact Sentient Core", "Intriguing Datum", "Iradite", "Ironwood", 
    "Javlok Capacitor", "Judgement Points", 
    "Kavat Genetic Code", "Kovnik", "Kuaka Spinal Claw", "Kullervo's Bane", "Kuva", 
    "Lamentus", "Laudavi", "Lawful Medallion", "Lazulite Toroid", "Lich Token", "Live Heartcell", "Lua Lens", "Lua Madurai Lens", "Lua Naramon Lens", "Lua Thrax Plasm", "Lua Unairu Lens", "Lua Vazarin Lens", "Lua Zenurik Lens", "Lucent Teroglobe", "Lyroic Bridge", 
    "Madurai Lens", "Mandachord", "Mandachord Body", "Mandachord Bridge", "Mandachord Fret", "Maphica", "Maprico", "Mark", "Maxim Medallion", "Medallion", "Medical Debt-Bond", "Mood Crystal", "Morphics", "Mother Token", "Muck Bonnet", "Mutalist Alad V Nav Coordinate", "Mytocardia Spore", 
    "Nano Spores", "Naramon Lens", "Narmer Isoplast", "Nav Coordinate", "Necracoil", "Neural Sensors", "Neurodes", "Nistlepod", "Nitain Extract", "Nonono", "Nullstones", 
    "On-lyne CD", "Orokin Animus Matrix", "Orokin Ballistics Matrix", "Orokin Cell", "Orokin Cipher", "Orokin Monitor", "Orokin Orientation Matrix", "Otak Token", "Oxides", "Oxium", 
    "Partner Quittance", "Pathos Clamp", "Phase Specter Regiment", "Pheromones", "Plastids", "Polymer Bundle", "Proof Fragment", "Pulsating Tubercles", "Pustulite", 
    "Quittance", 
    "Radiant Eidolon Shard", "Rania Crystal Fragment", "Reeking Puffball", "Ren Hypercore", "Repeller Systems", "Riven Sliver", "Riven Transmuter", "Rubedo", "Rune Marrow", 
    "Saggen Pearl", "Salvage", "Scintillant", "Scorched Beacon", "Scuttler Husk", "Seed", "Seriglass Shard", "Servoris", "Severed Bile Sac", "Shelter Debt-Bond", "Shrill Voca", "Silphsela", "Sister Of Parvos Token", "Sisters of Parvos Token", "Sola Toroid", "Somatic Fibers", "Son Token", "Spectral Debris", "Spring Popper", "Steel Essence", "Stela", "Synthetic Eidolon Shard", "Synthetics", "Synthula", 
    "Tasoma Extract", "Techrot Chitin", "Techrot Motherboard", "Tellurium", "Temporal Dust", "Tepa Nodule", "The Countessa Comic", "Thermal Sludge", "Thorn Tooth", "Thrax Plasm", "Thunder-Button", "Ticor Plate", "Titanium", "Training Debt-Bond", 
    "Ueymag", "Unairu Lens", "Universal Medallion", 
    "Vainthorn", "Vapor Specter Regiment", "Vazarin Lens", "Vega Toroid", "Vessel Capillaries", "Vestigial Motes", "Violet's Bane", "Vitus Essence", "Void Traces", "Voidgel Orb", "Voidplume Crest", "Voidplume Down", "Voidplume Pinion", "Voidplume Quill", "Voidplume Vane", "Vome Residue", "Vomval Trumpet", "Vosfor", 
    "Winter Spear", 
    "Yao Shrub", 
    "Zenith Granum Crown", "Zenurik Lens"
]

def load_config():
    """
    Loads config.json. Updates warframe_resources.txt on every startup.
    Falls back to existing data or hardcoded defaults if the script fails.
    """
    # 1. ALWAYS TRY TO UPDATE THE WHITELIST ON STARTUP
    update_successful = False
    
    if os.path.exists(WIKI_SCRAPER_SCRIPT):
        print(f"🌐 [STARTUP] Attempting live update via {WIKI_SCRAPER_SCRIPT}...")
        try:
            # 🔄 CHECK STATE: Are we running inside a frozen PyInstaller .exe?
            if getattr(sys, 'frozen', False):
                print("📦 [STARTUP] Running in compiled mode. Executing embedded scraper natively...")
                import importlib.util
                
                # Dynamically load the embedded extract_wiki.py file
                spec = importlib.util.spec_from_file_location("extract_wiki", WIKI_SCRAPER_SCRIPT)
                wiki_module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(wiki_module)
                
                # Call the main extraction function inside your extract_wiki.py
                if hasattr(wiki_module, 'extract_resources'):
                    wiki_module.extract_resources()
                else:
                    # Fallback if the code isn't wrapped in a function, executing it on import might have already run it
                    pass
                
                update_successful = True
            else:
                # 💻 DEVELOPMENT MODE: Run via subprocess normally
                current_env = os.environ.copy()
                current_env["PYTHONIOENCODING"] = "utf-8"
                
                result = subprocess.run(
                    [sys.executable, WIKI_SCRAPER_SCRIPT], 
                    capture_output=True, 
                    text=True, 
                    check=True,
                    encoding="utf-8",
                    env=current_env
                )
                update_successful = True
            
            # Verify the file was successfully written/updated regardless of the method above
            if os.path.exists(DEFAULT_RESOURCES_FILE) and os.path.getsize(DEFAULT_RESOURCES_FILE) > 0:
                print("✅ [STARTUP] Whitelist successfully updated from the Warframe Wiki.")
                update_successful = True
                
        except subprocess.CalledProcessError as cmd_err:
            print(f"⚠️ [STARTUP] Live update failed (Wiki changed or offline):")
            print(f"--- INTERNAL SCRAPER ERROR STACK --- \n{cmd_err.stderr}------------------------------------")
        except Exception as e:
            print(f"⚠️ [STARTUP] System error executing scraper script: {e}")
    else:
        print(f"ℹ️ [STARTUP] {WIKI_SCRAPER_SCRIPT} not found. Skipping live update loop.")

    # 2. EMERGENCY DRILL: If update failed, make sure we at least have a backup file
    if not update_successful:
        if os.path.exists(DEFAULT_RESOURCES_FILE):
            print(f"📦 [STARTUP] Update failed, but an existing copy of '{DEFAULT_RESOURCES_FILE}' was found. Carrying over old data matrix.")
        else:
            print(f"🚨 [STARTUP] Update failed AND no file exists! Deploying hardcoded fallback configurations...")
            try:
                with open(DEFAULT_RESOURCES_FILE, "w", encoding="utf-8") as rf:
                    rf.write("\n".join(HARDCODED_RESOURCE_FALLBACK) + "\n")
                print("✅ [STARTUP] Emergency default whitelist deployed successfully.")
            except Exception as write_err:
                print(f"❌ [CRITICAL] Failed to write emergency backup definitions to disk: {write_err}")

    # 3. SELF-HEAL LAYER: Ensure Configuration JSON Exists
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
            
    default_blueprint = {
        "TOKEN": "", 
        "WEBAPP_URL": "", 
        "ADMIN_KANAL_ID": 0, 
        "SPENDEN_KANAL_ID": 0, 
        "NUR_IM_SPENDENKANAL": True, 
        "RESOURCES_FILE": DEFAULT_RESOURCES_FILE,
        "AUTO_LEADERBOARD_CHANNEL_ID": 0,
        "AUTO_LEADERBOARD_DAY": "Monday"
    }
    
    save_config(default_blueprint)
    print(f"⚙️ [INITIALIZATION] Created clean template configuration file matrix at '{CONFIG_FILE}'.")
    return default_blueprint

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
        self.leaderboard_chan_input = QLineEdit(str(self.config["AUTO_LEADERBOARD_CHANNEL_ID"]))
        self.leaderboard_day_input = QLineEdit(self.config.get("AUTO_LEADERBOARD_DAY", "Monday"))
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
        settings_layout.addWidget(QLabel("🏆 **Automated Leaderboard Channel ID:**"))
        settings_layout.addWidget(self.leaderboard_chan_input)
        settings_layout.addWidget(QLabel("📅 **Automated Leaderboard Post Day (e.g., Monday, Sunday):**"))
        settings_layout.addWidget(self.leaderboard_day_input)
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
                <li><b>!leaderboard [week/month/year/all] [resource=Name]</b> - Renders visual competitive leaderboards sorted by contribution.</li>
                <li><b>!correct [Resource=Amount]</b> - Reply directly to a bot status message to update records dynamically in place.</li>
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
            self.config["AUTO_LEADERBOARD_CHANNEL_ID"] = int(self.leaderboard_chan_input.text().strip())
            self.config["AUTO_LEADERBOARD_DAY"] = self.leaderboard_day_input.text().strip().capitalize()
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