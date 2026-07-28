import csv
from pathlib import Path

import docx
import pypdfium2 as pdfium

from field_extraction import extract_fields_from_text


def extract_text_from_docx(path: str) -> str:
    doc = docx.Document(path)
    parts = [p.text for p in doc.paragraphs if p.text.strip()]
    for table in doc.tables:
        for row in table.rows:
            parts.append(" ".join(cell.text for cell in row.cells))
    return "\n".join(parts)


def extract_text_from_csv(path: str) -> str:
    with open(path, encoding="utf-8-sig", newline="") as f:
        return "\n".join(" ".join(row) for row in csv.reader(f))


def extract_text_from_pdf(path: str) -> str:
    pdf = pdfium.PdfDocument(path)
    pages = [page.get_textpage().get_text_range() for page in pdf]
    return "\n".join(pages)


_EXTRACTORS = {
    ".docx": extract_text_from_docx,
    ".csv": extract_text_from_csv,
    ".pdf": extract_text_from_pdf,
}


def extract_text(path: str) -> str:
    ext = Path(path).suffix.lower()
    extractor = _EXTRACTORS.get(ext)
    if extractor is None:
        raise ValueError(f"unsupported text-native format: {ext}")
    return extractor(path)


def extract_fields(path: str) -> dict:
    text = extract_text(path)
    return {"fields": extract_fields_from_text(text), "text": text}


if __name__ == "__main__":
    with open("module2_text_selfcheck_output.txt", "w", encoding="utf-8") as out:
        for name in (
            "samples/Bảng cân đối kế toán năm của doanh nghiệp hoạt động liên tục.docx",
            "samples/[Base.vn] MẪU BẢNG CÂN ĐỐI KẾ TOÁN THEO THÔNG TƯ 200 - Mẫu BCĐKT.pdf",
        ):
            result = extract_fields(name)
            out.write(f"--- {name} ---\n")
            for field, value in result["fields"].items():
                out.write(f"  {field}: {value}\n")
            out.write(f"  text length: {len(result['text'])} chars\n\n")
    print("saved module2_text_selfcheck_output.txt")
