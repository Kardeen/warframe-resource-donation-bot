import os
import re
import requests
import discord
from discord.ext import commands
import easyocr
from rapidfuzz import process, fuzz
from dotenv import dotenv_values

# --- CONFIGURATION ---
secrets = dotenv_values(".env")

TOKEN = secrets["TOKEN"]
WEBAPP_URL = secrets["WEBAPP_URL"]

# Channel Restrictions
ADMIN_KANAL_ID = 1516160408170528791    # Replace with your Admin Channel ID
SPENDEN_KANAL_ID = 1516100470584643586  # Replace with your Spenden Channel ID
NUR_IM_SPENDENKANAL = True

# Whitelist Config
RESOURCES_FILE = "warframe_resources.txt"
RESOURCE_WHITELIST = []

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
    # PASS 1: EXACT MATCHING & EXPLICIT SHORTHAND
    # =========================================================================
    for official_item in sorted_whitelist:
        item_words = official_item.split()
        
        # Look for the exact full name
        pattern_full = rf'\b{re.escape(official_item)}\b'
        for match in re.finditer(pattern_full, combined_text, re.IGNORECASE):
            start, end = match.start(), match.end()
            
            if not is_text_claimed(start, end):
                # Bind to closest number
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
    # PASS 2: FUZZY FALLBACK (For OCR Typos on remaining unclaimed words)
    # =========================================================================
    # Words we want to explicitly ignore so they never trigger false fuzzy matches
    UI_WORD_BLACKLIST = ["dojo", "cancel", "ok", "refunded", "contribution", "contributions", "never", "sure"]

    words = combined_text.split(" ")
    current_char_pos = 0

    for i, word in enumerate(words):
        word_len = len(word)
        word_start = current_char_pos
        word_end = word_start + word_len
        current_char_pos = word_end + 1

        if is_text_claimed(word_start, word_end):
            continue

        clean_word = re.sub(r'^\d+\s*[xX]?\s*|\b\d+\b|[.,;:!]', '', word).strip()
        
        # FIX: Skip the word entirely if it matches something on our UI noise blacklist
        if clean_word.lower() in UI_WORD_BLACKLIST or len(clean_word) < 4:
            continue

        # Fuzzy match continues down here safely...
        match = process.extractOne(clean_word, sorted_whitelist, scorer=fuzz.WRatio)
        if match:
            matched_name, confidence, _ = match
            if confidence >= threshold:
                # Check if we already registered this item type in Pass 1
                if not any(d['item'] == matched_name for d in detected_items):
                    
                    # Look backward for an unclaimed number
                    preceding_text = combined_text[max(0, word_start - 30):word_start]
                    num_matches = list(re.finditer(r'\b\d+\b', preceding_text))
                    
                    if num_matches:
                        closest_num = num_matches[-1]
                        global_num_pos = max(0, word_start - 30) + closest_num.start()
                        
                        if global_num_pos not in claimed_number_positions:
                            detected_items.append({"amount": int(closest_num.group()), "item": matched_name})
                            claimed_number_positions.add(global_num_pos)
                            claimed_text_ranges.append((word_start, word_end))
                            print(f"[PASS 2 FUZZY] Matched '{clean_word}' to '{matched_name}' ({confidence:.1f}%) -> Amount: {closest_num.group()}")

    return detected_items

# --- BOT EVENTS ---

@bot.event
async def on_ready():
    print(f"🤖 {bot.user.name} is online and operational!")

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    # Check if the bot is allowed to process messages in this channel
    if not NUR_IM_SPENDENKANAL or message.channel.id == SPENDEN_KANAL_ID:
        
        # Trigger processing if the bot is explicitly mentioned
        if bot.user.mentioned_in(message):
            raw_lines_to_process = []
            status_msg = None

            # --- PATH A: HANDLE TEXT MESSAGE CONTENT ---
            # Remove the bot's mention tag (e.g., <@123456789>) so it doesn't mess up parsing
            clean_text = re.sub(r'<@!?\d+>', '', message.content).strip()
            
            if clean_text:
                # Split the text message by commas, semicolons, or newlines 
                # This lets users type: "10x Salvage, 500 Credits, 10x Cryotic"
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

                # Run the exact same validation engine!
                verified_donations = clean_and_validate_ocr(raw_lines_to_process)
                
                if not verified_donations:
                    await status_msg.edit(content="⚠️ No valid Warframe resources or amounts recognized in your input.")
                    return

                # Send clean package to Google Sheets
                payload = {
                    "username": str(message.author.name),
                    "donations": verified_donations
                }
                
                try:
                    response = requests.post(WEBAPP_URL, json=payload)
                    if response.status_code == 200 and response.json().get("status") == "success":
                        details = "\n".join([f"▫️ {d['amount']}x {d['item']}" for d in verified_donations])
                        await status_msg.edit(content=f"✅ **Donation registered!**\n👤 Player: {message.author.name}\n{details}")
                    else:
                        await status_msg.edit(content="❌ Data processing failed at Google Sheets layer.")
                except Exception as e:
                    await status_msg.edit(content=f"❌ Network Error connecting to Google: {str(e)}")

    # Allow standard prefix commands (!clanstatus, !sync) to still process properly
    await bot.process_commands(message)

