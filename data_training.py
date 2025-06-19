import json

def split_text_and_chunks(text_file, landing_ai_json, max_input=35000, max_output=4500):
    """Split both input text and output chunks into paired segments"""
    
    # Load input text
    with open(text_file, "r", encoding="utf-8") as f:
        full_text = f.read()
    
    # Load chunks
    with open(landing_ai_json, "r", encoding="utf-8") as f:
        all_chunks = json.load(f)["chunks"]
    
    # Split text into parts
    text_parts = []
    current_part = ""
    
    for line in full_text.split('\n'):
        if len(current_part) + len(line) < max_input:
            current_part += line + '\n'
        else:
            text_parts.append(current_part)
            current_part = line + '\n'
    if current_part:
        text_parts.append(current_part)
    
    # Calculate chunks per part
    chunks_per_part = len(all_chunks) // len(text_parts)
    
    # Create training pairs
    training_data = []
    chunk_index = 0
    
    for i, text_part in enumerate(text_parts):
        # Get chunks for this part
        part_chunks = []
        output_size = 0
        
        while chunk_index < len(all_chunks) and output_size < max_output:
            chunk = all_chunks[chunk_index]
            chunk_str = json.dumps(chunk, ensure_ascii=False)
            
            if output_size + len(chunk_str) < max_output:
                part_chunks.append(chunk)
                output_size += len(chunk_str)
                chunk_index += 1
            else:
                break
        
        # Create training example
        training_data.append({
            "text_input": text_part,
            "output": json.dumps({"chunks": part_chunks}, ensure_ascii=False)
        })
        
        print(f"Part {i+1}: {len(text_part)} chars input, {len(part_chunks)} chunks output")
    
    return training_data

# Use it
training_data = split_text_and_chunks(
    "extraction_results/doc_1_docling.txt",
    "landing_ai_output.json"
)

print(f"\nCreated {len(training_data)} training examples")

# Save each part for review
for i, example in enumerate(training_data):
    with open(f"training_part_{i+1}_input.txt", "w", encoding="utf-8") as f:
        f.write(example["text_input"])
    with open(f"training_part_{i+1}_output.json", "w", encoding="utf-8") as f:
        f.write(example["output"])