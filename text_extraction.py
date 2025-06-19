from docling.document_converter import DocumentConverter
from pathlib import Path
import json

# Convert PDFs
def fix_headers(obj):
    """Recursively replace Ø→é in any string that starts with ##."""
    if isinstance(obj, str):
        if obj.lstrip().startswith("##"):
            return obj.replace("Ø", "é")
        return obj
    if isinstance(obj, list):
        return [fix_headers(item) for item in obj]
    if isinstance(obj, dict):
        return {k: fix_headers(v) for k, v in obj.items()}
    return obj

# Create output directory
JSON_OUT_DIR = Path("json_extracted")
JSON_OUT_DIR.mkdir(parents=True, exist_ok=True)

# Get all PDF files from raws_split directory
pdf_dir = Path("raws_split")
pdf_files = sorted(pdf_dir.glob("*.pdf"))

print(f"Found {len(pdf_files)} PDF files to process")

# Initialize converter once (reuse for all files)
converter = DocumentConverter()

# Process each PDF file
for pdf_file in pdf_files:
    print(f"\nProcessing: {pdf_file.name}")
    
    try:
        # Convert PDF
        result = converter.convert(str(pdf_file))
        
        # Get JSON format
        json_output = result.document.export_to_dict()
        
        # Fix the header
        doc_dict = fix_headers(json_output)
        
        # Create output filename based on input filename
        output_filename = pdf_file.stem + ".json"
        output_path = JSON_OUT_DIR / output_filename
        
        # Save to file
        output_path.write_text(
            json.dumps(doc_dict, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        
        print(f"  ✓ Saved to {output_path}")
        print(f"    Tables: {len(result.document.tables)}, Pages: {len(result.document.pages)}")
        
    except Exception as e:
        print(f"  ✗ Error processing {pdf_file.name}: {str(e)}")
        continue

print("\nProcessing complete!")





# if you want to get the markdown result 


# from docling.document_converter import DocumentConverter
# from pathlib import Path

# # Convert PDF
# converter = DocumentConverter()
# result = converter.convert("raws_split/BNC_RG_2024Q1_part01.pdf")

# # Get raw text (markdown format)
# raw_text = result.document.export_to_markdown()

# fixed_lines = [
#     line.replace("Ø", "é") if line.lstrip().startswith("##") else line
#     for line in raw_text.splitlines()
# ]
# raw_text = "\n".join(fixed_lines)

# # Save
# out_path = Path("plain_text/docling_raw_text.txt")
# out_path.parent.mkdir(parents=True, exist_ok=True)
# out_path.write_text(raw_text, encoding="utf-8")

# print(f"Saved raw text to {out_path}")
# print(f"Extracted {len(raw_text):,} characters")


# # Save to text file
# with open("plain_text/docling_raw_text.txt", "w", encoding="utf-8") as f:
#     f.write(raw_text)

# print("Saved raw text to docling_raw_text.txt")
# print(f"Extracted {len(raw_text)} characters")