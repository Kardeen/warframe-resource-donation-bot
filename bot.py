import os
import re
import requests
import discord
from discord.ext import commands
import easyocr
from rapidfuzz import process, fuzz
import json

def sync_global_config():
    """Reads config.json and forces the global variables to update to the latest GUI values."""
    global WEBAPP_URL, ADMIN_KANAL_ID, SPENDEN_KANAL_ID, NUR_IM_SPENDENKANAL
    
    config = get_live_config()
    WEBAPP_URL = config["WEBAPP_URL"]
    ADMIN_KANAL_ID = config["ADMIN_KANAL_ID"]
    SPENDEN_KANAL_ID = config["SPENDEN_KANAL_ID"]
    NUR_IM_SPENDENKANAL = config["NUR_IM_SPENDENKANAL"]

# --- NEW CONFIGURATION LOADER ---
def get_live_config():
    with open("config.json", "r") as f:
        return json.load(f)

config = get_live_config()

# Read running values instantly from file properties layout
WEBAPP_URL = config["WEBAPP_URL"]
ADMIN_KANAL_ID = config["ADMIN_KANAL_ID"]
SPENDEN_KANAL_ID = config["SPENDEN_KANAL_ID"]
NUR_IM_SPENDENKANAL = config["NUR_IM_SPENDENKANAL"]

RESOURCES_FILE = config.get("RESOURCES_FILE", "warframe_resources.txt")
RESOURCE_WHITELIST = []

# Inside your functions, whenever you read channels dynamically or want runtime updates, 
# you can re-call get_live_config() or let the bot restart to take full config changes!

if os.path.exists(RESOURCES_FILE):
    with open(RESOURCES_FILE, "r", encoding="utf-8") as f:
        RESOURCE_WHITELIST = [line.strip() for line in f if line.strip()]
    print(f"✅ Whitelist Engine: Loaded {len(RESOURCE_WHITELIST)} official resources.")
else:
    print(f"⚠️ WARNING: '{RESOURCES_FILE}' not found! Run your extraction script first.")

# --- INITIALIZE ENGINES ---
print("📥 Loading OCR Models (English)...")
# 'en' loads English. You can add languages later like ['en', 'de', 'fr']
reader = easyocr.Reader(['en'], gpu=False) 
print("🚀 OCR Engine ready!")

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# --- HELPER FUNCTIONS ---

