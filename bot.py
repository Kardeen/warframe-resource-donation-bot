import discord
from discord.ext import commands
import requests  # Neu hinzugefügt für die Verbindung zu Google
import base64  # Neu: Zum Umwandeln des Bildes in Text
from dotenv import dotenv_values

secrets = dotenv_values(".env")

# --- KONFIGURATION ---
TOKEN = secrets["TOKEN"]
WEBAPP_URL = secrets["WEBAPP_URL"]

# Kanaleinstellungen
SPENDEN_KANAL_NAME = "clan-spenden"    # Dein Spendenkanal-Name
NUR_IM_SPENDENKANAL = True             # True = Bot reagiert live NUR im Spendenkanal
                                       # False = Bot reagiert live in JEDEM Kanal
ADMIN_KANAL_ID = 987654321098765432    # <-- ERSETZE DIES MIT DER ID DEINES ADMIN-CHANNELS

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"Bot ist bereit und verknüpft! Name: {bot.user.name}")
    print("--------------------------------------------------")

@bot.event
async def on_message(message):
    # Wichtig: Der Bot soll nicht auf seine eigenen Nachrichten reagieren
    if message.author == bot.user:
        return
    
    # Prüfen, ob der Kanal-Name übereinstimmt
    if NUR_IM_SPENDENKANAL and message.channel.name != SPENDEN_KANAL_NAME:
        return  # Ignoriert alles, was nicht in "clan-spenden" geschrieben wird

    # Prüfen, ob der Bot in der Nachricht erwähnt (getaggt) wurde
    if bot.user.mentioned_in(message):
        
        # Falls ein Bild an der Nachricht hängt, verarbeiten wir es
        if message.attachments:
            for attachment in message.attachments:
                filename = attachment.filename.lower()
                if filename.endswith(('.png', '.jpg', '.jpeg', '.webp')):
                    
                    status_message = await message.channel.send("🔄 Erwähnung erkannt. Verarbeite Bilddaten...")
                    
                    try:
                        # Textinhalt der Nachricht bereinigen (Bot-Tag entfernen)
                        # Wenn du "@Bot 50x Eisen" schreibst, bleibt nur "50x Eisen" übrig
                        zusatz_text = message.clean_content.replace(f"@{bot.user.name}", "").strip()
                        
                        # Bild herunterladen und in Base64 umwandeln
                        image_bytes = await attachment.read()
                        base64_encoded = base64.b64encode(image_bytes).decode('utf-8')
                        
                        # Payload für Google Apps Script
                        payload = {
                            "username": str(message.author.name),
                            "imageBuffer": base64_encoded,
                            "additionalText": zusatz_text  # Wir senden den Text deiner Nachricht mit!
                        }
                        
                        response = requests.post(WEBAPP_URL, json=payload)
                        
                        if response.status_code == 200:
                            res_data = response.json()
                            if res_data.get("status") == "success":
                                details = res_data.get('message', 'Keine Details')
                                await status_message.edit(
                                    content=f"✅ **Spende über Erwähnung registriert!**\n"
                                            f"👤 Spieler: {res_data.get('spieler')}\n"
                                            f"📦 {details}"
                                )
                            else:
                                await status_message.edit(content=f"❌ Google-Fehler: {res_data.get('message')}")
                        else:
                            await status_message.edit(content=f"❌ HTTP-Fehler: {response.status_code}")
                    
                    except Exception as e:
                        await status_message.edit(content=f"❌ Fehler: {str(e)}")
                        
        else:
            # Der Bot wurde getaggt, aber es war kein Bild dabei (nur Text)
            zusatz_text = message.clean_content.replace(f"@{bot.user.name}", "").strip()
            await message.channel.send(f"👋 Hallo {message.author.mention}! Du hast mich getaggt. Ich habe folgenden Text von dir empfangen: *\"{zusatz_text}\"* (Es war aber kein Screenshot angehängt).")

    # WICHTIG: Damit Befehle wie !sync weiterhin funktionieren
    await bot.process_commands(message)

