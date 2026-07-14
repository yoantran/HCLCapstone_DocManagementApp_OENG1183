import os

import cv2
import numpy as np
import pypdfium2 as pdfium
import pytesseract
from PIL import Image

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
os.environ["TESSDATA_PREFIX"] = os.path.expanduser("~/.tessdata")

SRC = "sample_payslip.png"
DEGRADED_PNG = "sample_payslip_degraded.jpg"
WRAPPED_PDF = "sample_payslip_scanned.pdf"
RENDERED_PNG = "sample_payslip_rendered.png"
OUT_TXT = "ocr_output_degraded.txt"


def degrade(src_path: str, out_path: str) -> None:
    img = cv2.imread(src_path)

    h, w = img.shape[:2]
    matrix = cv2.getRotationMatrix2D((w / 2, h / 2), angle=1.5, scale=1.0)
    img = cv2.warpAffine(img, matrix, (w, h), borderValue=(255, 255, 255))

    img = cv2.GaussianBlur(img, (3, 3), sigmaX=0.6)

    noise = np.random.normal(0, 8, img.shape).astype(np.int16)
    img = np.clip(img.astype(np.int16) + noise, 0, 255).astype(np.uint8)

    cv2.imwrite(out_path, img, [cv2.IMWRITE_JPEG_QUALITY, 60])


def wrap_as_pdf(image_path: str, pdf_path: str) -> None:
    Image.open(image_path).convert("RGB").save(pdf_path, "PDF")


def render_first_page(pdf_path: str, out_png: str) -> None:
    pdf = pdfium.PdfDocument(pdf_path)
    bitmap = pdf[0].render(scale=2.0)
    bitmap.to_pil().save(out_png)


def run_ocr(image_path: str, out_txt: str) -> str:
    text = pytesseract.image_to_string(
        Image.open(image_path), lang="vie", config="--oem 1 --psm 6"
    )
    with open(out_txt, "w", encoding="utf-8") as f:
        f.write(text)
    return text


degrade(SRC, DEGRADED_PNG)
wrap_as_pdf(DEGRADED_PNG, WRAPPED_PDF)
render_first_page(WRAPPED_PDF, RENDERED_PNG)
run_ocr(RENDERED_PNG, OUT_TXT)
print(f"saved {OUT_TXT}")