def clean_and_validate_ocr(raw_text_lines, threshold=75):
    """
    Two-Pass Hybrid Parser:
    Pass 1: Scans for exact matches or explicit shorthand words from the whitelist.
    Pass 2: Uses fuzzy matching on remaining text chunks for OCR typos/misspellings.
    Finally: Binds each discovered item to its closest preceding unclaimed number.
    """
    detected_items = []
    
    # Merge lines into a single normalized text stream
    combined_text = " ".join(raw_text_lines)
    combined_text = re.sub(r'\s+', ' ', combined_text).strip()
    
    print(f"\n--- [PARSER DEBUG: TWO-PASS HYBRID ENGINE] ---")
    print(f"Stream: '{combined_text}'\n------------------------------------------------")

    # Sort whitelist by length descending to check longer names first
    sorted_whitelist = sorted(RESOURCE_WHITELIST, key=len, reverse=True)
    
    # Track which text positions (indices) and number values have been claimed
    claimed_text_ranges = [] # list of (start_idx, end_idx)
    claimed_number_positions = set()

    def is_text_claimed(start, end):
        return any(s < end and start < e for s, e in claimed_text_ranges)

    # =========================================================================
    # PASS 1: EXACT MATCHING & EXPLICIT SHORTHAND (Case-Insensitive)
    # =========================================================================
    for official_item in sorted_whitelist:
        item_words = official_item.split()
        
        # Look for the exact full name (Using re.IGNORECASE)
        pattern_full = rf'\b{re.escape(official_item)}\b'
        for match in re.finditer(pattern_full, combined_text, re.IGNORECASE):
            start, end = match.start(), match.end()
            
            if not is_text_claimed(start, end):
                preceding_text = combined_text[max(0, start - 30):start]
                num_matches = list(re.finditer(r'\b\d+\b', preceding_text))
                
                if num_matches:
                    closest_num = num_matches[-1]
                    global_num_pos = max(0, start - 30) + closest_num.start()
                    
                    if global_num_pos not in claimed_number_positions:
                        detected_items.append({"amount": int(closest_num.group()), "item": official_item})
                        claimed_number_positions.add(global_num_pos)
                        claimed_text_ranges.append((start, end))
                        print(f"[PASS 1 EXACT] Found: '{official_item}' -> Amount: {closest_num.group()}")

        # Look for distinct first-word shorthand if it's a long item name
        if len(item_words) > 1 and len(item_words[0]) > 4:
            pattern_short = rf'\b{re.escape(item_words[0])}\b'
            for match in re.finditer(pattern_short, combined_text, re.IGNORECASE):
                start, end = match.start(), match.end()
                
                if not is_text_claimed(start, end):
                    preceding_text = combined_text[max(0, start - 30):start]
                    num_matches = list(re.finditer(r'\b\d+\b', preceding_text))
                    
                    if num_matches:
                        closest_num = num_matches[-1]
                        global_num_pos = max(0, start - 30) + closest_num.start()
                        
                        if global_num_pos not in claimed_number_positions:
                            detected_items.append({"amount": int(closest_num.group()), "item": official_item})
                            claimed_number_positions.add(global_num_pos)
                            claimed_text_ranges.append((start, end))
                            print(f"[PASS 1 SHORTHAND] Found: '{official_item}' (via '{item_words[0]}') -> Amount: {closest_num.group()}")

    # =========================================================================
    # PASS 2: FUZZY FALLBACK (Case-Insensitive Typos & Multi-Word Items)
    # =========================================================================
    UI_WORD_BLACKLIST = ["dojo", "cancel", "ok", "refunded", "contribution", "contributions", "never", "sure"]

    words = combined_text.split(" ")
    unclaimed_words = []
    current_char_pos = 0

    for word in words:
        word_len = len(word)
        word_start = current_char_pos
        word_end = word_start + word_len
        current_char_pos = word_end + 1

        if is_text_claimed(word_start, word_end):
            continue

        clean_word = re.sub(r'^\d+\s*[xX]?\s*|\b\d+\b|[.,;:!]', '', word).strip()
        if clean_word.lower() in UI_WORD_BLACKLIST or len(clean_word) < 3:
            continue
            
        unclaimed_words.append((clean_word, word_start))

    # Fuzzy match each leftover word against the whitelist
    for clean_word, word_start in unclaimed_words:
        if any(d['item'] == clean_word for d in detected_items):
            continue

        best_match = None
        best_score = 0

        # FIX: We loop through the whitelist and lowercase everything during the score check
        # to force rapidfuzz.fuzz.partial_ratio to ignore casing entirely.
        for official_item in sorted_whitelist:
            # Calculate the partial ratio score on purely lowercased versions of both strings
            score = fuzz.partial_ratio(clean_word.lower(), official_item.lower())
            
            adjusted_threshold = threshold if len(clean_word) > 4 else 85
            
            if score >= adjusted_threshold and score > best_score:
                # Secondary validation: confirm a high character overlap ratio
                token_score = fuzz.token_set_ratio(clean_word.lower(), official_item.lower())
                if token_score >= 40:
                    best_score = score
                    best_match = official_item # Keep the pristine, correctly capitalized master name!

        if best_match:
            preceding_text = combined_text[max(0, word_start - 30):word_start]
            num_matches = list(re.finditer(r'\b\d+\b', preceding_text))
            
            if num_matches:
                closest_num = num_matches[-1]
                global_num_pos = max(0, word_start - 30) + closest_num.start()
                
                if global_num_pos not in claimed_number_positions:
                    detected_items.append({"amount": int(closest_num.group()), "item": best_match})
                    claimed_number_positions.add(global_num_pos)
                    print(f"[PASS 2 FUZZY SUCCESS] Matched typo/variant '{clean_word}' ➔ '{best_match}' ({best_score:.1f}%)")

    return detected_items

# --- BOT EVENTS ---

