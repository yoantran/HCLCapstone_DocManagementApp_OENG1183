FROM python:3.12-slim

# libgl1/libglib2.0-0: opencv-python's runtime shared-library dependencies,
# not present in the slim base image.
# libgomp1: paddlepaddle's own OpenMP runtime dependency for its compiled
# ops -- real, standalone requirement, unrelated to tesseract. Was never
# declared explicitly; happened to work before #246 only because
# tesseract-ocr pulled it in transitively, which masked the real gap.
# #246 removing tesseract (correctly -- confirmed unused) exposed it: a
# freshly started container whose first real request takes the
# text-native-PDF path (pipeline.py's _run_text_native_path, which still
# calls into module2_ocr_extraction for table-structure harvesting, #170)
# fails outright with "libgomp.so.1: cannot open shared object file",
# confirmed by triggering it for real through a live upload -- the
# image-OCR path happening to work in earlier testing was request-order
# luck, not a real fix. Declared explicitly now so paddle's dlopen always
# finds it on the standard system path, regardless of which code path a
# container's first request happens to take.
# libreoffice-writer: issue #208 -- text-native docx redacted previews
# convert docx->pdf via `soffice --headless` (file_routing.py's
# convert_docx_to_pdf_bytes) before rendering/searching, same as the
# offline benchmark script (measure_accuracy_image.py) already does.
# writer-only component, not the full libreoffice suite -- smaller image,
# and nothing else in this pipeline touches Calc/Impress documents.
#
# No tesseract-ocr/-vie/-eng here -- the only file that ever called the
# tesseract binary (module2_ocr_tesseract.py, the pre-#127 Vietnamese path)
# is explicitly excluded from the COPY list below and was never shipped in
# this image. Confirmed zero `pytesseract.*` calls across every file that
# IS shipped -- these apt packages were pure dead weight in every built
# image since PPStructureV3 became the production OCR engine (#129).
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libgomp1 \
    libreoffice-writer \
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
     demo.py \
     ./

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
