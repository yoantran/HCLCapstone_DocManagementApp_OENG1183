"""
PRODUCTION image-path OCR module (58.8%, up from PaddleOCR's 23.8% -- see
issue #116). A future FastAPI /process endpoint should import extract_fields
from here for image/scanned-document input, not from module2_ocr_extraction.

Tesseract-based alternative to module2_ocr_extraction.py's image path, for
comparing against PaddleOCR on Vietnamese diacritic recognition specifically
(see field_extraction dict-coverage findings in issue #116 -- no official
PaddleOCR/PaddleX model has real Vietnamese character coverage). Tesseract's
`vie` trained-data language pack is a genuinely different recognition engine
and vocabulary, not just a different PaddleOCR model size/tier. Measured
55.0% (38-doc batch) against PaddleOCR's 23.8% and two other engine/hybrid
attempts that scored worse (see issue #116, Updates 3-6) -- the standing
best result for the image/OCR path.

extract_by_proximity() closes part of the remaining gap: colon-less
label/value layouts (the same problem table-cell-pairing solved for the
DOCX branch) using Tesseract's own `image_to_data` word boxes, grouped into
lines, instead of PPStructureV3's table structure -- Tesseract does no
layout/table detection of its own, so this is the only source of position
data available here. Scoped to name/address only, matching
field_extraction.py's existing `_BARE_LABEL_RE` convention: phone/cccd/salary
are strict-format regexes that scan the whole text position-independently,
so they were never pairing-dependent -- and a real check on a failing
payslip confirmed the salary digits aren't merely misplaced, they're not
transcribed anywhere in the page's text at all, so pairing can't recover
that specific failure mode either.
"""

import os

import numpy as np
import pytesseract
from PIL import Image
from pytesseract import Output

from field_extraction import (
    _BARE_LABEL_RE,
    _BOILERPLATE_RE,
    _clean_label_value,
    extract_fields_from_text,
    restore_name_diacritics,
)

# Local Windows dev installs Tesseract at a fixed path with traineddata
# staged under ~/.tessdata (not the system default location) -- neither is
# true in a Linux container, where `apt-get install tesseract-ocr
# tesseract-ocr-vie` puts the binary on PATH and traineddata in Tesseract's
# own default tessdata dir already. TESSERACT_CMD/TESSDATA_PREFIX env vars
# override for any environment; otherwise fall back to the Windows-dev
# defaults only on Windows, and leave pytesseract's own PATH-based default
# untouched everywhere else (correct for the container).
_tesseract_cmd = os.environ.get(
    "TESSERACT_CMD", r"C:\Program Files\Tesseract-OCR\tesseract.exe" if os.name == "nt" else None
)
if _tesseract_cmd:
    pytesseract.pytesseract.tesseract_cmd = _tesseract_cmd

_tessdata_prefix = os.environ.get(
    "TESSDATA_PREFIX", os.path.expanduser("~/.tessdata") if os.name == "nt" else None
)
if _tessdata_prefix:
    os.environ["TESSDATA_PREFIX"] = _tessdata_prefix

_TESS_CONFIG = "--oem 1 --psm 6"


def _to_pil(image: np.ndarray) -> Image.Image:
    # module1_opencv.enhance()["image"] is grayscale (2D); a raw cv2.imread
    # result is BGR (3-channel) -- handle both, same as module2_ocr_extraction.
    if image.ndim == 2:
        return Image.fromarray(image)
    return Image.fromarray(image[:, :, ::-1])


def ocr_text(image, lang: str = "vie") -> str:
    return pytesseract.image_to_string(_to_pil(image), lang=lang, config=_TESS_CONFIG)


def _word_data(image, lang: str = "vie") -> dict:
    return pytesseract.image_to_data(_to_pil(image), lang=lang, config=_TESS_CONFIG, output_type=Output.DICT)


def _group_lines(data: dict) -> list[dict]:
    """Tesseract's image_to_data gives per-word boxes with block/paragraph/line
    indices -- group words sharing those indices back into line-level boxes,
    the same shape as PaddleOCR's line_boxes, so the same proximity logic
    applies regardless of which engine produced the detection."""
    lines: dict[tuple, dict] = {}
    for i, word in enumerate(data["text"]):
        word = word.strip()
        if not word or int(data["conf"][i]) < 0:
            continue
        key = (data["block_num"][i], data["par_num"][i], data["line_num"][i])
        x, y, w, h = data["left"][i], data["top"][i], data["width"][i], data["height"][i]
        line = lines.setdefault(key, {"words": [], "x1": x, "y1": y, "x2": x + w, "y2": y + h})
        line["words"].append((x, word))
        line["x1"] = min(line["x1"], x)
        line["y1"] = min(line["y1"], y)
        line["x2"] = max(line["x2"], x + w)
        line["y2"] = max(line["y2"], y + h)

    result = []
    for line in lines.values():
        text = " ".join(w for _, w in sorted(line["words"], key=lambda t: t[0]))
        result.append({"text": text, "box": (line["x1"], line["y1"], line["x2"], line["y2"])})
    return sorted(result, key=lambda l: (l["box"][1], l["box"][0]))


