import os
import pytesseract
from PIL import Image

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
os.environ["TESSDATA_PREFIX"] = os.path.expanduser("~/.tessdata")

text = pytesseract.image_to_string(
    Image.open("sample_payslip.png"), lang="vie", config="--oem 1 --psm 6"
)
with open("ocr_output.txt", "w", encoding="utf-8") as f:
    f.write(text)
print("saved ocr_output.txt")
