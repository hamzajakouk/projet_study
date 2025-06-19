"""
A multi-stage pipeline to extract table structures from PDF pages.
STAGE 1: A two-step OCR process to get structured text and tables from a page image.
    - Step 1.1: Raw OCR extraction (Image -> Text)
    - Step 1.2: Text structuring (Text -> JSON with Markdown)
STAGE 2: A table analysis process to extract the skeleton from the markdown tables.
"""

from pathlib import Path
import json, os, time, base64
from typing import Dict, List, Any

import fitz              # PyMuPDF
from openai import OpenAI  # pip install openai>=1.30

# ─────────────────────────── CONFIG ──────────────────────────── #
PDF_FILE  = Path("raws_split/rapport-actionnaire-t1-2025_part01.pdf")
OUT_TABLE = Path("json_extracted/table_metadata_from_pdf.jsonl")
OUT_TEXT  = Path("json_extracted/page_text_extracted.jsonl")
DPI       = 200
MAX_OCR_TOKENS = 8192

# Ensure your OpenAI API key is set as an environment variable
# e.g., export OPENAI_API_KEY='sk-...'
client = OpenAI()

# ────────────────────────── PDF helpers ───────────────────────── #
pdf_doc = fitz.open(str(PDF_FILE))
PAGE_COUNT = pdf_doc.page_count
print(f"📑 PDF pages: {PAGE_COUNT}")

def render_png(page_no: int, dpi: int = DPI) -> bytes:
    """Return page rendered as PNG bytes (1‑based page_no)."""
    return pdf_doc[page_no-1].get_pixmap(dpi=dpi).tobytes("png")

# ─────────────────── Load Pages to Process + OCR Cache ─────────── #

# Get a unique, sorted list of page numbers to process, ignoring incorrect table counts.
pages_with_tables = [1, 7, 8, 9]
print(f"Pages to process based on initial file: {pages_with_tables}")


cached_text: Dict[int, Dict[str, Any]] = {}
if OUT_TEXT.exists():
    for line in OUT_TEXT.read_text(encoding="utf-8").splitlines():
        try:
            rec = json.loads(line)
            if rec.get("extraction_status") == "success":
                cached_text[rec["page"]] = rec["text_data"]
        except json.JSONDecodeError:
            print(f"Skipping malformed line in cache file: {line}")
print(f"🔄 OCR cache pages:", len(cached_text))


# ────────────────────── STAGE 1.1: Raw Text Extraction ────────────────────── #

def ocr_raw_text(img_bytes: bytes) -> str:
    """
    Performs pure OCR on an image, returning only the raw text with basic layout.
    """
    img64 = base64.b64encode(img_bytes).decode()
    prompt = "You are a precision OCR engine. Extract every piece of text from this image exactly as you see it. Preserve the original line breaks and approximate spatial layout. Do not add any formatting like markdown or JSON."
    
    try:
        resp = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": [{"type": "text", "text": prompt}, {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img64}"}}]}],
            temperature=0,
            max_tokens=4096,
        )
        return resp.choices[0].message.content
    except Exception as e:
        print(f"CRITICAL: An error occurred during raw text OCR: {e}")
        return f"ERROR: Raw OCR failed with exception: {str(e)}"

