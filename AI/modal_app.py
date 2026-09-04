"""
Issue #233 real migration -- deploys the actual production FastAPI service
(main.py's real `app`, same /process and /apply-redaction contract BE
already calls) onto a Modal-hosted GPU container. No application code
changes: module2_ocr_extraction's own model caching and main.py's
_process_lock work exactly as they do in the local CPU Docker image --
Modal's own autoscaling (spinning up additional container instances under
load) is what actually answers #195's one-request-at-a-time bottleneck,
not a code change here.

Issue #254 -- promoted to use Modal's GPU Memory Snapshots (alpha,
https://modal.com/docs/guide/memory-snapshots) after validating it on an
isolated experiment app first (hcl-tco-ai-service-snapshot-experiment,
never wired to BE). Real, confirmed result across two independent
cold-restore cycles: ~21-30s cold start, down from ~74s without
snapshotting -- both correct (bit-exact field extraction against the
known-good result). Still an alpha Modal feature ("test carefully before
using in production" -- Modal's own docs); accepted given the real,
repeated measurement.

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
    # Matches AI/Dockerfile post-#246/real-audit fix exactly -- no
    # tesseract-ocr packages (confirmed unused, zero pytesseract.* calls
    # in any shipped file). libgomp1: paddlepaddle's own OpenMP runtime
    # dep, real and standalone -- without it, a container whose first
    # real request takes the text-native-PDF path (which still calls into
    # PPStructureV3 for table-structure harvesting, #170) fails outright
    # with "libgomp.so.1: cannot open shared object file", confirmed live
    # against this exact image before this fix. libreoffice-writer: issue
    # #208's docx->pdf redaction-preview path.
    .apt_install("libgl1", "libglib2.0-0", "libgomp1", "libreoffice-writer")
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
        # Issue #270 -- spaCy NER fallback (field_extraction_en.py's `name`
        # field), same pin as requirements.txt. Missing here left this
        # image unable to cold-start at all (ModuleNotFoundError on any
        # container that wasn't already warm/snapshotted from before #270).
        "spacy==3.8.16",
        "https://github.com/explosion/spacy-models/releases/download/en_core_web_sm-3.8.0/en_core_web_sm-3.8.0-py3-none-any.whl#egg=en_core_web_sm==3.8.0",
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


@app.cls(
    image=image,
    gpu="T4",
    timeout=600,
    # Keeps a container warm for 5min after its last request before
    # scaling to zero -- absorbs a real demo/testing burst without paying
    # a cold-start on every single request, while still scaling to zero
    # (the $30/mo free-tier assumption from #233's research) once
    # actually idle. With #254's snapshotting, even the next cold start
    # after that is real and fast (~21-30s measured), not the ~74s a
    # non-snapshotted cold start costs.
    scaledown_window=300,
    enable_memory_snapshot=True,
    experimental_options={"enable_gpu_snapshot": True},
)
class AIService:
    @modal.enter(snap=True)
    def warm_models(self):
        # Eagerly construct both pipelines (PPStructureV3 for the real
        # /process path, plain PaddleOCR for word-box reconstruction)
        # BEFORE Modal takes the snapshot, so a restored container has
        # real, already-loaded GPU weights instead of reconstructing from
        # scratch on every cold start.
        from module2_ocr_extraction import _get_pipeline, _get_word_pipeline

        _get_pipeline("en")
        _get_word_pipeline("en")

    @modal.asgi_app()
    def fastapi_app(self):
        from main import app as real_app

        return real_app
