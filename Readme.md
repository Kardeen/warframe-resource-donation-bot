# 🛰️ Warframe Clan Vault Management Framework

A standalone desktop control interface panel built with Python, PyQt6, and `pystray`. It hosts an asynchronous background Discord bot that orchestrates text strings and OCR captures, syncing clan donations instantly into a centralized Google Sheets ledger ecosystem.

---

## 📁 1. System Component File Architecture Map

| File Asset | System Type | Operational Responsibility |
| :--- | :--- | :--- |
| `gui_app.py` | PyQt6 Interface | **Application Entry Point.** Handles the 3-tab layout panels, self-healing missing file validation routines, thread isolation, system stream logging redirects, and tray minimization. |
| `bot.py` | discord.py Client | **The Gateway Broker.** Oversees live text scanning loops, regex extractions, and administrative command processors while continuously pulling dynamic configuration syncs from memory. |
| `extract_wiki.py` | BeautifulSoup4 Scraper | **Headless Dynamic Scraper.** Runs automatically on startup to scrape the official Warframe Wiki's Lua data module blocks to instantly patch and rebuild your localized item whitelist. |
| `pyproject.toml` | Poetry Manifest | **Dependency Controller.** Locks package boundaries, separates development-only builds, and targets the exact python ecosystem criteria (`>=3.13, <3.16`). |
| `config.json` | JSON Storage Model | **The Source of Truth.** Created dynamically on first boot. Contains runtime connection endpoints, tokens, and channel ID parameters. |
| `warframe_resources.txt` | Flat Text Database | **The Local Whitelist.** A line-separated list of items used by the bot's internal Levenshtein distance fuzzy-matching algorithm to cleanly scrub typos out of text streams. |

---

## 🎮 2. Functional Bot Capabilities & Examples

### A. Dynamic Public Donation Tracker Stream Logging
The bot actively evaluates incoming text signals inside your assigned public donation channel. It breaks down multi-item sentences, fixes typos using the whitelist, and forwards structured objects upstream.

#### **Discord Input Example:**
```text
@VaultBot Donated 1250 oxium and 5 morphicss
```

#### **System Dashboard Processing Log:**
```text
[PASS 1 PARSE] Isolated text segments: ['1250 oxium', '5 morphicss']
[PASS 2 FUZZY] Matched 'morphicss' ➔ 'Morphics' (Match Score: 93%)
[PASS 3 API] Pushing JSON payload data upstream to Google Webapp Endpoint Script...
```

### B. Administrative Timeline Sync (`!sync`)

Scans back through previous text blocks to capture mentions missed while your desktop dashboard app was closed or offline. This prevents missing items without causing duplicates.

* **Admin Usage Example:** `!sync 250`

### C. Analytical Vault Audit Reporting (`!clanstatus`)
Queries the Google Spreadsheet ledger database live to output analytical reports inside your secure admin channel. 

* **Per-User Breakdown Mode (Default)**: Omitting the `global` flag breaks down resource aggregates *individually* for every single user matching your filters.
* **Global Aggregation Mode**: Appending `global` collapses all individual user records, summing everything up into a single *clan-wide total*.

> ⚠️ **Mutual Exclusion Rule:** You must choose between `global` and `player=`. You cannot use them together in the same command line. Specifying a single player profile defeats the purpose of an all-user global aggregation sum, so combining them will result in a syntax validation warning.

Below is the complete permutation matrix demonstrating how to combine these parameters:

