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
    Scans raw OCR text blocks for patterns like '31 x Cryotic' or '10 Credits'.
    Cross-references resource names with the local whitelist using fuzzy matching.
    """
    detected_items = []
    
    # --- DEBUGGING LOGS ---
    print("\n--- [OCR DEBUG: RAW DETECTED LINES] ---")
    for idx, line in enumerate(raw_text_lines):
        print(f"Line {idx}: '{line}'")
    print("---------------------------------------\n")
    # ----------------------

    # EasyOCR fix: Clean spaces and stitch lines together into one big block
    # We replace multiple spaces or weird line breaks around 'x' to help regex catch it
    combined_text = "\n".join(raw_text_lines)
    
    # Pattern 1: Standard Items (e.g., "31 x Cryotic" or "5000 x Alloy Plate")
    regex_items = re.findall(r'(\d+)\s*[xX]\s*([^|$\n\(\)]+)', combined_text)
    for amount, raw_name in regex_items:
        raw_name = raw_name.strip()
        
        # Skip garbage UI matches
        if any(word in raw_name.lower() for word in ["direct vault", "donation", "credits", "cancel"]):
            continue
            
        # Fuzzy Match against our whitelist
        match = process.extractOne(raw_name, RESOURCE_WHITELIST, scorer=fuzz.WRatio)
        if match:
            matched_name, confidence, _ = match
            if confidence >= threshold:
                detected_items.append({"amount": int(amount), "item": matched_name})
                print(f"[MATCH SUCCESS] Found Item: {amount}x {matched_name} (Confidence: {confidence:.1f}%)")
            else:
                print(f"[MATCH REJECTED] Found '{raw_name}' but match to '{matched_name}' was too low ({confidence:.1f}%)")

    # Pattern 2: Vault Credits confirmation screen (e.g., "10 Credits to your CLAN Vault")
    regex_credits = re.search(r'(\d+)\s*credits', combined_text, re.IGNORECASE)
    if regex_credits:
        credit_amount = regex_credits.group(1)
        detected_items.append({"amount": int(credit_amount), "item": "Credits"})
        print(f"[MATCH SUCCESS] Found Credits: {credit_amount}x Credits")

    return detected_items

# --- BOT EVENTS ---

@bot.event
async def on_ready():
    print(f"🤖 {bot.user.name} is online and operational!")

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    # Filter live processing by channel
    if not NUR_IM_SPENDENKANAL or message.channel.id == SPENDEN_KANAL_ID:
        if bot.user.mentioned_in(message) and message.attachments:
            for attachment in message.attachments:
                filename = attachment.filename.lower()
                if filename.endswith(('.png', '.jpg', '.jpeg', '.webp')):
                    
                    status_msg = await message.channel.send("🔄 Local OCR engine is reading image pixels...")
                    
                    try:
                        # 1. Download image into system memory bytes
                        image_bytes = await attachment.read()
                        
                        # 2. Execute Local OCR Extraction
                        ocr_results = reader.readtext(image_bytes, detail=0) # detail=0 returns just raw string lines
                        
                        # 3. Clean and run Whitelist validation filter
                        verified_donations = clean_and_validate_ocr(ocr_results)
                        
                        if not verified_donations:
                            await status_msg.edit(content="⚠️ No valid Warframe resources detected in this image layout.")
                            continue
                        
                        # 4. Prepare clear payload package for Google Sheets
                        payload = {
                            "username": str(message.author.name),
                            "donations": verified_donations # Sending a clean array structure
                        }
                        
                        response = requests.post(WEBAPP_URL, json=payload)
                        
                        if response.status_code == 200 and response.json().get("status") == "success":
                            details = "\n".join([f"▫️ {d['amount']}x {d['item']}" for d in verified_donations])
                            await status_msg.edit(content=f"✅ **Donation registered via Local OCR!**\n👤 Player: {message.author.name}\n{details}")
                        else:
                            await status_msg.edit(content="❌ Data processing failed at Google Sheets layer.")
                            
                    except Exception as e:
                        await status_msg.edit(content=f"❌ OCR Runtime Error: {str(e)}")

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

# --- LAUNCH ---
bot.run(TOKEN)