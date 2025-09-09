import qrcode
import io
from pathlib import Path
import pandas as pd
from typing import Dict, Any, List, Literal

from PyQt6.QtGui import QPixmap, QImage
from PyQt6.QtCore import QBuffer, QIODevice
from PIL import Image as PILImage
import fitz # For PDF preview
from registration.cardgenerator.cardgenerator import generate_card, CardOptions

def load_data(file_path: str) -> tuple[Dict[Any, Dict[str, Any]], List[Any]]:
    """
    Loads data from an Excel file and returns a dictionary mapping NIPs to data
    and a sorted list of NIPs.
    """
    df = pd.read_excel(file_path)
    # Create a mapping for easy lookup
    nip_to_data = {row['NIP Unizar']: row for index, row in df.iterrows()}
    return nip_to_data, sorted(list(nip_to_data.keys()))

def show_qr(data: str) -> QPixmap:
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    
    # Convert PIL Image to QPixmap
    buffer = io.BytesIO()
    img.save(buffer, "PNG")
    qimage = QImage.fromData(buffer.getvalue())
    pixmap = QPixmap.fromImage(qimage)
    return pixmap

def show_pdf_preview(pdf_path: str) -> QPixmap:
    """
    Shows a preview of the PDF using fitz and returns a QPixmap.
    """
    try:
        doc = fitz.open(pdf_path)
        page = doc.load_page(0)
        # Render the page as a high-resolution image
        pix = page.get_pixmap(matrix=fitz.Matrix(3, 3))
        img = PILImage.frombytes("RGB", (pix.width, pix.height), pix.samples) # Convert list to tuple
        doc.close()

        # Convert PIL Image to QPixmap
        buffer = io.BytesIO()
        img.save(buffer, "PNG")
        qimage = QImage.fromData(buffer.getvalue())
        pixmap = QPixmap.fromImage(qimage)
        return pixmap
    except Exception as e:
        print(f"Error loading PDF preview: {e}")
        return QPixmap()