# --- BOT COMMANDS ---

@bot.command(name="sync")
@commands.has_permissions(administrator=True)
async def sync_history(ctx):
    """Processes historical channel messages using local Python OCR, ignoring already confirmed segments."""
    status_msg = await ctx.send("🔄 Analyzing channel history for missing donations...")
    
    letzte_bot_nachricht = None
    verpasste_nachrichten = []
    
    async for message in ctx.channel.history(limit=200):
        if message.author == bot.user and "Analyzing" not in message.content:
            letzte_bot_nachricht = message
            break

    if letzte_bot_nachricht:
        async for message in ctx.channel.history(after=letzte_bot_nachricht, limit=100, oldest_first=True):
            if message.attachments and message.author != bot.user:
                verpasste_nachrichten.append(message)
    else:
        async for message in ctx.channel.history(limit=50, oldest_first=True):
            if message.attachments and message.author != bot.user:
                verpasste_nachrichten.append(message)

    if not verpasste_nachrichten:
        await status_msg.edit(content="✨ System up to date. No unprocessed layouts found.")
        return

    await status_msg.edit(content=f"📦 Found {len(verpasste_nachrichten)} pending layout instances. Running OCR queue...")
    
    success_count = 0
    for message in verpasste_nachrichten:
        for attachment in message.attachments:
            if attachment.filename.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
                try:
                    img_data = await attachment.read()
                    lines = reader.readtext(img_data, detail=0)
                    verified = clean_and_validate_ocr(lines)
                    
                    if verified:
                        payload = {"username": str(message.author.name), "donations": verified}
                        res = requests.post(WEBAPP_URL, json=payload)
                        if res.status_code == 200 and res.json().get("status") == "success":
                            success_count += 1
                            await ctx.send(f"✅ Synced legacy entry from **{message.author.name}**.")
                except Exception as e:
                    print(f"Sync skip on item error: {str(e)}")

    await ctx.send(f"🏁 Sync cycle finalized. {success_count} item packages recorded.")

# --- ADMIN & UTILITY COMMANDS ---

@bot.command(name="clanstatus")
@commands.has_permissions(administrator=True)
async def clan_status(ctx, *, filter_option: str = None):
    """
    Queries aggregated clan donations. 
    Applies local fuzzy matching to shorthand inputs before requesting from Google Sheets.
    """
    if ctx.channel.id != ADMIN_KANAL_ID:
        await ctx.send("⛔ This command can only be executed in the secure Admin Channel.")
        return

    status_msg = await ctx.send("🛰️ Querying aggregated Google Sheets database...")

    url = WEBAPP_URL
    cleaned_filter = None

    if filter_option:
        filter_option = filter_option.strip()
        
        # 1. Fuzzy match the user's input against your perfect resource file
        match = process.extractOne(filter_option, RESOURCE_WHITELIST, scorer=fuzz.WRatio)
        
        if match:
            matched_name, confidence, _ = match
            # If the match is solid (score >= 70), overwrite the shorthand with the official name
            if confidence >= 70:
                cleaned_filter = matched_name
                print(f"[ADMIN FUZZY MATCH] Mapped '{filter_option}' to '{cleaned_filter}' ({confidence:.1f}%)")
            else:
                # If confidence is low, assume they might be filtering by a player name instead
                cleaned_filter = filter_option
        else:
            cleaned_filter = filter_option

        # 2. Append the cleaned resource/player asset name to the URL query string
        url += f"?resource={requests.utils.quote(cleaned_filter)}"

    try:
        response = requests.get(url, timeout=15)
        if response.status_code == 200:
            res_data = response.json()
            
            if res_data.get("status") == "success" and res_data.get("data"):
                overview_dict = res_data["data"]
                
                # Format report header using the clean name returned by Google or our fallback
                display_filter = res_data.get('filteredResource') or cleaned_filter or 'None'
                filter_text = f" (Filter: `{display_filter}`)" if res_data.get("filterActive") else ""
                
                report = [
                    f"📊 **Clan Donation Overview Report**{filter_text}\n" + "—" * 40
                ]
                
                for player, items in overview_dict.items():
                    item_strings = [f"**{amount}x {item}**" for item, amount in items.items()]
                    report.append(f"👤 `{player}`: {', '.join(item_strings)}")
                
                final_text = "\n".join(report)
                if len(final_text) > 2000:
                    await status_msg.edit(content="⚠️ Data summary is too large to fit in a Discord message. Check the Sheet directly!")
                else:
                    await status_msg.edit(content=final_text)
            else:
                # Provide a helpful error if it found nothing
                await status_msg.edit(content=f"🔍 No aggregated records found matching filter: `{cleaned_filter}`")
        else:
            await status_msg.edit(content=f"❌ Database error. HTTP Status: {response.status_code}")
            
    except Exception as e:
        await status_msg.edit(content=f"❌ Script connection error: {str(e)}")

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

# --- LAUNCH ---
bot.run(TOKEN)