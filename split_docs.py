from pathlib import Path
from math import ceil

from pypdf import PdfReader, PdfWriter     # pip install pypdf

def split_pdf_into_10(in_path: str | Path, out_dir: str | Path = ".") -> None:
    """
    Split *in_path* into 10 separate PDFs written to *out_dir*.
    Files are named  <original_stem>_part01.pdf … _part10.pdf
    """
    in_path  = Path(in_path)
    out_dir  = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    reader        = PdfReader(in_path)
    total_pages   = len(reader.pages)
    pages_per_part = ceil(total_pages / 10)

    for part in range(10):
        start = part * pages_per_part
        end   = min(start + pages_per_part, total_pages)
        if start >= total_pages:          # no more pages left
            break

        writer = PdfWriter()
        for page in range(start, end):
            writer.add_page(reader.pages[page])

        out_file = out_dir / f"{in_path.stem}_part{part+1:02}.pdf"
        with out_file.open("wb") as f:
            writer.write(f)

        print(f"Saved pages {start+1}-{end} ➜ {out_file.name}")

# ---- usage example ----
if __name__ == "__main__":
    split_pdf_into_10("rapport-actionnaire-t1-2025.pdf", out_dir="raws_pdf")
