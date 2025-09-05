#!/usr/bin/env python3
"""
Filter JSON file based on IDs from CSV files.

This script:
1. Loads IDs from docids.csv and object_ids.csv
2. Processes a JSON file in pairs of lines
3. If the first line's index._id value is in the list of IDs, appends both lines to a new file
"""

import csv
import json
import os
from pathlib import Path

def load_ids_from_csv(csv_file_path):
    """Load IDs from a CSV file."""
    ids = set()
    try:
        with open(csv_file_path, 'r', encoding='utf-8') as csv_file:
            reader = csv.reader(csv_file)
            next(reader)  # Skip header
            for row in reader:
                if row and row[0]:  # Check if row exists and has a value
                    ids.add(row[0])
        print(f"Loaded {len(ids)} IDs from {csv_file_path}")
        return ids
    except Exception as e:
        print(f"Error loading IDs from {csv_file_path}: {e}")
        return set()

def filter_json_file_by_ids(json_file_path, ids_set, output_file_path):
    """
    Filter a JSON file by IDs.
    
    Processes the file in pairs of lines. If the first line's index._id value is in the
    list of IDs, appends both lines to the output file.
    """
    try:
        line_count = 0
        pair_count = 0
        matched_count = 0
        
        # Create output directory if it doesn't exist
        os.makedirs(os.path.dirname(output_file_path) if os.path.dirname(output_file_path) else '.', exist_ok=True)
        
        with open(json_file_path, 'r', encoding='utf-8') as json_file, \
             open(output_file_path, 'w', encoding='utf-8') as output_file:
            
            lines = []
            for line in json_file:
                line_count += 1
                lines.append(line)
                
                # Process in pairs
                if len(lines) == 2:
                    pair_count += 1
                    
                    try:
                        # Parse the first line to extract _id
                        first_line_json = json.loads(lines[0])
                        
                        # Check for _id in different possible locations
                        doc_id = None
                        
                        # Try index._id structure
                        if 'index' in first_line_json and '_id' in first_line_json['index']:
                            doc_id = first_line_json['index']['_id']
                        # Try _id directly
                        elif '_id' in first_line_json:
                            doc_id = first_line_json['_id']
                        
                        if doc_id and doc_id in ids_set:
                            # Write both lines to output file
                            output_file.write(lines[0])
                            output_file.write(lines[1])
                            matched_count += 1
                            
                            if matched_count % 100 == 0:
                                print(f"Progress: {matched_count} matching pairs found")
                    except json.JSONDecodeError:
                        print(f"Error parsing JSON at line {line_count-1}")
                    except KeyError as e:
                        print(f"Key error at line {line_count-1}: {e}")
                    
                    # Reset for next pair
                    lines = []
        
        print(f"Processed {line_count} lines ({pair_count} pairs)")
        print(f"Found {matched_count} matching pairs")
        print(f"Output written to {output_file_path}")
    
    except Exception as e:
        print(f"Error processing file: {e}")

def main():
    # Define file paths
    base_dir = Path(__file__).parent
    docids_path = base_dir / "docids.csv"
    object_ids_path = base_dir / "object_ids.csv"
    json_file_path = base_dir / "esci_us_opensearch-2025-06-06.json"
    output_file_path = base_dir / "esci_us_opensearch_shrunk.ndjson"
    
    print("Starting JSON filtering process...")
    
    # Load IDs from CSV files
    docids = load_ids_from_csv(docids_path)
    object_ids = load_ids_from_csv(object_ids_path)
    
    # Combine IDs from both files
    all_ids = docids.union(object_ids)
    print(f"Total unique IDs: {len(all_ids)}")
    
    # Filter JSON file by IDs
    filter_json_file_by_ids(json_file_path, all_ids, output_file_path)
    
    print("Process completed.")

if __name__ == "__main__":
    main()