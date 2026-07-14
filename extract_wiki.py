import re
import requests
import luadata

RAW_WIKI_URL = "https://wiki.warframe.com/w/Module:Resources/data?action=raw"

def extract_resources():
    print("🌐 Fetching raw module data from wiki.warframe.com...")
    try:
        response = requests.get(RAW_WIKI_URL, timeout=15)
        if response.status_code != 200:
            print(f"❌ Failed to reach the wiki. HTTP Status: {response.status_code}")
            return

        raw_text = response.text
        
        # 1. Isolate the 'local ResourceData = { ... }' block precisely
        start_marker = "local ResourceData = {"
        start_idx = raw_text.find(start_marker)
        if start_idx == -1:
            print("❌ Could not find 'local ResourceData = {' in the module script.")
            return
            
        # Shift past the variable declaration string to point to the opening brace '{'
        cursor = start_idx + len(start_marker) - 1
        
        # Find the matching closing brace of the main table structure
        brace_depth = 0
        end_idx = -1
        in_string = False
        string_char = None
        escape_next = False
        
        for i in range(cursor, len(raw_text)):
            char = raw_text[i]
            
            if escape_next:
                escape_next = False
                continue
            if char == "\\":
                escape_next = True
                continue
                
            if in_string:
                if char == string_char:
                    in_string = False
                continue
            else:
                if char in ('"', "'"):
                    in_string = True
                    string_char = char
                    continue
            
            if char == "{":
                brace_depth += 1
            elif char == "}":
                brace_depth -= 1
                if brace_depth == 0:
                    end_idx = i + 1
                    break

        if end_idx == -1:
            print("❌ Failed to isolate matching boundaries for the ResourceData dictionary.")
            return

        # 2. Extract the table block text slice
        lua_table_string = raw_text[cursor:end_idx]

        print("⚙️ Decoding Lua array structures natively via 'luadata' module...")
        # luadata translates the isolated Lua table string into a python dictionary matrix instantly!
        resource_dict = luadata.unserialize(lua_table_string)

        print(f"🔍 Successfully mapped {len(resource_dict)} native entries. Applying type filters...")

        resource_names = ["Credits"]  # Retain standard base currency fallback entry

        # 3. Work with clean Python dictionary mappings instead of text strings!
        for item_key, properties in resource_dict.items():
            if not isinstance(properties, dict):
                continue
                
            # Filter A: Must have Type equal to "Resource" exactly
            if properties.get("Type") == "Resource":
                internal_name = properties.get("InternalName", "")
                
                # Filter B: Exclude open-world mining rocks, gems, and fish parts
                if any(k in internal_name for k in ["/Gems/", "/Fish/", "/MushroomJournal/"]):
                    continue
                    
                display_name = properties.get("Name", item_key).strip()
                
                # Filter C: Filter out internal placeholders
                if not display_name.startswith("/Lotus/") and display_name != "[PH]":
                    resource_names.append(display_name)

        resource_names = sorted(list(set(resource_names)))

        if len(resource_names) > 1:
            print(f"\n🎉 Success! Extracted {len(resource_names)} verified inventory items.")
            print("-" * 50)
            print(f" -> Total items captured: {len(resource_names)}")
            print("-" * 50)

            with open("warframe_resources.txt", "w", encoding="utf-8") as f:
                f.write("\n".join(resource_names))
            print("💾 Saved perfect whitelist file to 'warframe_resources.txt'")
        else:
            print("⚠️ Parsing loop finished, but 0 elements matched our filters.")

    except Exception as e:
        print(f"❌ Script hit a critical exception error: {str(e)}")

if __name__ == "__main__":
    extract_resources()