@bot.event
async def on_ready():
    print(f"🤖 {bot.user.name} is online and operational!")

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    
    # 🔄 Refresh all global variables right before processing anything
    sync_global_config()

    # Check if the bot is allowed to process messages in this channel
    if not NUR_IM_SPENDENKANAL or message.channel.id == SPENDEN_KANAL_ID:
        
        # Trigger processing if the bot is explicitly mentioned
        if bot.user.mentioned_in(message):
            raw_lines_to_process = []
            status_msg = None

            # --- PATH A: HANDLE TEXT MESSAGE CONTENT ---
            clean_text = re.sub(r'<@!?\d+>', '', message.content).strip()
            
            if clean_text:
                # Note: If you want to use the streamlined stream parsing we built earlier,
                # you can change this to just: raw_lines_to_process.append(clean_text)
                text_lines = re.split(r'[,;\n]', clean_text)
                raw_lines_to_process.extend([line.strip() for line in text_lines if line.strip()])

            # --- PATH B: HANDLE IMAGE ATTACHMENTS ---
            if message.attachments:
                for attachment in message.attachments:
                    filename = attachment.filename.lower()
                    if filename.endswith(('.png', '.jpg', '.jpeg', '.webp')):
                        if not status_msg:
                            status_msg = await message.channel.send("🔄 Processing data (Image OCR engine active)...")
                        
                        try:
                            image_bytes = await attachment.read()
                            ocr_results = reader.readtext(image_bytes, detail=0)
                            raw_lines_to_process.extend(ocr_results)
                        except Exception as e:
                            print(f"OCR Error: {str(e)}")

            # --- PROCESSING LAYER ---
            if raw_lines_to_process:
                if not status_msg:
                    status_msg = await message.channel.send("🔄 Processing your text entry...")

                verified_donations = clean_and_validate_ocr(raw_lines_to_process)
                
                if not verified_donations:
                    await status_msg.edit(content="⚠️ No valid Warframe resources or amounts recognized in your input.")
                    return

                # Send clean package to Google Sheets
                # FIX: Add the "timestamp" parameter right here inside the dictionary payload layout
                payload = {
                    "action": "log",
                    "username": str(message.author.name),
                    "donations": verified_donations,
                    "timestamp": message.created_at.isoformat()  # <-- ADDED
                }
                
                try:
                    response = requests.post(WEBAPP_URL, json=payload)
                    if response.status_code == 200 and response.json().get("status") == "success":
                        
                        # FIX: Slap the checkmark onto the player's message instantly
                        await message.add_reaction("✅")
                        
                        details = "\n".join([f"▫️ {d['amount']}x {d['item']}" for d in verified_donations])
                        await status_msg.edit(content=f"✅ **Donation registered!**\n👤 Player: {message.author.name}\n{details}")
                    else:
                        # Optional: slap a cross on it if Google breaks down
                        await message.add_reaction("❌")
                        await status_msg.edit(content="❌ Data processing failed at Google Sheets layer.")
                except Exception as e:
                    await message.add_reaction("❌")
                    await status_msg.edit(content=f"❌ Network Error connecting to Google: {str(e)}")

    # Allow standard prefix commands (!clanstatus, !sync) to still process properly
    await bot.process_commands(message)

# --- BOT COMMANDS ---

