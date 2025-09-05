#!/usr/bin/env python3
"""
Extract all docId values from esci_us_judgments.json and save them to a CSV file.
"""

import json
import csv
import os
from pathlib import Path

def extract_docids(json_file_path):
    """Extract all docId values from the specified JSON file."""
    try:
        with open(json_file_path, 'r', encoding='utf-8') as json_file:
            data = json.load(json_file)
            
        doc_ids = []
        
        # Navigate the JSON structure to extract all docIds
        for judgment in data.get('judgmentRatings', []):
            for rating in judgment.get('ratings', []):
                if 'docId' in rating:
                    doc_ids.append(rating['docId'])
        
        return doc_ids
    except Exception as e:
        print(f"Error extracting docIds: {e}")
        return []

def save_to_csv(doc_ids, csv_file_path):
    """Save the list of docIds to a CSV file."""
    try:
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(csv_file_path), exist_ok=True)
        
        with open(csv_file_path, 'w', newline='', encoding='utf-8') as csv_file:
            writer = csv.writer(csv_file)
            writer.writerow(['docId'])  # Write header
            for doc_id in doc_ids:
                writer.writerow([doc_id])
        
        print(f"Successfully wrote {len(doc_ids)} docIds to {csv_file_path}")
    except Exception as e:
        print(f"Error saving to CSV: {e}")

def main():
    # Define file paths
    base_dir = Path(__file__).parent
    json_file_path = base_dir / "nightly-playground/sample-data/search-relevance/esci_us_judgments.json"
    csv_file_path = base_dir / "docids.csv"
    
    print(f"Extracting docIds from {json_file_path}")
    
    # Extract docIds
    doc_ids = extract_docids(json_file_path)
    
    if doc_ids:
        print(f"Found {len(doc_ids)} docIds")
        # Save to CSV
        save_to_csv(doc_ids, csv_file_path)
    else:
        print("No docIds found or an error occurred.")

if __name__ == "__main__":
    main()