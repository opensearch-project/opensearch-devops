import sys
import json
import zstandard as zstd
from tqdm import tqdm

# Input and output file settings
n = len(sys.argv)
fIn = 'esci.json.zst' if n <= 1 else sys.argv[1]
outfile_prefix = 'transformed_esci_'

# Batch size and index name
batch_size = 10000
index_name = "ecommerce"

def process_stream(input_file):
    dctx = zstd.ZstdDecompressor()
    with open(input_file, 'rb') as compressed_file:
        with dctx.stream_reader(compressed_file) as reader:
            buffer = b""
            while True:
                chunk = reader.read(65536)  # Read in 64KB chunks
                if not chunk:
                    break
                buffer += chunk
                while b"\n" in buffer:  # Process lines in the buffer
                    line, buffer = buffer.split(b"\n", 1)
                    yield line.decode('utf-8', errors='ignore')
            if buffer:  # Handle remaining content
                yield buffer.decode('utf-8', errors='ignore')

batch = []  # List to collect actions
i = 1       # File index for batch output

# Process each line in the input file
for line in tqdm(process_stream(fIn)):
    if line.strip():  # Skip empty lines
        try:
            json_obj = json.loads(line)

            # Filter products by criteria
            if (
                json_obj.get('locale') == "us" and
                json_obj.get('image') and
                json_obj.get('price')
            ):
                # Clean price field
                json_obj["price"] = json_obj["price"][1:].replace(",", "")

                # Create bulk action for OpenSearch
                action_meta = {"index": {"_index": index_name, "_id": json_obj['asin']}}
                batch.append(json.dumps(action_meta))
                batch.append(json.dumps(json_obj))

                # Write batch to file if batch size is reached
                if len(batch) // 2 >= batch_size:  # Each action has 2 lines
                    with open(f"{outfile_prefix}{i}.json", 'w', encoding='utf8') as fOut:
                        fOut.write('\n'.join(batch) + '\n')
                    batch.clear()
                    i += 1

        except json.JSONDecodeError:
            # Skip lines that cannot be parsed
            continue

# Write remaining actions to a final file
if batch:
    with open(f"{outfile_prefix}final.json", 'w', encoding='utf8') as fOut:
        fOut.write('\n'.join(batch) + '\n')
