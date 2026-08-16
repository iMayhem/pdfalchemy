"""
Command-line interface for PDFAlchemy.
"""
import argparse
import sys
from pathlib import Path

from .core.extractor import StreamingExtractor
from .core.converter import ConverterFactory
from .core.editor import PDFEditor


def main():
    parser = argparse.ArgumentParser(
        description="PDFAlchemy - Transform PDFs into editable formats",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  pdfalchemy input.pdf -o output.docx
  pdfalchemy input.pdf -f markdown -o output.md
  pdfalchemy edit input.pdf --watermark "CONFIDENTIAL" -o watermarked.pdf
        """
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Convert command
    convert_parser = subparsers.add_parser("convert", help="Convert PDF to editable format")
    convert_parser.add_argument("input", help="Input PDF file")
    convert_parser.add_argument("-o", "--output", help="Output file path")
    convert_parser.add_argument(
        "-f", "--format", default="docx",
        choices=["docx", "html", "md", "markdown", "json"],
        help="Output format (default: docx)"
    )
    convert_parser.add_argument("--no-page-breaks", action="store_true",
                               help="Disable page breaks in output")

    # Edit command
    edit_parser = subparsers.add_parser("edit", help="Edit PDF operations")
    edit_parser.add_argument("input", help="Input PDF file")
    edit_parser.add_argument("-o", "--output", required=True, help="Output file path")
    edit_parser.add_argument("--split", nargs=2, type=int, metavar=("START", "END"),
                            action="append", help="Split range (1-indexed, repeatable)")
    edit_parser.add_argument("--rotate", type=int, help="Rotate all pages by degrees")
    edit_parser.add_argument("--watermark", type=str, help="Add text watermark")
    edit_parser.add_argument("--compress", action="store_true", help="Compress PDF")
    edit_parser.add_argument("--extract-images", type=str, metavar="DIR",
                            help="Extract images to directory")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: File not found: {input_path}", file=sys.stderr)
        sys.exit(1)

    if args.command == "convert":
        if args.output:
            output_path = Path(args.output)
        else:
            output_path = input_path.with_suffix(f".{args.format}")

        format_type = args.format
        if args.output and not args.format:
            format_type = output_path.suffix.lstrip(".")

        print(f"Converting {input_path} → {output_path} ({format_type})")

        with StreamingExtractor(str(input_path)) as extractor:
            print(f"Pages: {len(extractor.doc)}")
            converter = ConverterFactory.get_converter(format_type, extractor)
            converter.convert(str(output_path), page_breaks=not args.no_page_breaks)

        print(f"✓ Conversion complete: {output_path}")

    elif args.command == "edit":
        editor = PDFEditor(str(input_path))

        if args.watermark:
            editor.watermark(args.watermark, args.output)
            print(f"✓ Watermarked: {args.output}")
        elif args.rotate:
            import fitz
            total_pages = len(fitz.open(args.input))
            editor.rotate(list(range(1, total_pages + 1)), args.rotate, args.output)
            print(f"✓ Rotated: {args.output}")
        elif args.compress:
            editor.compress(args.output)
            print(f"✓ Compressed: {args.output}")
        elif args.extract_images:
            files = editor.extract_images(args.extract_images)
            print(f"✓ Extracted {len(files)} images to {args.extract_images}")
        elif args.split:
            prefix = str(Path(args.output).with_suffix(""))
            editor.split([(r[0], r[1]) for r in args.split], prefix)
            print(f"✓ Split complete")
        else:
            print("No edit operation specified", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()