| Query Type | Command Layout | Target Analytical Response Matrix |
| :--- | :--- | :--- |
| **All History (Per-User)** | `!clanstatus` | Lists every user in the database alongside their individual lifelong contribution totals. |
| **All History (Global Clan Sum)** | `!clanstatus global` | The true complete audit. Sums up every single transaction across all time into a single collective clan inventory sheet. |
| **Target Player Profile** | `!clanstatus player=TennoMaster` | Isolates historical records matching only that specific username. Displays their personal vault contribution history. |
| **Target Resource (Per-User)** | `!clanstatus resource=Oxium` | Lists every member who has ever donated Oxium, ranked by their personal individual donation sizes. |
| **Target Resource (Global Clan Sum)** | `!clanstatus global resource=Oxium` | Calculates the absolute total amount of Oxium currently logged in the clan vault across all users combined. |
| **Time-Bound Start (Per-User)** | `!clanstatus start=2026-06-01` | Displays an individual performance breakdown for each user, showing only what they donated on or after June 1st, 2026. |
| **Time-Bound Start (Global Clan Sum)** | `!clanstatus global start=2026-06-01` | Sums all vault fluctuations across the entire clan from June 1st, 2026 to today (useful for tracking collective monthly goals). |
| **Date Range Window (Per-User)** | `!clanstatus start=2026-06-01 end=2026-06-15` | Isolates a 15-day window, displaying exactly what each individual member contributed during that specific sprint. |
| **Date Range Window (Global Clan Sum)** | `!clanstatus global start=2026-06-01 end=2026-06-15` | Provides a macro-level audit of all resource changes across the entire clan collectively inside that 15-day block. |
| **Player + Resource Core** | `!clanstatus player=TennoMaster resource=Plastids` | Pinpoints exactly how many Plastids this single player has contributed over their entire history. |
| **Player + Timeframe Window** | `!clanstatus player=ExcaliburPrime start=2026-01-01` | Filters for a specific member and extracts their personalized activity profile since the beginning of the year. |
| **Resource + Start Date (Per-User)** | `!clanstatus resource=Tellurium start=2026-01-01` | Displays a leaderboard of individual members showing how much Tellurium each person has farmed since January 1st. |
| **Resource + Start Date (Global Clan Sum)** | `!clanstatus global resource=Tellurium start=2026-01-01` | Tracks collective clan-wide Tellurium cultivation progress since the start of the year to evaluate long-term research benchmarks. |
| **Resource + Range Window (Per-User)** | `!clanstatus resource=Cryotic start=2026-05-01 end=2026-05-31` | Shows a per-user breakdown of who mined Cryotic during a past monthly cycle (e.g., assessing individual effort during an event). |
| **Resource + Range Window (Global Clan Sum)** | `!clanstatus global resource=Cryotic start=2026-05-01 end=2026-05-31` | Calculates the exact gross amount of Cryotic the entire clan pooled together during that specific month. |
| **Full Matrix (Player Pinpoint)** | `!clanstatus player=TennoMaster resource=Oxium start=2026-06-01 end=2026-06-17` | The ultimate targeted filter. Evaluates how much Oxium a single specific user contributed during this explicit June timeframe. |

### D. Vault Inventory Balancing Tools (`!vaultsync` & `!vaultconsume`)

#### 🔄 `!vaultsync`
Used by administrators to synchronize the spreadsheet with a snapshot of the actual in-game clan vault balances. Instead of logging incremental additions, it overrides or updates the master baseline tab inside your spreadsheet using extracted values.
* **Command Syntax:** `!vaultsync`
* **Context Interaction:** Typically paired with a screenshot attachment of the in-game Dojo Treasury UI page, running it through the backend OCR parser matrix.

#### 📉 `!vaultconsume`
When the clan builds a new Dojo room or replicates research blueprints, resources are subtracted from the vault balances. This command pushes a negative quantity entry upstream to record the deduction.
* **Command Syntax:** `!vaultconsume <quantity> <resource_name>`
* **Usage Examples:**
```text
  !vaultconsume 50000 Polymer Bundle
  !vaultconsume 15 Orokin Cell
```

* **System Action:** Pushes a log entry containing `-50000` or `-15` to the spreadsheet ledger to decrement the live standing balances.

### E. Whitelist Schema Auditing (`!resourcefields`)
An administrative utility used to query the active memory layout of your validation files directly from within Discord. This helps verify that recent wiki syncs or manual edits successfully registered.

* **Access Restriction**: `@commands.has_permissions(administrator=True)` — This command is strictly locked to Discord Server Administrators. If a non-admin user attempts execution, the gateway interface drops the request silently or logs an access violation warning.
* **Command Syntax**: `!resourcefields`

#### Operational Workflow Example:
* **Admin Input:** 
```text
  !resourcefields
```

* **Bot Discord Response:**

```text
  📑 [INTERNAL WHITELIST REGISTRY]
  Active Data Source: warframe_resources.txt
  Total Monitored Fields: 23 Loaded

  Current Matched Schema Enforcements:
  • Alloy Plate       • Argon Crystal     • Circuits          • Control Module
  • Cryotic           • Detonite Ampule   • Ferrite           • Fieldron Sample
  • Gallium           • Hexenon           • Morphics          • Mutagen Sample
  • Nano Spores       • Neural Sensors    • Neurodes          • Orokin Cell
  • Oxium             • Plastids          • Polymer Bundle    • Rubedo
  • Salvage           • Tellurium         • Chromatic Atramentum
```