def _build_word_reconstruction(data: dict) -> tuple[str, list[dict]]:
    """Joins image_to_data's words into one string in the same reading
    order _group_lines() already establishes (grouped by block/par/line,
    lines sorted top-to-bottom/left-to-right, words sorted left-to-right
    within a line), returning a parallel list recording each word's exact
    character span in that string -- the offset map find_sensitive_boxes()
    (module3_redaction.py) uses to locate a regex match's box(es)."""
    lines: dict[tuple, list[dict]] = {}
    for i, word in enumerate(data["text"]):
        word = word.strip()
        if not word or int(data["conf"][i]) < 0:
            continue
        key = (data["block_num"][i], data["par_num"][i], data["line_num"][i])
        x, y, w, h = data["left"][i], data["top"][i], data["width"][i], data["height"][i]
        lines.setdefault(key, []).append({"word": word, "box": (x, y, x + w, y + h)})

    ordered_lines = []
    for words in lines.values():
        words.sort(key=lambda w: w["box"][0])
        y1 = min(w["box"][1] for w in words)
        x1 = min(w["box"][0] for w in words)
        ordered_lines.append((y1, x1, words))
    ordered_lines.sort(key=lambda t: (t[0], t[1]))

    text_parts = []
    word_spans = []
    pos = 0
    for _, _, words in ordered_lines:
        for j, w in enumerate(words):
            if j > 0:
                text_parts.append(" ")
                pos += 1
            text_parts.append(w["word"])
            word_spans.append({"word": w["word"], "box": w["box"], "start": pos, "end": pos + len(w["word"])})
            pos += len(w["word"])
        text_parts.append("\n")
        pos += 1

    return "".join(text_parts), word_spans


def _looks_like_label(text: str) -> bool:
    return any(p.search(text) for p in _BARE_LABEL_RE.values())


def _is_bad_candidate(text: str) -> bool:
    return _looks_like_label(text) or bool(_BOILERPLATE_RE.search(text))


def extract_by_proximity(lines: list[dict]) -> dict:
    result: dict[str, str] = {}
    for line in lines:
        text = line["text"].strip()
        if not text:
            continue
        x1, y1, x2, y2 = line["box"]
        height = y2 - y1

        for field, pattern in _BARE_LABEL_RE.items():
            if result.get(field):
                continue
            match = pattern.search(text)
            if not match:
                continue

            # same line: "Label: value" or "Label value" (no colon). A tail
            # that itself looks like another label isn't a value -- e.g. a
            # signature block with two side-by-side columns ("... Ký và ghi
            # rõ họ tên | ... Ký và ghi rõ họ tên") merges into one Tesseract
            # line, and the trailing copy would otherwise be accepted as the
            # first copy's "value" purely by sitting after it on the line.
            colon_idx = text.find(":", match.end())
            if colon_idx != -1:
                candidate = _clean_label_value(text[colon_idx + 1:])
            else:
                candidate = _clean_label_value(text[match.end():].strip(" :"))
            if candidate and not _looks_like_label(candidate):
                result[field] = candidate
                continue

            # colon-less standalone header: nearest line below with x-overlap.
            # Reject a candidate that itself looks like another label (e.g. a
            # "Ký và ghi rõ họ tên" signature-block prompt sitting below a
            # name header and getting grabbed as the "value" purely because
            # it's the nearest x-overlapping line and contains "tên" too) --
            # a real value line is never itself a label phrase.
            best, best_dist = None, None
            for other in lines:
                other_text = other["text"].strip()
                if other is line or not other_text:
                    continue
                if _looks_like_label(other_text):
                    continue
                ox1, oy1, ox2, oy2 = other["box"]
                overlaps_x = ox1 < x2 and ox2 > x1
                below = oy1 >= y2
                if not (overlaps_x and below):
                    continue
                dist = oy1 - y2
                if dist < 0 or dist > height * 4:
                    continue
                if best_dist is None or dist < best_dist:
                    best, best_dist = other, dist
            if best:
                candidate = _clean_label_value(best["text"].strip())
                if candidate:
                    result[field] = candidate
    return result


def extract_fields(image, lang: str = "vie") -> dict:
    data = _word_data(image, lang=lang)
    text, _ = _build_word_reconstruction(data)
    fields = extract_fields_from_text(text)

    missing = [f for f in ("name", "address") if not fields.get(f)]
    if missing:
        lines = _group_lines(data)
        proximity_fields = extract_by_proximity(lines)
        for f in missing:
            if proximity_fields.get(f):
                fields[f] = proximity_fields[f]
        fields["name"] = restore_name_diacritics(fields.get("name"))

    return {"fields": fields, "text": text}
