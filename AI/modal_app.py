"""
Issue #233 real migration -- deploys the actual production FastAPI service
(main.py's real `app`, same /process and /apply-redaction contract BE
already calls) onto a Modal-hosted GPU container. No application code
changes: module2_ocr_extraction's own model caching and main.py's
_process_lock work exactly as they do in the local CPU Docker image --
Modal's own autoscaling (spinning up additional container instances under
load) is what actually answers #195's one-request-at-a-time bottleneck,
not a code change here.

Deploy:
    ./venv/Scripts/modal.exe deploy modal_app.py

Then point BE at the printed https://...modal.run URL via the
AI_SERVICE_URL env var (docker-compose.yaml / application.properties) --
this is an alternate deployment target, not a replacement for the local
CPU Docker path, which stays the default for local dev (graceful
degradation / offline dev per project rules).
"""

import modal

app = modal.App("hcl-tco-ai-service")

image = (
    modal.Image.debian_slim(python_version="3.12")
    # Matches AI/Dockerfile post-#246 exactly -- no tesseract-ocr packages
    # (confirmed unused, zero pytesseract.* calls in any shipped file).
    # libreoffice-writer: issue #208's docx->pdf redaction-preview path.
    .apt_install("libgl1", "libglib2.0-0", "libreoffice-writer")
    .pip_install(
        "fastapi==0.141.1",
        "uvicorn==0.52.1",
        "python-multipart==0.0.32",
        "opencv-python==5.0.0.93",
        "numpy==2.3.5",
        "pytesseract==0.3.13",
        "pillow==12.3.0",
        "pypdfium2==5.10.1",
        "python-docx==1.2.0",
        "paddleocr==3.7.0",
        "paddlex[ocr]==3.7.2",
        "onnxruntime==1.28.0",
    )
    # GPU build, not the CPU paddlepaddle==3.3.1 pinned in requirements.txt
    # -- the wheel bundles its own CUDA runtime, no local CUDA/cuDNN setup
    # needed on Modal's side per PaddlePaddle's own install docs. Recipe
    # proven working in modal_gpu_benchmark.py's own real measurement.
    .pip_install(
        "paddlepaddle-gpu==3.3.0",
        extra_index_url="https://www.paddlepaddle.org.cn/packages/stable/cu126/",
    )
    # Full real production import chain -- matches AI/Dockerfile's COPY
    # list exactly (main.py + demo.py included, unlike the benchmark).
    .add_local_python_source(
        "field_extraction",
        "field_extraction_en",
        "module1_opencv",
        "module2_ocr_extraction",
        "module2_text_extraction",
        "module3_redaction",
        "module4_loan_rules",
        "income_normalization",
        "file_routing",
        "pipeline",
        "main",
        "demo",
    )
)


@app.function(
    image=image,
    gpu="T4",
    timeout=600,
    # Keeps a container warm for 5min after its last request before
    # scaling to zero -- absorbs a real demo/testing burst without paying
    # a ~30-60s PPStructureV3 cold-start on every single request, while
    # still scaling to zero (the $30/mo free-tier assumption from #233's
    # research) once actually idle.
    scaledown_window=300,
)
@modal.asgi_app()
def fastapi_app():
    from main import app as real_app

    return real_app