# ────────────────────── STAGE 1.2: Text Structuring ─────────────────────── #
# ────────────────────── STAGE 1.2: Text Structuring (using o3) ─────────────────────── #
def extract_markdown_tables_with_o3(raw_text: str, page_no: int) -> List[str]:
    """
    Takes raw text from a page and uses the o3 model to extract a list of
    markdown-formatted table strings.
    """
    # 1. Define the new, simpler tool schema
    table_detection_tool_schema = [{
        "type": "function",
        "name": "capture_markdown_tables",
        "description": "Captures all markdown-formatted tables found in the text.",
        "parameters": {
            "type": "object",
            "properties": {
                "markdown_tables": {
                    "type": "array",
                    "description": "A list containing the markdown string for each table found in the text.",
                    "items": {"type": "string"}
                }
            },
            "required": ["markdown_tables"]
        }
    }]

    # 2. Define the new, focused system prompt
    SYS_DETECT_TABLES = (
        "You are a data extraction bot. Your sole purpose is to find any and all tables "
        "within the provided raw text. Format each table you find into a clean markdown string. "
        "After finding all tables, you MUST call the `capture_markdown_tables` function, "
        "passing the list of markdown table strings you created. "
        "If no tables are found, call the function with an empty list."
    )

    try:
        # 3. Call the o3 model with the new tool and prompt
        resp = client.responses.create(
            model="o3",
            input=[
                {"role": "system", "content": SYS_DETECT_TABLES},
                {"role": "developer", "content": [{"type": "input_text", "text": raw_text}]}
            ],
            tools=table_detection_tool_schema,
            store=False,
            reasoning={"effort": "medium", "summary": "auto"},
            text={"format": {"type": "text"}},
        )

        # 4. Parse the response
        if len(resp.output) > 1 and hasattr(resp.output[1], 'arguments'):
            arguments = json.loads(resp.output[1].arguments)
            return arguments.get("markdown_tables", [])
        else:
            # The model didn't call the tool, likely meaning no tables were found
            return []

    except Exception as e:
        print(f"    CRITICAL: An error occurred during o3 table detection on page {page_no}: {e}")
        return [] # Return an empty list on error
# def structure_text_as_json(raw_text: str, page_no: int) -> Dict[str, Any]:
#     """
#     Takes a string of raw text and structures it into the desired JSON format.
#     """
#     prompt = f"""
# # ROLE AND OBJECTIVE
# You are an expert document structuring AI. You will be given raw, unstructured text extracted from page {page_no} of a PDF. Your ONLY job is to clean this text, identify the semantic structure (headers, paragraphs, tables), and format it into a single, strictly-formatted JSON object.

# # RAW TEXT INPUT:
# ---
# {raw_text}
# ---

# # CORE INSTRUCTIONS
# 1.  **Analyze the Raw Text**: Read the provided text and identify all logical content blocks.
# 2.  **Format and Clean**: Correct any minor OCR errors and format the content beautifully.
# 3.  **Format Tables**: Pay special attention to text that looks like tables. Convert it into perfect markdown tables.
# 4.  **Produce JSON**: Assemble all structured information into the final JSON object as specified below.

# # CONTENT TYPE DEFINITIONS
# - **`header`**: A title or a major section heading. Typically larger, bold, or otherwise distinct from body text. In the `formatted_text`, prefix these with `##`.
# - **`paragraph`**: A standard block of prose or body text.
# - **`list`**: A sequence of items, typically marked with bullets (•, *, -) or numbers.
# - **`table`**: A region of structured data with rows and columns.
#     - **Crucially, capture the entire table as a single markdown string in the `content` field.**
#     - This includes the header, all rows, and any separating lines (`|---|---|`).
#     - In the `formatted_text`, enclose the entire markdown table between `[TABLE START]` and `[TABLE END]`.
# - **`TOC`**: A "Table of Contents" section that lists document sections and their corresponding page numbers.
# - **`footnote`**: Small-print text at the bottom of the page, often referenced from the main content with a superscript number or symbol.
# - **`caption`**: Text that describes an image, chart, or table. Usually located directly below or beside it.

# # OUTPUT FORMAT
# You MUST return a single, valid JSON object. Do not wrap it in markdown backticks.
# ```json
# {{
#   "page_number": {page_no},
#   "has_tables": true,
#   "table_count": 1,
#   "formatted_text": "...",
#   "sections": []
# }}
# """
#     try:
#         resp = client.chat.completions.create(
#             model="gpt-4o",
#             messages=[{"role": "user", "content": prompt}],
#             temperature=0,
#             max_tokens=MAX_OCR_TOKENS,
#             response_format={"type": "json_object"}
#         )
#         return json.loads(resp.choices[0].message.content)
#     except Exception as e:
#         print(f"CRITICAL: An error occurred during text structuring on page {page_no}: {e}")
#         return {"error": "Text structuring failed", "details": str(e), "page_number": page_no}

