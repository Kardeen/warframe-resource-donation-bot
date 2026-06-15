import re
import requests

RAW_WIKI_URL = "https://wiki.warframe.com/w/Module:Resources/data?action=raw"

def extract_resources():
    print("🌐 Fetching raw module data from wiki.warframe.com...")
    try:
        response = requests.get(RAW_WIKI_URL, timeout=15)
        if response.status_code != 200:
            print(f"❌ Failed to reach the wiki. HTTP Status: {response.status_code}")
            return

        print("⚙️ Processing Lua lines via State-Machine Parser...")
        
        resource_names = ["Credits"]
        
        in_resource_data = False
        current_item_key = None
        current_item_name = None
        is_resource_type = False
        brace_depth = 0

        lines = response.text.splitlines()

        for line in lines:
            line_str = line.strip()
            if not line_str or line_str.startswith("--"):
                continue

            if "local ResourceData =" in line_str:
                in_resource_data = True
                continue
            
            if not in_resource_data:
                continue

            if brace_depth == 0 and line_str == "}" and current_item_key is None:
                break

            # 3. Detect the start of a new item block (Separated to prevent quote conflicts)
            if brace_depth == 0:
                bracket_match = re.match(r'\["([^"]+)"\]\s*=\s*\{', line_str)
                plain_match = re.match(r'([a-zA-Z0-9_]+)\s*=\s*\{', line_str) if not bracket_match else None
                
                if bracket_match or plain_match:
                    current_item_key = bracket_match.group(1).strip() if bracket_match else plain_match.group(1).strip()
                    current_item_name = None
                    is_resource_type = False
                    brace_depth = 1
                    continue

            # 4. Parse properties inside the active item block
            if current_item_key:
                openers = line_str.count("{")
                closers = line_str.count("}")
                brace_depth += (openers - closers)

                if not is_resource_type:
                    if re.search(r'\bType\s*=\s*["\']Resource["\']', line_str):
                        is_resource_type = True

                # FIX: Handle inner single quotes safely by separating double-quote and single-quote matching
                if not current_item_name:
                    name_dq_match = re.search(r'\bName\s*=\s*"([^"]+)"', line_str)
                    name_sq_match = re.search(r"\bName\s*=\s*'([^']+)'", line_str) if not name_dq_match else None
                    
                    if name_dq_match or name_sq_match:
                        current_item_name = name_dq_match.group(1).strip() if name_dq_match else name_sq_match.group(1).strip()

                if brace_depth <= 0:
                    if is_resource_type and not current_item_key.startswith("/Lotus/"):
                        final_name = current_item_name if current_item_name else current_item_key
                        if not final_name.startswith("/Lotus/"):
                            resource_names.append(final_name)
                    
                    current_item_key = None
                    brace_depth = 0

        resource_names = sorted(list(set(resource_names)))

        if resource_names:
            print(f"\n🎉 Success! Extracted {len(resource_names)} exact items matching Type = 'Resource':")
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