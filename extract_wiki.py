import re
import requests

# The official wiki's raw action endpoint
RAW_WIKI_URL = "https://wiki.warframe.com/w/Module:Resources/data?action=raw"



def extract_resources():
    print("🌐 Fetching raw module data from wiki.warframe.com...")
    try:
        response = requests.get(RAW_WIKI_URL, timeout=15)
        print(f"📡 Connection Status: {response.status_code}")

        if response.status_code != 200:
            print(
                f"❌ Failed to reach the wiki source block. HTTP Status: {response.status_code}"
            )
            return

        raw_text = response.text
        print("AI-PARSER: Isolating 'local ResourceData' block...")

        # 1. Target and extract ONLY the local ResourceData array
        block_match = re.search(
            r"local\s+ResourceData\s*=\s*\{(.*?)\n\s*\}\s*(?=\n|return|$)",
            raw_text,
            re.DOTALL,
        )
        if not block_match:
            block_match = re.search(
                r"local\s+ResourceData\s*=\s*\{(.*)", raw_text, re.DOTALL
            )

        if not block_match:
            print(
                "❌ Error: Could not locate 'local ResourceData' table in the raw text."
            )
            return

        resource_data_content = block_match.group(1)
        print(
            "AI-PARSER: Slicing elements strictly matching Type = 'Resource'..."
        )

        # 2. Extract every single parent item block structure
        item_blocks = re.findall(r'\["([^"]+)"\]\s*=\s*\{([^}]+)\}', resource_data_content)

        resource_names = []

        for name, block_content in item_blocks:
            # SKIP: If the key name itself starts with a file path like /Lotus/, skip it entirely
            if name.strip().startswith("/Lotus/"):
                continue
                
            # STRICT FILTER: Check if Type is exactly "Resource"
            if re.search(r'Type\s*=\s*["\']Resource["\']', block_content):
                
                # We use \b (word boundary) so 'InternalName' is ignored
                name_field_match = re.search(r'\bName\s*=\s*["\']([^"\']+)["\']', block_content)
                
                if name_field_match:
                    display_name = name_field_match.group(1).strip()
                    # Extra safety check: skip if the display name accidentally contains a path
                    if not display_name.startswith("/Lotus/"):
                        resource_names.append(display_name)
                else:
                    resource_names.append(name.strip())

        # Sort and deduplicate alphabetically
        resource_names = sorted(list(set(resource_names)))

        if resource_names:
            print(
                f"\n🎉 Successfully isolated {len(resource_names)} official resources:"
            )
            print("-" * 50)
            for r_name in resource_names:
                print(f" - {r_name}")
            print("-" * 50)

            # Write out to text file asset
            with open("warframe_resources.txt", "w", encoding="utf-8") as f:
                f.write("\n".join(resource_names))
            print("💾 Data saved successfully to 'warframe_resources.txt'")
        else:
            print(
                "⚠️ Completed parsing loop, but zero items matched Type = 'Resource'."
            )

    except Exception as e:
        print(f"❌ Script encountered a critical error: {str(e)}")


if __name__ == "__main__":
    extract_resources()