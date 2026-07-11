import unittest
import sys
import os

# Force standard text output visibility for IDE terminals
suite = unittest.TestSuite()
unittest.runner.TextTestRunner(stream=sys.stdout, verbosity=2)

# Import your engines straight from bot.py
from bot import clean_raw_donation_text, clean_and_validate_ocr, RESOURCE_WHITELIST, reader

class WarframeBotComprehensiveTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        """Runs once before testing. Verifies the resource checklist is populated."""
        if not RESOURCE_WHITELIST:
            RESOURCE_WHITELIST.extend([
                "Oxium", "Salvage", "Rubedo", "Alloy Plate", "Ferrite", 
                "Nano Spores", "Polymer Bundle", "Circuits", "Gallium", 
                "Control Module", "Credits", "Plastids", "Tellurium", "Cryotic"
            ])

    def test_text_stream_offline_sync_simulation(self):
        """Validates arrays of strings matching your offline !sync bug context."""
        simulated_offline_lines = [
            "I have donated 6000 credits", 
            "20000 salvage", 
            "5000 rubedo", 
            "11000 ferrite", 
            "2000 oxium", 
            "2426 plastids"
        ]
        results = clean_and_validate_ocr(simulated_offline_lines)
        results_map = {res["item"].lower(): res["amount"] for res in results}
        self.assertEqual(results_map.get("credits"), 6000)
        self.assertEqual(results_map.get("ferrite"), 11000)
        self.assertEqual(results_map.get("oxium"), 2000)

    def test_text_thousand_separator_normalization(self):
        """Ensures that thousands commas do not generate word spacing closures."""
        raw_input = 'Donation: 2, 000 X Oxium 300, 000 X Salvage'
        normalized = clean_raw_donation_text(raw_input)
        self.assertIn("2000 X Oxium", normalized)
        self.assertIn("300000 X Salvage", normalized)


    # =========================================================================
    # 📸 PARAMETERIZED IMAGE MATRIX RUNNER
    # =========================================================================

    def test_all_matrix_images_ocr(self):
        """Iterates over the defined image matrix to execute live OCR comparisons."""
        
        # 🎯 DEFINE YOUR EXPECTED TEST MATRIX HERE
        # Add or adjust these items and amounts to match your actual screenshot values!
        image_test_matrix = {
            "donation_1.png": [
                {"item": "Cryotic", "amount": 31},
                {"item": "Salvage", "amount": 8}
            ],
            "donation_2.png": [
                {"item": "Credits", "amount": 10}
            ],
            "donation_3.png": [
                {"item": "Nano Spores", "amount": 500000},
                {"item": "Salvage", "amount": 500000},
                {"item": "Alloy Plate", "amount": 250000},
                {"item": "Ferrite", "amount": 120000},
                {"item": "Circuits", "amount": 35000},
                {"item": "Polymer Bundle", "amount": 5000},
                {"item": "Plastids", "amount": 5000}
            ],
            "donation_4.png": [
                {"item": "Oxium", "amount": 2000},
                {"item": "Salvage", "amount": 300000},
                {"item": "Rubedo", "amount": 70000},
                {"item": "Alloy Plate", "amount": 100000},
                {"item": "Ferrite", "amount": 200000},
                {"item": "Nano Spores", "amount": 20000},
                {"item": "Polymer Bundle", "amount": 10000},
                {"item": "Circuits", "amount": 10000},
                {"item": "Gallium", "amount": 100},
                {"item": "Control Module", "amount": 300}
            ]
        }

        print("\n\n====== 📸 STARTING MULTI-IMAGE MATRIX TESTING ======")
        
        for filename, expected_data in image_test_matrix.items():
            target_image_path = os.path.join("test_images", filename)
            
            # Step-nested block mapping context
            with self.subTest(image=filename):
                if not os.path.exists(target_image_path):
                    print(f"⏩ [MATRIX SKIP] File not found: '{target_image_path}'. Skipping entry.")
                    continue
                
                print(f"\n--- 🔍 Testing File: {filename} ---")
                
                # 1. Extract raw line readings from image file
                raw_ocr_lines = reader.readtext(target_image_path, detail=0)
                
                # 2. Map through parsing logic structure
                actual_results = clean_and_validate_ocr(raw_ocr_lines)
                
                # 3. Standardize layouts to easily assert values (lowercase matching maps)
                actual_map = {res["item"].lower(): res["amount"] for res in actual_results}
                expected_map = {res["item"].lower(): res["amount"] for res in expected_data}
                
                print(f"📋 Expected Data: {expected_map}")
                print(f"📥 Extracted Data: {actual_map}")
                
                # 4. Check for length balance mismatches
                self.assertEqual(
                    len(actual_map), len(expected_map), 
                    f"Mismatched count of extracted items for {filename}. Expected {len(expected_map)}, got {len(actual_map)}."
                )
                
                # 5. Assert resource name and amount matches exactly
                for resource_name, expected_amount in expected_map.items():
                    self.assertIn(
                        resource_name, actual_map, 
                        f"Missing resource assignment error! Expected to find '{resource_name}' in {filename} but it wasn't extracted."
                    )
                    self.assertEqual(
                        actual_map[resource_name], expected_amount, 
                        f"Quantity mismatch for '{resource_name}' in {filename}. Expected {expected_amount}, got {actual_map[resource_name]}."
                    )
                
                print(f"✅ Pass: {filename} data matches expectations perfectly.")
                
        print("\n====== 🏁 MULTI-IMAGE MATRIX TESTING COMPLETE ======")


if __name__ == "__main__":
    unittest.main(testRunner=unittest.TextTestRunner(stream=sys.stdout, verbosity=2))