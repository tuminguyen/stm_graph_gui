import os
import fitz
from PIL import Image
from PyQt6.QtCore import QFileInfo

def check_file_size(file_path, max_size_mb=4):
    """Check if file size exceeds max_size_mb (in MB)."""
    file_info = QFileInfo(file_path)
    file_size_mb = file_info.size() / (1024 * 1024)  # Convert bytes to MB
    return file_size_mb >= max_size_mb

def generate_rasterized_pdf(input_pdf_path, output_pdf_path, dpi=200):
    """Generate a rasterized version of the PDF by scale."""
    pdf_doc = fitz.open(input_pdf_path)
    page = pdf_doc.load_page(0) 
    original_width = page.rect.width
    original_height = page.rect.height
    zoom = dpi / 72 
    matrix = fitz.Matrix(zoom, zoom) 
    pix = page.get_pixmap(matrix=matrix) 
    img = Image.frombytes('RGB', [pix.width, pix.height], pix.samples)
    target_width = int(original_width * zoom)
    target_height = int(original_height * zoom)
    img = img.resize((target_width, target_height), Image.Resampling.LANCZOS)  # Use LANCZOS for high-quality resampling
    img.save(output_pdf_path)

def filter_pdf(pdf_files):
    """List PDFs with prioritize rasterized versions."""
    display_files = pdf_files.copy()
    for pdf in pdf_files:
        base_name, _ = os.path.splitext(pdf)
        if base_name.endswith("_rasterized"):
            display_files.remove(base_name[:-11] + ".pdf")
    return display_files

def rasterize_process_check(out_prepocess_dir):
    print(f"Generate additional rasterized version for big files in {out_prepocess_dir}")
    pdfs = sorted(os.path.join(out_prepocess_dir, fn)
        for fn in os.listdir(out_prepocess_dir) if fn.lower().endswith(".pdf")
    )
    for x in pdfs:
        if check_file_size(x, max_size_mb=8):
            base_name, ext = os.path.splitext(x)
            x_rasterized = base_name + "_rasterized" + ext
            generate_rasterized_pdf(x, x_rasterized)
            print(f"|-- Rasterized version of {x} generated and saved")