@bot.command(name="sync")
@commands.has_permissions(administrator=True)
async def sync_missed_donations(ctx, limit: int = 100):
    """
    Admin Command: Executed in Admin Channel, but scans and processes 
    unhandled bot pings directly from the public Donation Channel.
    """
    # 1. Enforce strict Admin Channel usage guard lock
    if ctx.channel.id != ADMIN_KANAL_ID:
        await ctx.send("⛔ This system synchronization command can only be executed inside the secure Admin Channel.")
        return

    # 2. Safely grab the public Donation Channel object from Discord's cache
    donation_channel = bot.get_channel(SPENDEN_KANAL_ID)
    if not donation_channel:
        await ctx.send("❌ Error: Could not locate the target Donation Channel. Verify SPENDEN_KANAL_ID configuration.")
        return

    status_msg = await ctx.send(f"🔄 Interrogating timeline history inside <#{SPENDEN_KANAL_ID}> for missed player pings...")

    processed_count = 0
    logged_lines_count = 0

    # 3. Read history backward specifically from the donation tracking channel
    async for message in donation_channel.history(limit=limit):
        # Skip bot responses completely
        if message.author.bot:
            continue

        # RULE: Check if this bot was explicitly tagged in the donation channel
        if bot.user in message.mentions:
            # Duplicate Guard: skip if it already sports our confirmation green checkmark
            has_check = any(r.emoji == "✅" for r in message.reactions)
            if has_check:
                continue 

            raw_lines = []
            if message.content:
                raw_lines.append(message.content)

            if message.attachments:
                for attachment in message.attachments:
                    if any(attachment.filename.lower().endswith(ext) for ext in ['.png', '.jpg', '.jpeg', '.webp']):
                        try:
                            img_bytes = await attachment.read()
                            ocr_text = reader.readtext(img_bytes, detail=0)
                            raw_lines.extend(ocr_text)
                        except Exception as e:
                            print(f"[CROSS-SYNC OCR FAILED] Message ID {message.id}: {e}")

            if raw_lines:
                # Run the text stream through your case-insensitive hybrid engine
                detected_items = clean_and_validate_ocr(raw_lines)

                if detected_items:
                    payload = {
                        "action": "log", 
                        "username": str(message.author.name),
                        "donations": detected_items,
                        "timestamp": message.created_at.isoformat() # FIX: Pass original time for history sync too!
                    }

                    try:
                        response = requests.post(WEBAPP_URL, json=payload)
                        if response.status_code == 200 and response.json().get("status") == "success":
                            # Add the checkmark directly onto the user's message in the donation channel!
                            await message.add_reaction("✅")
                            processed_count += 1
                            logged_lines_count += len(detected_items)
                        else:
                            await message.add_reaction("❌")
                    except Exception as err:
                        print(f"[CROSS-SYNC POST ERROR] {err}")
                        break

    # 4. Return the summary analysis back to the Admin Channel
    if processed_count > 0:
        await status_msg.edit(content=f"✅ **Cross-Channel Sync Complete!**\nScanned <#{SPENDEN_KANAL_ID}>: Processed **{processed_count}** missed pings and updated **{logged_lines_count}** inventory entries.")
    else:
        await status_msg.edit(content=f"🔍 Timeline check inside <#{SPENDEN_KANAL_ID}> complete. No unprocessed pings discovered within the last {limit} messages.")

