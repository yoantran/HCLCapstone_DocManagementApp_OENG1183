FROM python:3.12-slim

# tesseract-ocr: the OCR engine itself (native binary, not a pip package).
# tesseract-ocr-vie/-eng: language packs -- apt installs these into
# Tesseract's own default tessdata location, which module2_ocr_tesseract.py
# now relies on by default in any non-Windows environment (see its
# TESSERACT_CMD/TESSDATA_PREFIX env-var handling).
# libgl1/libglib2.0-0: opencv-python's runtime shared-library dependencies,
# not present in the slim base image.
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-vie \
    tesseract-ocr-eng \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Explicit file list, not `COPY . .` -- excludes venv/, samples/, test_*.py,
# and module2_ocr_tesseract.py, the pre-#127 Vietnamese Tesseract-path file
# pipeline.py no longer imports at all. field_extraction.py stays -- it's
# not itself part of the VN path, field_extraction_en.py imports a shared
# helper from it (_clean_label_value).
COPY field_extraction.py \
     field_extraction_en.py \
     module1_opencv.py \
     module2_ocr_extraction.py \
     module2_text_extraction.py \
     module3_redaction.py \
     module4_loan_rules.py \
     income_normalization.py \
     file_routing.py \
     pipeline.py \
     main.py \
     ./

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
