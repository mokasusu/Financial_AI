
from pathlib import Path
from docling.document_converter import DocumentConverter

def test_docling(pdf_path: str):
    path = Path(pdf_path)

    if not path.exists():
        print(f"Khong tim thay file: {path}")
        return

    converter = DocumentConverter()
    result = converter.convert(str(path))
    document = result.document

    print("\n===== NOI DUNG TRICH XUAT =====")
    text = document.export_to_markdown()
    print(text[:5000])

    print("\n===== KIEM TRA BANG =====")
    tables = document.tables
    print(f"So bang tim thay: {len(tables)}")

    for index, table in enumerate(tables, start=1):
        print(f"\n--- Bang {index} ---")
        print(table.export_to_dataframe().to_string(index=False))

if __name__ == "__main__":
    pdf_path = input("Nhap duong dan file PDF: ").strip().strip('"')
    test_docling(pdf_path)
