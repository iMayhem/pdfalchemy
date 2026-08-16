"""
Semantic PDF extraction with layout preservation.
Streams pages one at a time — ideal for low-RAM VPS environments.
"""
import fitz
import json
from dataclasses import dataclass, asdict
from typing import List, Optional, Dict, Any, Iterator
from pathlib import Path
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)


@dataclass
class TextBlock:
    text: str
    bbox: tuple
    font: str
    size: float
    flags: int
    color: int
    page_num: int
    block_type: str = "text"


@dataclass
class PageLayout:
    page_num: int
    width: float
    height: float
    blocks: List[TextBlock]
    images: List[Dict[str, Any]]
    tables: List[Dict[str, Any]]
    rotation: int = 0


class StreamingExtractor:
    """
    Memory-efficient extractor that yields pages one at a time.
    Perfect for VPS with limited RAM processing large PDFs.
    """

    def __init__(self, pdf_path: str, dpi: int = 150):
        self.pdf_path = Path(pdf_path)
        self.dpi = dpi
        self.doc = None

    def __enter__(self):
        self.doc = fitz.open(self.pdf_path)
        return self

    def __exit__(self, *args):
        if self.doc:
            self.doc.close()

    def extract_page(self, page_num: int) -> PageLayout:
        """Extract single page with full layout analysis."""
        page = self.doc[page_num]
        blocks = []
        dict_page = page.get_text("dict")

        for block in dict_page.get("blocks", []):
            if block.get("type") == 0:
                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        block_type = self._classify_block(span, page.rect.height)
                        blocks.append(TextBlock(
                            text=span["text"],
                            bbox=span["bbox"],
                            font=span["font"],
                            size=span["size"],
                            flags=span["flags"],
                            color=span["color"],
                            page_num=page_num,
                            block_type=block_type
                        ))

        images = []
        for img_index, img in enumerate(page.get_images(full=True)):
            xref = img[0]
            base_image = self.doc.extract_image(xref)
            images.append({
                "index": img_index,
                "ext": base_image["ext"],
                "width": base_image["width"],
                "height": base_image["height"],
                "xref": xref
            })

        tables = self._detect_tables(blocks)

        return PageLayout(
            page_num=page_num,
            width=page.rect.width,
            height=page.rect.height,
            blocks=blocks,
            images=images,
            tables=tables,
            rotation=page.rotation
        )

    def _classify_block(self, span: Dict, page_height: float) -> str:
        """Classify text block as header, footer, body, heading, etc."""
        y_pos = span["bbox"][1]
        size = span["size"]
        flags = span["flags"]

        if y_pos < page_height * 0.08:
            return "header"
        if y_pos > page_height * 0.92:
            return "footer"
        if size > 14 or (flags & 2 ** 4):
            return "heading"
        if size < 9:
            return "caption"
        return "body"

    def _detect_tables(self, blocks: List[TextBlock]) -> List[Dict]:
        """Detect table structures from text block alignment."""
        tables = []
        rows = defaultdict(list)

        for block in blocks:
            y_key = round(block.bbox[1] / 5) * 5
            rows[y_key].append(block)

        sorted_y = sorted(rows.keys())
        table_blocks = []
        current_table = []

        for y in sorted_y:
            row_blocks = sorted(rows[y], key=lambda b: b.bbox[0])
            if len(row_blocks) >= 2:
                current_table.append(row_blocks)
            else:
                if len(current_table) >= 2:
                    table_blocks.append(current_table)
                current_table = []

        if len(current_table) >= 2:
            table_blocks.append(current_table)

        for idx, table in enumerate(table_blocks):
            tables.append({
                "index": idx,
                "rows": len(table),
                "cols": max(len(row) for row in table),
                "cells": [[cell.text for cell in row] for row in table]
            })

        return tables

    def stream_pages(self) -> Iterator[PageLayout]:
        """Yield pages one at a time for memory efficiency."""
        for i in range(len(self.doc)):
            yield self.extract_page(i)

    def extract_all(self) -> List[PageLayout]:
        """Extract all pages (not recommended for large files)."""
        return list(self.stream_pages())