@bot.command(name="sync")
@commands.has_permissions(administrator=True)
async def sync_history(ctx):
    """Sucht nach der letzten Nachricht des Bots und verarbeitet alles, was danach kam."""
    # 1. Schritt: Wir suchen rückwärts nach der letzten Nachricht vom Bot
    # Aber wir merken uns die ID der aktuellen Nachricht, um sie zu ignorieren!
    aktueller_status = await ctx.send("🔄 Analysiere Kanal-Historie auf verpasste Spenden...")
    
    letzte_bot_nachricht = None
    verpasste_nachrichten = []
    
    async for message in ctx.channel.history(limit=200):
        # Die Nachricht muss vom Bot sein, darf aber NICHT die gerade eben gesendete Status-Nachricht sein
        if message.author == bot.user and message.id != aktueller_status.id:
            letzte_bot_nachricht = message
            break # Älteren Anker gefunden -> Stoppen

    # 2. Schritt: Wir holen alle Nachrichten ab, die NACH dieser Bot-Nachricht kamen
    if letzte_bot_nachricht:
        print(f"[SYNC] Letzte Bot-Nachricht gefunden am {letzte_bot_nachricht.created_at}. Hole neuere Nachrichten...")
        # 'after' sorgt dafür, dass nur Nachrichten geladen werden, die zeitlich NACH dem Bot kamen
        async for message in ctx.channel.history(after=letzte_bot_nachricht, limit=100, oldest_first=True):
            if message.attachments:
                verpasste_nachrichten.append(message)
    else:
        # Falls der Bot noch NIE in diesem Kanal geschrieben hat, nehmen wir zur Sicherheit die letzten 50
        await ctx.send("ℹ️ Keine vorherige Bot-Nachricht gefunden. Scanne die letzten 50 Nachrichten...")
        async for message in ctx.channel.history(limit=50, oldest_first=True):
            if message.author != bot.user and message.attachments:
                verpasste_nachrichten.append(message)

    # 3. Schritt: Die verpassten Screenshots verarbeiten
    if not verpasste_nachrichten:
        await ctx.send("✨ Alles auf dem Laufenden! Es gibt keine verpassten Spenden seit der letzten Aktivität.")
        return

    await ctx.send(f"📦 {len(verpasste_nachrichten)} verpasste Nachricht(en) mit Anhängen gefunden. Verarbeite...")
    erfolgreiche_syncs = 0

    for message in verpasste_nachrichten:
        for attachment in message.attachments:
            filename = attachment.filename.lower()
            if filename.endswith(('.png', '.jpg', '.jpeg', '.webp')):
                try:
                    image_bytes = await attachment.read()
                    base64_encoded = base64.b64encode(image_bytes).decode('utf-8')
                    
                    payload = {
                        "username": str(message.author.name),
                        "imageBuffer": base64_encoded
                    }
                    
                    response = requests.post(WEBAPP_URL, json=payload)
                    
                    if response.status_code == 200 and response.json().get("status") == "success":
                        erfolgreiche_syncs += 1
                        # Der Bot gibt eine kurze Info im Chat ab – das dient gleichzeitig als neuer Anker für das nächste Mal!
                        await ctx.send(f"✅ Nachgetragen: Spende von **{message.author.name}** ({attachment.filename})")
                        
                except Exception as e:
                    print(f"[SYNC-FEHLER] Fehler bei {message.author.name}: {str(e)}")

    await ctx.send(f"🏁 Sync abgeschlossen! Insgesamt {erfolgreiche_syncs} Spende(n) erfolgreich nachgetragen.")

@bot.command(name="clanstatus")
async def clan_status(ctx, resource: str = None):
    """Displays donation totals. Can be filtered by a specific resource. Admin channel only."""
    # 1. Check if the command is executed in the Admin Channel
    if ctx.channel.id != ADMIN_KANAL_ID:
        await ctx.send("❌ This command can only be used in the admin channel.")
        return

    # Build the URL with an optional query parameter for the filter
    request_url = WEBAPP_URL
    if resource:
        await ctx.send(f"📊 Fetching clan donation status filtered by: **{resource}**...")
        # Passing the filter to Google Apps Script via URL parameters
        request_url += f"?resource={resource}"
    else:
        await ctx.send("📊 Fetching complete clan donation overview...")

    try:
        # 2. Send GET request to Google Apps Script
        response = requests.get(request_url)
        
        if response.status_code == 200:
            res_data = response.json()
            
            if res_data.get("status") == "success":
                donation_data = res_data.get("data", {})
                
                if not donation_data:
                    if resource:
                        await ctx.send(f"ℹ️ No donations found for the resource: **{resource}**.")
                    else:
                        await ctx.send("ℹ️ No donations have been registered in the sheet yet.")
                    return
                
                # 3. Format the Discord Output Message in English
                title_string = f"📋 **Clan Donation Status (Filtered by: {resource})**:\n" if resource else "📋 **Complete Clan Donation Overview**:\n"
                output = title_string
                output += "--------------------------------------------------\n"
                
                for player, items in donation_data.items():
                    output += f"👤 **{player}**:\n"
                    for item, amount in items.items():
                        output += f"  ▫️ {amount}x {item}\n"
                    output += "--------------------------------------------------\n"
                
                await ctx.send(output)
            else:
                await ctx.send(f"❌ Google Script Error: {res_data.get('message')}")
        else:
            await ctx.send(f"❌ HTTP Error: Connection to Google failed (Status: {response.status_code}).")
            
    except Exception as e:
        await ctx.send(f"❌ An error occurred: {str(e)}")

@bot.command(name="resources")
async def list_resources(ctx):
    """Lists all unique resource types currently stored in the spreadsheet."""
    if ctx.channel.id != ADMIN_KANAL_ID:
        await ctx.send("❌ This command can only be used in the admin channel.")
        return

    status_message = await ctx.send("🔍 Fetching available filter options...")
    try:
        response = requests.get(f"{WEBAPP_URL}?action=list")
        if response.status_code == 200:
            res_data = response.json()
            if res_data.get("status") == "success":
                resources = res_data.get("resources", [])
                if not resources:
                    await status_message.edit(content="ℹ️ No resources logged in the sheet yet.")
                    return
                
                output = "💡 **Available Resource Filters:**\n"
                output += "Use these values with `!clanstatus [name]`:\n```\n"
                output += ", ".join(resources)
                output += "\n```"
                await status_message.edit(content=output)
            else:
                await status_message.edit(content=f"❌ Error: {res_data.get('message')}")
        else:
            await status_message.edit(content=f"❌ HTTP Error {response.status_code}")
    except Exception as e:
        await status_message.edit(content=f"❌ Failed to fetch recommendations: {str(e)}")

bot.run(TOKEN)