* **System Design Value**: This eliminates the need to open up the host machine's desktop interface panel or check `warframe_resources.txt` manually to confirm if a newly patched update asset has been successfully added to your bot's parsing dictionary matrix.


---

## 🛠️ 3. Comprehensive Build Pipeline & Compiling Guide

### Step 1: Initialize Your Environment Dependencies

Ensure you have Poetry installed globally on your machine. Open a command prompt inside your project's root directory and run:

```bash
poetry install
```

### Step 2: Executing Your Application Locally

To boot up the interface panel during development, run:

```bash
poetry run python gui_app.py
```

### Step 3: Compiling to a Standalone Windows Executable (.exe)

To package everything into a single, highly portable executable that hides the command prompt window and safely embeds the wiki extraction engine script file internally, execute this build line:

```bash
poetry run pyinstaller --noconsole --onefile --add-data "extract_wiki.py;." --name="Warframe_Vault_System" gui_app.py
```

> ⚠️ **Post-Build Note:** Move the compiled `Warframe_Vault_System.exe` out of your `dist/` folder. It must sit side-by-side with your `extract_wiki.py` file if you want to allow runtime updates, or can run standalone if embedded!

---

## 🌐 4. Cloud Infrastructure Configuration Tutorial

### Step 1: The Discord Developer Portal Setup

1. Open your browser and navigate to the **Discord Developer Portal** (`discord.com/developers/applications`).
2. Click **New Application**, name it (e.g., *Clan Vault Controller*), and click **Create**.
3. Select **Bot** from the left-hand menu sidebar, then click **Reset Token**. Copy this key immediately—this is your private `TOKEN` value needed in your application's settings window.
4. Scroll down on that same page to find **Privileged Gateway Intents**.
5. Toggle **ON** the following options (the bot will crash without these enabled):
* `Presence Intent`
* `Server Members Intent`
* `Message Content Intent` (Crucial for parsing text strings and scanning items)


6. Go to **OAuth2 ➔ URL Generator**. Under *Scopes*, select `bot`. Under *Bot Permissions*, select `View Channels`, `Send Messages`, `Add Reactions`, and `Read Message History`. Copy the generated URL at the bottom and use it to invite your bot into your server.

### Step 2: Google Sheets Tracking Ledger Creation

1. Go to `sheets.google.com` and generate a fresh, completely blank spreadsheet document.
2. Change the workbook's bottom tab sheet layer name from `Sheet1` to exactly: **`DonationLog`**.
3. Set your tracking columns up by placing these labels exactly across Row 1:
* Column A: `Timestamp`
* Column B: `Discord Username`
* Column C: `Resource Name`
* Column D: `Quantity Logged`



### Step 3: Deploying the Google Apps Script Webapp Webhook

1. Inside your new Google Sheet window menu bar, click **Extensions ➔ Apps Script**.
2. Erase the empty template code snippet block entirely and replace it with this dynamic deployment parser:
```javascript
function doPost(e) {
  try {
    var payload = JSON.parse(e.postData.contents);
    var sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName("DonationLog");

    payload.donations.forEach(function(item) {
      sheet.appendRow([
        payload.timestamp,
        payload.username,
        item.resource,
        item.quantity
      ]);
    });

    return ContentService.createTextOutput(JSON.stringify({"status": "success"}))
                         .setMimeType(ContentService.MimeType.JSON);
  } catch(err) {
    return ContentService.createTextOutput(JSON.stringify({"status": "error", "message": err.toString()}))
                         .setMimeType(ContentService.MimeType.JSON);
  }
}
```


3. Click the **Save (Disk icon)** button layout at the top.
4. Click **Deploy ➔ New Deployment**.
5. Click the Gear configuration icon next to "Select type" and pick **Web App**.
6. Set the parameters exactly like this:
* **Execute as:** `Me (Your Google Account Email)`
* **Who has access:** `Anyone` (This allows your desktop app to post logs securely without needing individual authorization screens).


7. Click **Deploy**. Google will pop open a window asking you to verify execution rights. Select *Advanced ➔ Go to Untitled Project (unsafe)* and hit *Allow*.
8. Copy the generated **Web App URL** endpoint. Paste this exact address string directly into your PyQt6 Settings tab screen, commit changes, and start your bot!