@bot.command(name="clanstatus")
@commands.has_permissions(administrator=True)
async def clan_status(ctx, *, args: str = None):
    """
    Advanced Inventory Status Query with explicit flags.
    Syntax Examples:
      !clanstatus global oxides
      !clanstatus player=laury oxides start=2026-06-01
    """
    if ctx.channel.id != ADMIN_KANAL_ID:
        await ctx.send("⛔ This command can only be executed in the secure Admin Channel.")
        return

    # --- 1. PARAMETER EXTRACTION ENGINE ---
    target = "player"
    player_filter = None
    resource_filter = None
    start_date = None
    end_date = None

    if args:
        # Check for mutual exclusion upfront
        if "global" in args.lower() and "player=" in args.lower():
            await ctx.send("❌ **Invalid Parameter Conflict**: You cannot request a `global` summation summary while filtering for a specific individual `player=` simultaneously.")
            return

        # Extract explicit key-value parameters using regex patterns
        start_match = re.search(r'start=(\d{4}-\d{2}-\d{2})', args, re.IGNORECASE)
        end_match = re.search(r'end=(\d{4}-\d{2}-\d{2})', args, re.IGNORECASE)
        player_match = re.search(r'player=([^\s]+)', args, re.IGNORECASE) # Captures up to the next space
        
        if start_match: start_date = start_match.group(1)
        if end_match: end_date = end_match.group(1)
        if player_match: player_filter = player_match.group(1).strip()

        # Clean all explicit tokens completely out of the string arguments
        clean_args = re.sub(r'(start|end)=\d{4}-\d{2}-\d{2}', '', args, flags=re.IGNORECASE)
        clean_args = re.sub(r'player=[^\s]+', '', clean_args, flags=re.IGNORECASE).strip()
        
        words = clean_args.split()

        if words:
            # Check and strip global flag
            if "global" in [w.lower() for w in words]:
                target = "global"
                words = [w for w in words if w.lower() != "global"]

            # Remaining unflagged text MUST be the resource name!
            if words:
                remaining_phrase = " ".join(words).strip()
                match = process.extractOne(remaining_phrase, RESOURCE_WHITELIST, scorer=fuzz.WRatio)
                if match and match[1] >= 75:
                    resource_filter = match[0]
                    print(f"[ADMIN FUZZY MATCH] Mapped input '{remaining_phrase}' to asset '{resource_filter}' ({match[1]:.1f}%)")

    # --- 2. QUERY LAYER DISPATCH ---
    status_msg = await ctx.send("🛰️ Interrogating vault database engine metrics...")

    params = {"target": target}
    if resource_filter: params["resource"] = resource_filter
    if player_filter: params["player"] = player_filter
    if start_date: params["start"] = start_date
    if end_date: params["end"] = end_date

    try:
        response = requests.get(WEBAPP_URL, params=params, timeout=15)
        if response.status_code == 200:
            res_data = response.json()
            
            if res_data.get("status") == "success" and res_data.get("data"):
                payload_data = res_data["data"]
                
                # Header formatting
                header = f"📊 **Clan Donation Report Summary** (`Target: {target.upper()}`)\n"
                if start_date or end_date:
                    header += f"📅 Window: `{start_date or 'Beginning'} ➔ {end_date or 'Present'}`\n"
                if resource_filter:
                    header += f"🔍 Resource Filter: `{resource_filter}`\n"
                if player_filter:
                    header += f"👤 Player Filter: `{player_filter}`\n"
                header += "—" * 40 + "\n"

                report = [header]

                if target == "global":
                    for item, total in payload_data.items():
                        report.append(f"📦 Total **{total}x {item}** donated.")
                else:
                    for player, items in payload_data.items():
                        item_strings = [f"**{amount}x {item}**" for item, amount in items.items()]
                        if item_strings:
                            report.append(f"👤 `{player}`: {', '.join(item_strings)}")

                final_text = "\n".join(report)
                if len(final_text) > 2000:
                    await status_msg.edit(content="⚠️ Output too massive to display over Discord. Reduce date windows.")
                else:
                    await status_msg.edit(content=final_text)
            else:
                await status_msg.edit(content=f"🔍 No records matched your search parameters.")
        else:
            await status_msg.edit(content=f"❌ Network Error. HTTP Status: {response.status_code}")
    except Exception as e:
        await status_msg.edit(content=f"❌ Script error executing search: {str(e)}")

@bot.command(name="resourcefields")
@commands.has_permissions(administrator=True)
async def resource_fields(ctx, *, search_term: str = None):
    """
    Helper method: Lists valid resource filters.
    If search_term is provided, it searches the Master Whitelist.
    If no term is provided, it dynamically polls Google Sheets for what has *actually* been donated via ?action=list.
    """
    if ctx.channel.id != ADMIN_KANAL_ID:
        await ctx.send("⛔ This utility method is restricted to the Admin Channel.")
        return

    # Option A: User provided a keyword search -> Check the local file
    if search_term:
        search_term = search_term.strip()
        matches = [item for item in RESOURCE_WHITELIST if search_term.lower() in item.lower()]
        
        if not matches:
            await ctx.send(f"❌ No official Warframe resource contains the phrase text: `{search_term}`")
            return
            
        output = [f"🔍 **Matching Master Whitelist Keywords for '{search_term}':**", "—" * 40]
        output.extend([f"▫️ {item}" for item in matches[:30]]) # Cap at 30 to prevent spam
        if len(matches) > 30:
            output.append(f"\n*...and {len(matches) - 30} more exact matches.*")
            
        await ctx.send("\n".join(output))
        return

    # Option B: No parameter -> Use your NEW action=list code to see what's currently in the sheet!
    status_msg = await ctx.send("📡 Fetching active logged resources from Google Sheets...")
    try:
        response = requests.get(f"{WEBAPP_URL}?action=list", timeout=15)
        if response.status_code == 200:
            res_data = response.json()
            
            if res_data.get("status") == "success" and res_data.get("resources"):
                active_resources = res_data["resources"]
                
                output = ["📋 **Currently Logged Resources inside Spreadsheet:**", "—" * 40]
                output.extend([f"▫️ {r}" for r in active_resources])
                output.append(f"\n💡 *Tip: Use `!clanstatus [Item Name]` to filter the overview report for any of these!*")
                
                await status_msg.edit(content="\n".join(output))
            else:
                await status_msg.edit(content="📦 The spreadsheet does not contain any valid recorded resource rows yet.")
        else:
            await status_msg.edit(content="❌ Failed to retrieve resource list from Google Sheets.")
    except Exception as e:
        await status_msg.edit(content=f"❌ Network Error: {str(e)}")