# ────────────────────── STAGE 1 Orchestrator ────────────────────── #

def ocr_page_pipeline(img_bytes: bytes, page_no: int) -> Dict[str, Any]:
    """
    Orchestrates the new two-stage OCR pipeline.
    """
    print(f"  -> OCR Stage 1.1: Extracting raw text from page {page_no}...")
    raw_text = ocr_raw_text(img_bytes)
    
    if raw_text.startswith("ERROR:"):
        print(f"  -> OCR Stage 1.1 FAILED for page {page_no}.")
        return {"error": "Raw OCR failed", "details": raw_text, "page_number": page_no}
        
    print(f"  -> OCR Stage 1.2: Structuring text for page {page_no}...")
    structured_json = structure_text_as_json(raw_text, page_no)
    
    return structured_json

# ───────────────── STAGE 2: Table Skeleton Extraction ──────────────── #

def analyze_one_table(markdown_table: str) -> Dict[str, Any]:
    """Send a single markdown table to get its skeleton."""
    tool_schema = [{"type": "function","name": "extract_table_skeleton","description": "Return structural metadata (no data cells) for ONE markdown table block.","parameters": {"type": "object","properties": {"caption": {"type": ["string", "null"]},"column_count": {"type": "integer"},"row_count": {"type": "integer"},"column_headers": {"type": "array", "items": {"type": "string"}},"row_headers": {"type": "array", "items": {"type": "string"}}},"required": ["column_count", "row_count", "column_headers", "row_headers"],"additionalProperties": False}}]
    SYS_ANALYZE = ("Your primary task is to analyze the structure of a single markdown table provided as input. Your goal is to extract its column headers, row headers (if any), and a total count of data rows and columns. \n\nIMPORTANT INSTRUCTIONS:\n1.  **Column Headers**: Identify the main header row and extract its cells into the `column_headers` list.\n2.  **Handling Conjoined Tables**: If the input looks like two tables separated by a newline, treat it as ONE continuous table.\n3.  **Row Count**: Count all data rows, excluding any header rows.\n4.  **Row Header Location**: Row headers, if they exist, are always in the first column.\n5.  **Handling Sparse Row Headers**: For sparse first columns, extract only the unique, non-empty category labels to form the `row_headers` list.\n\nCall the `extract_table_skeleton` function once with the aggregated metadata.")
    user_block = {"role": "developer","content": [{"type": "input_text", "text": markdown_table[:8000]}]}
    try:
        resp = client.responses.create(model="o3", input=[{"role": "system", "content": SYS_ANALYZE}, user_block], tools=tool_schema, store=False, reasoning={"effort": "medium", "summary": "auto"}, text={"format": {"type": "text"}})
        return json.loads(resp.output[1].arguments)
    except Exception as e:
        print(f"CRITICAL: Error analyzing table: {e}")
        return {"error": "Failed to analyze table", "details": str(e)}
# ───────────────── (NEW) Post-Processing Step ──────────────── #

