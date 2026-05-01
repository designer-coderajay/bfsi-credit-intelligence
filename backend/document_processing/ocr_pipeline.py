"""
OCR Pipeline for loan documents.
Uses PyMuPDF for PDF text extraction + Surya OCR for scanned/image PDFs.
Handles: bank statements, salary slips, ITR, KYC documents.
"""
import logging
import base64
from pathlib import Path
import fitz  # PyMuPDF

logger = logging.getLogger(__name__)


class OCRPipeline:
    """Multi-strategy document text extractor."""

    async def extract_text(self, file_path: str) -> str:
        """
        Extract text from a document using the best available strategy.
        Strategy order: PyMuPDF native → Surya OCR (for scanned)
        """
        path = Path(file_path)
        if not path.exists():
            logger.warning(f"File not found: {file_path}")
            return ""

        if path.suffix.lower() == ".pdf":
            return await self._extract_pdf(str(path))
        else:
            return await self._extract_image(str(path))

    async def _extract_pdf(self, pdf_path: str) -> str:
        """Extract text from PDF — native first, OCR if needed."""
        try:
            doc = fitz.open(pdf_path)
            text_parts = []

            for page_num, page in enumerate(doc):
                text = page.get_text("text").strip()

                if len(text) < 50:
                    # Likely scanned — use Surya OCR
                    logger.info(f"Page {page_num+1} appears scanned, applying OCR")
                    ocr_text = await self._surya_ocr_page(page)
                    text_parts.append(f"[Page {page_num+1}]\n{ocr_text}")
                else:
                    text_parts.append(f"[Page {page_num+1}]\n{text}")

            doc.close()
            return "\n\n".join(text_parts)

        except Exception as e:
            logger.error(f"PDF extraction failed for {pdf_path}: {e}")
            return ""

    async def _surya_ocr_page(self, page: fitz.Page) -> str:
        """Apply Surya OCR to a single PDF page."""
        try:
            from surya.ocr import run_ocr
            from surya.model.detection.model import load_model as load_det_model
            from surya.model.recognition.model import load_model as load_rec_model
            from PIL import Image
            import io

            # Render page to image
            mat = fitz.Matrix(2.0, 2.0)  # 2x zoom for better OCR
            pix = page.get_pixmap(matrix=mat)
            img_bytes = pix.tobytes("png")
            image = Image.open(io.BytesIO(img_bytes))

            det_model, det_processor = load_det_model(), None
            rec_model, rec_processor = load_rec_model(), None

            predictions = run_ocr(
                [image],
                [["en", "hi"]],  # English + Hindi support
                det_model, det_processor,
                rec_model, rec_processor,
            )
            return " ".join([line.text for page_pred in predictions for line in page_pred.text_lines])

        except ImportError:
            logger.warning("Surya OCR not installed. Falling back to empty text.")
            return ""
        except Exception as e:
            logger.error(f"Surya OCR failed: {e}")
            return ""

    async def _extract_image(self, image_path: str) -> str:
        """Extract text from image file using OCR."""
        try:
            from surya.ocr import run_ocr
            from PIL import Image

            image = Image.open(image_path)
            predictions = run_ocr([image], [["en", "hi"]], None, None, None, None)
            return " ".join([line.text for page_pred in predictions for line in page_pred.text_lines])
        except Exception as e:
            logger.error(f"Image OCR failed: {e}")
            return ""