@bot.command(name="vaultsync")
@commands.has_permissions(administrator=True)
async def vault_sync(ctx):
    """
    Overwrites the 'Inventory' tab balances using a master snapshot image attachment or manual list.
    """
    if ctx.channel.id != ADMIN_KANAL_ID:
        await ctx.send("⛔ This inventory command is restricted to the Admin Channel.")
        return

    if not ctx.message.attachments:
        await ctx.send("⚠️ Please attach a snapshot image of your current Dojo Vault screen balance rows.")
        return

    status_msg = await ctx.send("🔄 Running OCR baseline evaluation scan on Vault screenshot...")
    
    try:
        attachment = ctx.message.attachments[0]
        image_bytes = await attachment.read()
        
        # Feed through your exact same high-precision state machine text parser!
        ocr_results = reader.readtext(image_bytes, detail=0)
        verified_balances = clean_and_validate_ocr(ocr_results)
        
        if not verified_balances:
            await status_msg.edit(content="⚠️ No valid Warframe materials or amounts recognized in this vault image.")
            return

        # Package payload with the 'sync' action command
        payload = {
            "action": "sync",
            "donations": verified_balances
        }
        
        response = requests.post(WEBAPP_URL, json=payload)
        if response.status_code == 200 and response.json().get("status") == "success":
            lines = [f"▫️ **{d['item']}** set to balance: `{d['amount']}`" for d in verified_balances]
            await status_msg.edit(content=f"✅ **Vault Inventory Sync Complete!**\n\n" + "\n".join(lines))
        else:
            await status_msg.edit(content="❌ Inventory sync update request failed at the Spreadsheet layer.")
            
    except Exception as e:
        await status_msg.edit(content=f"❌ Script error running baseline sync: {str(e)}")


@bot.command(name="vaultconsume")
@commands.has_permissions(administrator=True)
async def vault_consume(ctx, *, message_content: str):
    """
    Deducts materials from the live Inventory sheet tab.
    Syntax: !vaultconsume 5000 Salvage, 10 Oxium
    """
    if ctx.channel.id != ADMIN_KANAL_ID:
        await ctx.send("⛔ This inventory command is restricted to the Admin Channel.")
        return

    status_msg = await ctx.send("🔄 Evaluating material consumption text parameters...")
    
    # Pass text through the clean_and_validate_ocr function to translate shorthand strings
    parsed_lines = [message_content]
    deductions = clean_and_validate_ocr(parsed_lines)
    
    if not deductions:
        await status_msg.edit(content="⚠️ Could not process any matching resource deduction terms. Check item spelling syntax.")
        return

    # Package payload with the 'consume' action command
    payload = {
        "action": "consume",
        "donations": deductions
    }
    
    try:
        response = requests.post(WEBAPP_URL, json=payload)
        if response.status_code == 200 and response.json().get("status") == "success":
            lines = [f"📉 Subtracted **{d['amount']}x** away from **{d['item']}** stock lines." for d in deductions]
            await status_msg.edit(content=f"✅ **Vault Inventory Consumption Logged!**\n\n" + "\n".join(lines))
        else:
            await status_msg.edit(content="❌ Consumption update request failed at the Spreadsheet layer.")
    except Exception as e:
        await status_msg.edit(content=f"❌ Network transmission error: {str(e)}")

# --- LAUNCH ---
if __name__ == "__main__":
    # This only runs if you execute 'python test_bot.py' manually via terminal
    live_config = get_live_config()
    bot.run(live_config["TOKEN"])