def merge_consecutive_tables(table_records: List[Dict]) -> List[Dict]:
    """
    Merges consecutive tables in the list if they are on the same page
    and have identical column headers.
    """
    if not table_records:
        return []

    merged_records = []
    # Make a copy to modify while iterating
    records_to_process = list(table_records) 
    
    i = 0
    while i < len(records_to_process):
        current_rec = records_to_process[i]
        
        # Check if there is a next record to compare with
        if i + 1 < len(records_to_process):
            next_rec = records_to_process[i+1]
            
            # Define the conditions for merging
            # Using .get() provides safety if a key is missing
            current_meta = current_rec.get("meta", {})
            next_meta = next_rec.get("meta", {})
            
            same_page = current_rec.get("page") == next_rec.get("page")
            same_headers = current_meta.get("column_headers") == next_meta.get("column_headers")
            
            if same_page and same_headers:
                print(f"  -> Merging table (Original Index {current_rec['table_index']}) and table (Original Index {next_rec['table_index']}) on page {current_rec['page']}.")
                
                # Create the new merged metadata
                merged_meta = {
                    "caption": current_meta.get("caption") or next_meta.get("caption"),
                    "column_count": current_meta.get("column_count"),
                    "row_count": current_meta.get("row_count", 0) + next_meta.get("row_count", 0),
                    "column_headers": current_meta.get("column_headers"),
                    "row_headers": current_meta.get("row_headers", []) + next_meta.get("row_headers", []),
                    "type": "data_table",
                    "merged_from": [current_rec['table_index'], next_rec['table_index']]
                }
                
                # Create the new record for the merged table
                new_rec = {
                    "table_index": current_rec["table_index"], # Keep the index of the first table
                    "page": current_rec["page"],
                    "meta": merged_meta,
                    "extraction_status": "success"
                }
                
                merged_records.append(new_rec)
                
                # Skip the next record since it has been merged
                i += 2
                continue

        # If no merge happened, just add the current record
        merged_records.append(current_rec)
        i += 1

    # Re-index all tables to be sequential after merging
    for new_index, rec in enumerate(merged_records, 1):
        rec["table_index"] = new_index

    return merged_records
# ────────────────────────── MAIN WORKFLOW ────────────────────────── #

def main():
    """Main execution block."""
    table_recs, text_recs = [], []
    global_table_index = 1

    for page_no in pages_with_tables:
        if page_no > PAGE_COUNT:
            print(f"Skipping page {page_no} - out of range for PDF with {PAGE_COUNT} pages.")
            continue

        print(f"\nProcessing Page {page_no}...")
        # ---- OCR step (cached) ----
        if page_no in cached_text:
            ocr_json = cached_text[page_no]
            print(f"  -> Found page {page_no} in cache.")
        else:
            ocr_json = ocr_page_pipeline(render_png(page_no), page_no)
            status = "failed" if "error" in ocr_json else "success"
            text_recs.append({"page": page_no, "text_data": ocr_json, "extraction_status": status})
            if status == "success":
                cached_text[page_no] = ocr_json

        if "error" in ocr_json:
            print(f"  -> Skipping page {page_no} due to OCR error.")
            continue
            
        # ---- Extract table blocks based on OCR results ----
        table_blocks = [s["content"] for s in ocr_json.get("sections", []) if s.get("type") == "table"]
        
        if not table_blocks:
            print(f"  -> No tables found by OCR on page {page_no}, though one was expected.")
            continue

        print(f"  -> Found {len(table_blocks)} table(s) on page {page_no}. Analyzing skeletons...")
        
        # ---- Loop through EACH table found by OCR ----
        for i, table_markdown in enumerate(table_blocks, 1):
            print(f"    - Analyzing table {i} of {len(table_blocks)}...")
            meta = analyze_one_table(table_markdown)
            meta.update({"type": "data_table"})
            
            status = "failed" if "error" in meta else "success"
            
            table_recs.append({
                "table_index": global_table_index,
                "page": page_no,
                "meta": meta,
                "extraction_status": status
            })
            
            global_table_index += 1

    # ───────────────── (NEW) Post-Processing Step Call ────────────────── #
    print("\nChecking for tables to merge...")
    final_records = merge_consecutive_tables(table_recs)

    # ─────────────────────── save outputs ──────────────────────────── #
    OUT_TABLE.parent.mkdir(exist_ok=True)
    # Write the FINAL, merged records to the file
    OUT_TABLE.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in final_records), encoding="utf-8")

    if text_recs:
        with OUT_TEXT.open("a", encoding="utf-8") as f:
            for r in text_recs:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(f"\n✅ Processed and saved a total of {len(final_records)} tables.")
    print("✅ Table JSONL →", OUT_TABLE)
    print("✅ Text JSONL →", OUT_TEXT)

if __name__ == "__main__":
    main()