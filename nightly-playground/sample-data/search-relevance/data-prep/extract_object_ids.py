#!/usr/bin/env python3
"""
Extract object_ids from ubi_queries_events.ndjson and save them to a CSV file.
Only processes entries with:
- action_name of "add_to_cart", "impression", or "search"
- non-empty event_attributes
- object_id present in event_attributes.object
"""

import json
import csv
import os
from pathlib import Path

def extract_object_ids(ndjson_file_path):
    """
    Extract object_ids from entries with specific action_name values and valid event_attributes.
    Only processes entries where event_attributes has an object with an object_id.
    """
    try:
        object_ids = []
        target_actions = ["add_to_cart", "impression", "search"]
        processed_count = 0
        skipped_count = 0
        valid_count = 0
        
        with open(ndjson_file_path, 'r', encoding='utf-8') as ndjson_file:
            for line_num, line in enumerate(ndjson_file, 1):
                if not line.strip():  # Skip empty lines
                    continue
                    
                try:
                    # Parse each line as a separate JSON object
                    json_obj = json.loads(line.strip())
                    
                    # Check if action_name is one of our target actions
                    if "action_name" in json_obj and json_obj["action_name"] in target_actions:
                        processed_count += 1
                        
                        # Check if event_attributes exists and is not empty/None
                        if not json_obj.get("event_attributes"):
                            skipped_count += 1
                            continue
                        
                        event_attrs = json_obj["event_attributes"]
                        
                        # Check if object exists in event_attributes and contains an object_id
                        if (isinstance(event_attrs, dict) and 
                            "object" in event_attrs and 
                            isinstance(event_attrs["object"], dict) and
                            "object_id" in event_attrs["object"]):
                            
                            object_id = event_attrs["object"]["object_id"]
                            if object_id:  # Only add non-empty object_ids
                                object_ids.append(object_id)
                                valid_count += 1
                        else:
                            skipped_count += 1
                            
                except json.JSONDecodeError as json_err:
                    print(f"Error parsing JSON at line {line_num}: {json_err}")
                    continue
                except Exception as e:
                    print(f"Error processing line {line_num}: {e}")
                    continue
        
        # Remove duplicates while preserving order
        unique_object_ids = []
        for obj_id in object_ids:
            if obj_id not in unique_object_ids:
                unique_object_ids.append(obj_id)
        
        print(f"Processed {processed_count} entries matching target actions")
        print(f"Found {valid_count} entries with valid object_ids")
        print(f"Skipped {skipped_count} entries with missing/empty event_attributes or object_id")
        print(f"Extracted {len(unique_object_ids)} unique object_ids")
        
        return unique_object_ids
    except Exception as e:
        print(f"Error extracting object_ids: {e}")
        return []

def save_to_csv(object_ids, csv_file_path):
    """Save the list of object_ids to a CSV file."""
    try:
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(csv_file_path), exist_ok=True)
        
        with open(csv_file_path, 'w', newline='', encoding='utf-8') as csv_file:
            writer = csv.writer(csv_file)
            writer.writerow(['object_id'])  # Write header
            for obj_id in object_ids:
                writer.writerow([obj_id])
        
        print(f"Successfully wrote {len(object_ids)} object_ids to {csv_file_path}")
    except Exception as e:
        print(f"Error saving to CSV: {e}")

def main():
    # Define file paths
    base_dir = Path(__file__).parent
    ndjson_file_path = base_dir / "nightly-playground/sample-data/search-relevance/ubi_queries_events.ndjson"
    csv_file_path = base_dir / "object_ids.csv"
    
    print(f"Extracting object_ids from {ndjson_file_path}")
    print(f"Looking for entries with action_name: add_to_cart, impression, or search")
    
    # Extract object_ids
    object_ids = extract_object_ids(ndjson_file_path)
    
    if object_ids:
        # Save to CSV
        save_to_csv(object_ids, csv_file_path)
    else:
        print("No object_ids found or an error occurred.")

if __name__ == "__main__":
    main()