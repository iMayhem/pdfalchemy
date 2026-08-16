"""
PDF editing operations: merge, split, rotate, watermark, redact, compress.
"""
from pathlib import Path
from typing import List, Tuple
import fitz
import pikepdf


class PDFEditor:
    """
    Non-destructive PDF editor.
    All operations create new files, preserving the original.
    """

    def __init__(self, pdf_path: str):
        self.source_path = Path(pdf_path)
        self.operations = []

    def merge(self, other_pdfs: List[str], output_path: str) -> str:
        """Merge multiple PDFs into one."""
        pdf = pikepdf.open(self.source_path)
        for other_path in other_pdfs:
            other = pikepdf.open(other_path)
            pdf.pages.extend(other.pages)
            other.close()
        pdf.save(output_path)
        pdf.close()
        self.operations.append(f"merged with {len(other_pdfs)} files")
        return output_path

    def split(self, ranges: List[Tuple[int, int]], output_prefix: str) -> List[str]:
        """
        Split PDF into multiple files.
        ranges: list of (start, end) page tuples (1-indexed)
        """
        pdf = pikepdf.open(self.source_path)
        outputs = []

        for i, (start, end) in enumerate(ranges):
            new_pdf = pikepdf.Pdf.new()
            for page_num in range(start - 1, min(end, len(pdf.pages))):
                new_pdf.pages.append(pdf.pages[page_num])
            output_path = f"{output_prefix}_part{i+1}.pdf"
            new_pdf.save(output_path)
            new_pdf.close()
            outputs.append(output_path)

        pdf.close()
        self.operations.append(f"split into {len(ranges)} parts")
        return outputs

    def rotate(self, pages: List[int], degrees: int, output_path: str) -> str:
        """Rotate specific pages."""
        pdf = pikepdf.open(self.source_path)
        for page_num in pages:
            if 1 <= page_num <= len(pdf.pages):
                page = pdf.pages[page_num - 1]
                current_rot = page.Rotate if "/Rotate" in page else 0
                page.Rotate = (current_rot + degrees) % 360
        pdf.save(output_path)
        pdf.close()
        self.operations.append(f"rotated {len(pages)} pages by {degrees}°")
        return output_path

    def watermark(self, text: str, output_path: str, 
                  opacity: float = 0.3, fontsize: int = 60) -> str:
        """Add text watermark to all pages."""
        doc = fitz.open(self.source_path)
        for page in doc:
            rect = page.rect
            page.insert_text(
                (rect.width / 2, rect.height / 2),
                text,
                fontsize=fontsize,
                color=(0.5, 0.5, 0.5),
                opacity=opacity,
                rotate=45,
                overlay=True
            )
        doc.save(output_path)
        doc.close()
        self.operations.append(f"added watermark '{text}'")
        return output_path

    def redact(self, page_num: int, bbox: Tuple[float, float, float, float], 
               output_path: str) -> str:
        """Redact a rectangular area on a specific page."""
        doc = fitz.open(self.source_path)
        page = doc[page_num - 1]
        rect = fitz.Rect(bbox)
        page.add_redact_annot(rect, fill=(0, 0, 0))
        page.apply_redactions()
        doc.save(output_path)
        doc.close()
        self.operations.append(f"redacted page {page_num}")
        return output_path

    def extract_images(self, output_dir: str) -> List[str]:
        """Extract all images from PDF."""
        doc = fitz.open(self.source_path)
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        extracted = []
        for page_num in range(len(doc)):
            page = doc[page_num]
            images = page.get_images(full=True)
            for img_index, img in enumerate(images):
                xref = img[0]
                base_image = doc.extract_image(xref)
                filename = output_path / f"page{page_num+1}_img{img_index+1}.{base_image['ext']}"
                with open(filename, "wb") as f:
                    f.write(base_image["image"])
                extracted.append(str(filename))

        doc.close()
        self.operations.append(f"extracted {len(extracted)} images")
        return extracted

    def compress(self, output_path: str) -> str:
        """Compress PDF using pikepdf optimization."""
        pdf = pikepdf.open(self.source_path)
        pdf.save(
            output_path, 
            compress_streams=True,
            object_stream_mode=pikepdf.ObjectStreamMode.generate
        )
        pdf.close()
        self.operations.append("compressed")
        return output_path
