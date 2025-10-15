import fitz  # PyMuPDF
import pytesseract
from PIL import Image
import io

OCR_ENABLED = True  # Set to False if you want to skip OCR fallback

def extract_text_from_pdf(file_path):
    try:
        doc = fitz.open(file_path)
    except Exception as e:
        return None, f"❌ Failed to open PDF: {e}"

    try:
        all_text = []
        for page_num, page in enumerate(doc):
            text = page.get_text().strip()

            # Fallback to OCR if needed
            if not text and OCR_ENABLED:
                pix = page.get_pixmap(dpi=300)
                image = Image.open(io.BytesIO(pix.tobytes("png")))
                text = pytesseract.image_to_string(image).strip()
                if not text:
                    return None, f"❌ Page {page_num + 1} contains no readable text, even via OCR."

            elif not text:
                return None, f"❌ Page {page_num + 1} contains no extractable text and OCR is disabled."

            all_text.append(text)

        doc.close()

        if not all_text:
            return None, "❌ PDF contains no readable text."
        return "\n".join(all_text), None

    except Exception as e:
        doc.close()
        return None, f"❌ Error while processing PDF: {e}"
