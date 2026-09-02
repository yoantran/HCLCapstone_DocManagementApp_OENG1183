import re
import cv2
import numpy as np

from field_extraction_en import (
    ABN_RE,
    PHONE_RE,
    SALARY_RE,
    ANNUAL_SALARY_RE,
    LABEL_PATTERNS,
    INCOME_LABEL_PATTERNS,
    BALANCE_SHEET_VALUE_PATTERNS,
    _BALANCE_SHEET_LABEL_RE,
    _clean_label_value,
    parse_currency_amount,
    parse_currency_amount_balance_sheet,
)

_REGEX_LIST_FIELDS = {
    "abn": ABN_RE,
    "phone": PHONE_RE,
    "salary": SALARY_RE,
}

# Field keys Module 3 is configured to detect and redact -- derived from
# the detectors themselves (not detection results), so a real detection
# miss on a given document degrades to a missing black box rather than
# silently reporting the field as "safe to show raw." annual_salary isn't
# in any of the dicts above (it has its own ANNUAL_SALARY_RE-based
# detector, handled separately in find_sensitive_spans/find_sensitive_boxes
# -- see #305) so it's included explicitly here too, otherwise it would be
# silently omitted from this set despite being a real detected field.
SENSITIVE_FIELD_KEYS = sorted(
    set(_REGEX_LIST_FIELDS)
    | set(LABEL_PATTERNS)
    | set(BALANCE_SHEET_VALUE_PATTERNS)
    | {"income", "annual_salary"}
)


def _cleaned_span(match: re.Match) -> tuple[str, int, int] | None:
    """Given a match whose group(1) is a raw label-anchored capture, return
    (cleaned_value, start, end) covering exactly the substring
    _clean_label_value accepts -- not the raw group, which may include
    leading/trailing whitespace _clean_label_value's .strip() discards."""
    raw = match.group(1)
    cleaned = _clean_label_value(raw)
    if cleaned is None:
        return None
    offset = raw.find(cleaned)
    start = match.start(1) + offset
    return cleaned, start, start + len(cleaned)


# Issue #303 -- candidate finder for the balance-sheet value fallback
# below. Requires a literal "$" prefix -- every real balance-sheet
# dollar figure seen across this whole project's real templates has
# one, and requiring it avoids false-matching an unrelated bare
# number (a page number, a date, a ratio) that happens to equal the
# target. parse_currency_amount_balance_sheet does the real parsing/
# validation; this only needs to generate plausible candidates.
_BALANCE_SHEET_BARE_AMOUNT_RE = re.compile(r"\$\s*\d[\d,.\s]*\d|\$\s*\d")


def find_sensitive_spans(text: str, fields: dict) -> list[dict]:
    spans = []

    for field, pattern in _REGEX_LIST_FIELDS.items():
        if not fields.get(field):
            continue
        for match in pattern.finditer(text):
            spans.append(
                {
                    "field": field,
                    "value": match.group(0),
                    "start": match.start(),
                    "end": match.end(),
                    "detection_method": "regex",
                }
            )

    for field, pattern in LABEL_PATTERNS.items():
        if not fields.get(field):
            continue
        for match in pattern.finditer(text):
            result = _cleaned_span(match)
            if result is None:
                continue
            cleaned, start, end = result
            # Issue #205 -- redact every occurrence of the real value (a
            # repeated name/address/bsb/account_number on a payslip header
            # AND footer both need a box), not just the first. Safe because
            # _matches_accepted_value is an exact string compare against
            # fields[field] -- a different real value that happens to match
            # the same label pattern elsewhere in the document is rejected,
            # not redacted.
            if not _matches_accepted_value(field, cleaned, fields):
                continue
            spans.append(
                {
                    "field": field,
                    "value": cleaned,
                    "start": start,
                    "end": end,
                    "detection_method": "regex",
                }
            )

    # Issue #305 -- annual_salary is in SENSITIVE_FIELD_KEYS (so BE
    # correctly strips it from aiResult.fields) but had no detector here at
    # all: 25/25 real payslips with a correctly-extracted annual_salary got
    # zero redaction spans, leaving the real dollar figure fully visible in
    # the rendered preview. ANNUAL_SALARY_RE's group(1) is already the
    # clean "$67,000" value (not a raw rest-of-line capture), so this can
    # cross-check against the already-parsed target directly -- same
    # "search for the value, not just the label" rigor #289/#303 use.
    if fields.get("annual_salary") is not None:
        target = fields["annual_salary"]
        for match in ANNUAL_SALARY_RE.finditer(text):
            result = _cleaned_span(match)
            if result is None:
                continue
            cleaned, start, end = result
            amount = parse_currency_amount(cleaned)
            if amount is None or abs(amount - target) >= 0.01:
                continue
            spans.append(
                {
                    "field": "annual_salary",
                    "value": cleaned,
                    "start": start,
                    "end": end,
                    "detection_method": "regex",
                }
            )

    if fields.get("income") is not None:
        # income's fields value is a parsed float, not the raw printed
        # string, so (unlike the fields above) there's no exact-match check
        # available to safely redact every occurrence -- a different dollar
        # figure elsewhere in the document (a subtotal, a prior period) can
        # match the same label pattern and would be false-positive-redacted
        # without one. Keep the existing first-match-only behavior here
        # deliberately; fixing this for real needs Module 2 to expose which
        # match it actually parsed the accepted value from, out of scope
        # for #205.
        pattern = INCOME_LABEL_PATTERNS.get(fields.get("income_basis"))
        if pattern is not None:
            for match in pattern.finditer(text):
                result = _cleaned_span(match)
                if result is None:
                    continue
                cleaned, start, end = result
                spans.append(
                    {
                        "field": "income",
                        "value": cleaned,
                        "start": start,
                        "end": end,
                        "detection_method": "regex",
                    }
                )
                break

    for field, pattern in BALANCE_SHEET_VALUE_PATTERNS.items():
        target = fields.get(field)
        if target is None:
            continue
        # Same limitation as income above -- fields[field] is a parsed
        # float with no fixed printed string form ("$87,500.00", "87,500",
        # "87500" are all possible depending on the cell), so there's no
        # exact-match cross-check available. First clean match only, same
        # accepted trade-off (#214).
        found = False
        for match in pattern.finditer(text):
            result = _cleaned_span(match)
            if result is None:
                continue
            cleaned, start, end = result
            spans.append(
                {
                    "field": field,
                    "value": cleaned,
                    "start": start,
                    "end": end,
                    "detection_method": "regex",
                }
            )
            found = True
            break
        if found:
            continue
        # Issue #303 -- some real templates never write "Total Current
        # Assets"/"Total Current Liabilities" as literal combined text
        # at all (the section-header + bare "Total" row shape #167/#297
        # already handle on the extraction side) -- the label search
        # above can never match these, even when extraction resolved
        # the value correctly. Confirmed real: 5/5 fields extracted
        # correctly on a real balance sheet, only 3/5 got a span. Falls
        # back to searching for the ALREADY-KNOWN value directly, same
        # "search for the value, not the label" approach #289 already
        # uses on the image path.
        for amount_match in _BALANCE_SHEET_BARE_AMOUNT_RE.finditer(text):
            amount = parse_currency_amount_balance_sheet(amount_match.group(0))
            if amount is None or abs(amount - target) >= 0.01:
                continue
            spans.append(
                {
                    "field": field,
                    "value": amount_match.group(0),
                    "start": amount_match.start(),
                    "end": amount_match.end(),
                    "detection_method": "regex",
                }
            )
            break

    return spans


def _words_overlapping_span(word_spans: list[dict], start: int, end: int) -> list[dict]:
    return [w for w in word_spans if w["start"] < end and w["end"] > start]


# Real confirmed leak: rendered actual computed redaction boxes onto a real
# processed payslip image and visually inspected the result -- nearly
# every box's RIGHT edge cut into the last character (a sliver of a real
# digit left visible outside the redacted rectangle), on "$27.81",
# "$1.28", BSB "123-456", account "1234 5678", every dollar total, etc.
# Root cause: this union takes OCR word boxes exactly as returned, and
# nothing downstream ever adds a safety margin -- if the underlying word
# box itself is even slightly tight (common for OCR boxes, which often
# clip trailing serifs/anti-aliasing), the redacted rectangle inherits
# that tightness with nothing to correct it. Margin is a percentage of
# the box's own height (not a fixed pixel count) so it scales naturally
# across different image resolutions and font sizes.
#
# Asymmetric on purpose, not a guess: a first pass shipped 15% on both
# sides, but re-inspecting at 5x pixel zoom after a follow-up report
# showed the LEFT edge was still clipping the first character even with
# that margin applied -- while the right edge was genuinely fine. This
# lines up with the same left-edge tightness already confirmed elsewhere
# this session in PPStructureV3's own text detection (a different,
# unfixable-without-cost issue there -- see field_extraction_en.py's
# LABEL_PATTERNS comments) showing up again here in the separate
# word-box detection path this redaction logic depends on. Tested 15%/
# 25%/35%/50% directly against 3 real boxes (BSB, account, ABN) at 6x
# zoom: 15% and 25% both still left a visible sliver of the first
# character, 35% was the first value that fully covered it in all 3
# real cases with no meaningful over-expansion. Right stays at 15%,
# already confirmed sufficient in the original inspection.
_LEFT_MARGIN_PCT = 0.35
_RIGHT_MARGIN_PCT = 0.15

# Issue #310 -- originally this union added no vertical margin at all
# ("no vertical clipping was observed in either inspection" -- true at
# the time, checked only against payslip images). The contract redaction
# IoU audit found a real counter-example: rendered a real computed box
# onto a real contract image at 8x zoom and the BOTTOM edge clipped a
# descender's tail ("King"'s "g"), the same class of tight-OCR-box
# clipping already confirmed horizontally above, just never observed
# vertically before. No top/ascender clipping was found in the same
# inspection, so top stays untouched -- same "don't expand on an
# unconfirmed dimension" discipline the original comment already used,
# just now correctly scoped to top only. Tested 15%/25%/35% at 8x zoom
# against the same real descender: 15% and 25% still left a sliver of
# the tail exposed, 35% was the first value that fully covered it,
# matching _LEFT_MARGIN_PCT's own value from the same kind of test.
# Verified this also closes all 4 real IoU misses found by the audit
# (0.468-0.488 -> 0.638-0.787, all now above the 0.5 threshold) by
# recomputing IoU against redaction_ground_truth.json's real boxes, not
# just visual inspection.
_BOTTOM_MARGIN_PCT = 0.35


def _union_box(words: list[dict], all_words: list[dict]) -> tuple[int, int, int, int]:
    x1 = min(w["box"][0] for w in words)
    y1 = min(w["box"][1] for w in words)
    x2 = max(w["box"][2] for w in words)
    y2 = max(w["box"][3] for w in words)
    h = y2 - y1

    # Issue #310 -- clamp the bottom margin to at most half the real gap
    # to the next word below (in the SAME OCR pass's own coordinates --
    # confirmed real gaps between contract text lines run ~28px here,
    # comfortably wider than the ~7px margin this normally adds, but
    # nothing upstream guarantees that on every document/layout). Without
    # this, a document with genuinely tight line spacing could have this
    # margin bleed the redaction box into an unrelated line below --
    # worse than the clipping it's meant to fix. own_boxes excludes this
    # field's own words so a multi-word/multi-line field's later word
    # never counts as "the next line."
    own_boxes = {tuple(w["box"]) for w in words}
    below_tops = [w["box"][1] for w in all_words if tuple(w["box"]) not in own_boxes and w["box"][1] >= y2]
    bottom_margin = round(h * _BOTTOM_MARGIN_PCT)
    if below_tops:
        bottom_margin = min(bottom_margin, max((min(below_tops) - y2) // 2, 0))

    return x1 - round(h * _LEFT_MARGIN_PCT), y1, x2 + round(h * _RIGHT_MARGIN_PCT), y2 + bottom_margin


def _matches_accepted_value(field: str, cleaned: str, fields: dict) -> bool:
    return cleaned == fields.get(field)


def _box_pct(box: tuple[int, int, int, int], img_h: int, img_w: int) -> dict:
    # Clamp -- _union_box's horizontal margin can push x1 below 0 or x2
    # past img_w for a value sitting near the page edge, and (#310) its
    # bottom margin can now push y2 past img_h the same way for a value
    # sitting near the page's bottom edge; an unclamped negative/over-bound
    # percentage would be a real invalid percentage downstream (redaction
    # coordinates are documented as percentages, never absolute pixels,
    # never negative).
    x1, y1, x2, y2 = box
    x1 = max(x1, 0)
    x2 = min(x2, img_w)
    y2 = min(y2, img_h)
    return {
        "x_pct": x1 / img_w,
        "y_pct": y1 / img_h,
        "w_pct": (x2 - x1) / img_w,
        "h_pct": (y2 - y1) / img_h,
    }


def _fragment_center_in_cell(cell_box: list[float], frag_box: list[float]) -> bool:
    cx1, cy1, cx2, cy2 = cell_box
    fx1, fy1, fx2, fy2 = frag_box
    fcx, fcy = (fx1 + fx2) / 2, (fy1 + fy2) / 2
    return cx1 <= fcx <= cx2 and cy1 <= fcy <= cy2


def _row_label_matches(
    field: str,
    cell_box: list[float],
    all_cell_boxes: list[list[float]],
    frag_texts: list[str],
    frag_boxes: list[list[float]],
) -> bool:
    """Issue #293 -- when the same dollar amount appears in more than
    one cell on a page (confirmed real: a synthetic document with
    three separate $139,000 cells), find_sensitive_boxes needs a way
    to tell which cell is actually this field's row. Checks every
    cell_box in the same row (vertical overlap) positioned to this
    one's LEFT -- not just the nearest one -- since real balance
    sheets are multi-column (assets/liabilities side by side), so the
    immediate left neighbor is often another value column, not the
    label; the real label can sit two or more columns further left.
    Matches each candidate's concatenated fragment text against the
    field's already-defined exact label pattern (same one the
    DOCX-path extraction uses)."""
    cy = (cell_box[1] + cell_box[3]) / 2
    left_neighbors = [
        cb
        for cb in all_cell_boxes
        if cb is not cell_box and cb[1] <= cy <= cb[3] and cb[2] <= cell_box[0]
    ]
    pattern = _BALANCE_SHEET_LABEL_RE.get(field)
    if pattern is None:
        return False
    for label_cell in left_neighbors:
        label_text = "".join(
            text
            for _, _, text in sorted(
                (fb[1], fb[0], ft)
                for ft, fb in zip(frag_texts, frag_boxes)
                if _fragment_center_in_cell(label_cell, fb)
            )
        )
        if pattern.search(label_text):
            return True
    return False


def _find_balance_sheet_value_box(
    field: str, target: float, table_ocr_preds: list[dict]
) -> tuple[str, tuple[int, int, int, int]] | None:
    """Issue #289 -- locates a balance-sheet total's box by searching for
    its ALREADY-KNOWN value (from fields[field], already correctly
    resolved by extract_balance_sheet_fields_en's section-tracking-aware
    table_rows matching) instead of re-finding the LABEL via a flat text
    reconstruction. Confirmed real, not theoretical: PPStructureV3's
    plain word-level OCR pass (build_word_reconstruction, a completely
    separate pass from the table-aware one) can scramble a "TOTAL"/
    "ASSETS" label apart with real numeric content interleaved between
    the fragments.

    A first version tried concatenating table_ocr_pred's fragments in
    their own raw reading order -- wrong, confirmed by direct testing:
    that order runs across the WHOLE visual line first ("$106", "$75,",
    "$74,", "$30,", "$92," -- 5 columns' first half each), then the
    next line ("000" x5), not each cell's own two-line value
    consecutively. A single value never appears as a contiguous run in
    that flat sequence at all when it wraps within a narrow column.

    Instead: for each of the table's own detected CELL boxes
    (cell_box_list), find whichever OCR fragments fall inside that
    cell's box by simple center-point containment, sort those fragments
    top-to-bottom (correct within one cell, since fragments only wrap
    vertically within a narrow column -- confirmed real: "$92," above
    "000", same x-range), and concatenate. cell_box_list is used purely
    as a set of spatial regions here, never correlated to pred_html's
    own <td> order (see ocr_document's own comment on why that
    correlation isn't reliable) -- so this is unaffected by whatever
    mismatch exists between the two.

    Issue #291 -- returning the CELL's own detected box directly (as
    this originally did) is too loose: cell_box_list includes real
    margin/padding beyond the digits, confirmed directly against real
    ground truth (a predicted box ~60% wider than the human-annotated
    tight box, consistently landing at 0.2-0.48 IoU -- just under the
    0.5 threshold -- across every real miss). Returns the union of the
    MATCHED fragments' own boxes instead -- tight around the actual
    value text, same approach the regex-based fields above already
    use via _union_box.

    Issue #293 -- returning the FIRST matching cell is wrong when more
    than one cell shares the same dollar amount: confirmed real, a
    synthetic document had three separate cells worth $139,000 on one
    page, only one of them this field's actual row. Now collects every
    matching cell and prefers whichever one's row label (via
    _row_label_matches) actually matches this field, falling back to
    plain value-matching candidates when none of them do.

    Issue #295 -- a same-tier tie (either tier) still needs a
    tiebreaker: real multi-column comparative balance sheets (two
    dollar-amount columns per row, e.g. year-over-year) can have the
    SAME target value repeat across columns of one row, and #293's
    "first one found" pick is then arbitrary. Confirmed on two real,
    independent documents that ground truth always lands on the
    RIGHTMOST matching candidate within whichever tier is non-empty --
    matches real financial-statement convention of placing the
    current/primary reporting period in the last column. Applies
    equally to a label-confirmed tie (two columns' rows both satisfy
    the label pattern) and a no-label-match fallback tie (the row
    label wasn't recognized by OCR at all -- confirmed real on one of
    the two documents, its label cell only contained the fragment
    "Total", missing "Current Assets" entirely)."""
    labeled_candidates = []
    fallback_candidates = []
    for table in table_ocr_preds:
        frag_texts = table["texts"]
        frag_boxes = table["boxes"]
        cell_boxes = table.get("cell_boxes", [])
        for cell_box in cell_boxes:
            contained = sorted(
                (
                    (fb[1], fb[0], ft, fb)
                    for ft, fb in zip(frag_texts, frag_boxes)
                    if _fragment_center_in_cell(cell_box, fb)
                ),
            )
            if not contained:
                continue
            joined = "".join(text for _, _, text, _ in contained)
            amount = parse_currency_amount_balance_sheet(joined)
            if amount is None or abs(amount - target) >= 0.01:
                continue
            x1 = min(fb[0] for _, _, _, fb in contained)
            y1 = min(fb[1] for _, _, _, fb in contained)
            x2 = max(fb[2] for _, _, _, fb in contained)
            y2 = max(fb[3] for _, _, _, fb in contained)
            entry = (x1, joined, (round(x1), round(y1), round(x2), round(y2)))
            fallback_candidates.append(entry)
            if _row_label_matches(field, cell_box, cell_boxes, frag_texts, frag_boxes):
                labeled_candidates.append(entry)
    pool = labeled_candidates or fallback_candidates
    if not pool:
        return None
    _, joined, box = max(pool, key=lambda entry: entry[0])
    return joined, box


def find_sensitive_boxes(image, fields: dict, table_ocr_preds: list[dict] | None = None) -> list[dict]:
    from module2_ocr_extraction import build_word_reconstruction, ocr_document

    img_h, img_w = image.shape[:2]
    text, word_spans = build_word_reconstruction(image)
    boxes = []

    for field, pattern in _REGEX_LIST_FIELDS.items():
        accepted = set(fields.get(field) or [])
        if not accepted:
            continue
        for match in pattern.finditer(text):
            value = match.group(0)
            if value not in accepted:
                continue
            overlapping = _words_overlapping_span(word_spans, match.start(), match.end())
            if not overlapping:
                continue
            boxes.append(
                {
                    "field": field,
                    "value": value,
                    **_box_pct(_union_box(overlapping, word_spans), img_h, img_w),
                    "detection_method": "regex",
                }
            )

    fields_boxed = set()
    for field, pattern in LABEL_PATTERNS.items():
        if not fields.get(field):
            continue
        for match in pattern.finditer(text):
            result = _cleaned_span(match)
            if result is None:
                continue
            cleaned, start, end = result
            if not _matches_accepted_value(field, cleaned, fields):
                continue
            overlapping = _words_overlapping_span(word_spans, start, end)
            if not overlapping:
                # No OCR word boxes overlap this occurrence specifically --
                # continue, not break: a LATER occurrence of the same real
                # value (#205) may still have overlapping word boxes even
                # though this one doesn't.
                continue
            boxes.append(
                {
                    "field": field,
                    "value": cleaned,
                    **_box_pct(_union_box(overlapping, word_spans), img_h, img_w),
                    "detection_method": "regex",
                }
            )
            fields_boxed.add(field)

    # Issue #306 -- build_word_reconstruction's own per-line "\n" join can
    # split a label from its value onto separate OCR lines exactly like
    # module2_ocr_extraction._repair_line_split_fields already works
    # around on the extraction side (its spatial adjacent-box lookup, not
    # a flat-text regex) -- but there was no equivalent repair here, so a
    # value recovered via that repair got zero boxes even though the same
    # label pattern loop above never found a same-line match to reject.
    # Confirmed real: a photographed payslip's name/income, both extracted
    # correctly via the repair, produced zero boxes -- every box came back
    # tagged for an unrelated field. Falls back to searching for the
    # ALREADY-KNOWN value directly, same "search for the value, not just
    # the label" approach #289/#303/#305 already use for their own
    # versions of this exact limitation.
    for field in LABEL_PATTERNS:
        target = fields.get(field)
        if not target or field in fields_boxed:
            continue
        search_from = 0
        while True:
            idx = text.find(target, search_from)
            if idx == -1:
                break
            end = idx + len(target)
            overlapping = _words_overlapping_span(word_spans, idx, end)
            if overlapping:
                boxes.append(
                    {
                        "field": field,
                        "value": target,
                        **_box_pct(_union_box(overlapping, word_spans), img_h, img_w),
                        "detection_method": "regex",
                    }
                )
            search_from = end

    # Issue #305 -- box-side counterpart to the span-side fix above.
    if fields.get("annual_salary") is not None:
        target = fields["annual_salary"]
        for match in ANNUAL_SALARY_RE.finditer(text):
            result = _cleaned_span(match)
            if result is None:
                continue
            cleaned, start, end = result
            amount = parse_currency_amount(cleaned)
            if amount is None or abs(amount - target) >= 0.01:
                continue
            overlapping = _words_overlapping_span(word_spans, start, end)
            if not overlapping:
                continue
            boxes.append(
                {
                    "field": "annual_salary",
                    "value": cleaned,
                    **_box_pct(_union_box(overlapping, word_spans), img_h, img_w),
                    "detection_method": "regex",
                }
            )

    if fields.get("income") is not None:
        # income's fields value is a parsed float, not the raw printed
        # string -- unlike the other label-anchored fields, there's no
        # string form to cross-check the reconstruction's match against
        # without changing Module 2's return contract (out of scope).
        # Accept the first clean match, same limitation find_sensitive_spans
        # already has for this field.
        pattern = INCOME_LABEL_PATTERNS.get(fields.get("income_basis"))
        income_boxed = False
        if pattern is not None:
            for match in pattern.finditer(text):
                result = _cleaned_span(match)
                if result is None:
                    continue
                cleaned, start, end = result
                overlapping = _words_overlapping_span(word_spans, start, end)
                if overlapping:
                    boxes.append(
                        {
                            "field": "income",
                            "value": cleaned,
                            **_box_pct(_union_box(overlapping, word_spans), img_h, img_w),
                            "detection_method": "regex",
                        }
                    )
                    income_boxed = True
                break

        if not income_boxed:
            # Issue #306 -- same label/value OCR-line split as the
            # fallback above, but income has no fixed printed string form
            # to search for literally (a parsed float, same limitation the
            # comment above already notes) -- falls back to scanning for a
            # "$"-shaped bare amount whose PARSED value matches the
            # already-known target, same approach the balance-sheet (#303)
            # and annual_salary (#305) fallbacks already use for this
            # exact limitation.
            target = fields["income"]
            for amount_match in _BALANCE_SHEET_BARE_AMOUNT_RE.finditer(text):
                amount = parse_currency_amount(amount_match.group(0))
                if amount is None or abs(amount - target) >= 0.01:
                    continue
                overlapping = _words_overlapping_span(word_spans, amount_match.start(), amount_match.end())
                if not overlapping:
                    continue
                boxes.append(
                    {
                        "field": "income",
                        "value": amount_match.group(0),
                        **_box_pct(_union_box(overlapping, word_spans), img_h, img_w),
                        "detection_method": "regex",
                    }
                )
                break

    if any(fields.get(f) is not None for f in BALANCE_SHEET_VALUE_PATTERNS):
        # Issue #289 -- table_ocr_preds is threaded through from the
        # caller when already available (pipeline.py's own extract_fields
        # call already computed it, same PPStructureV3 call -- passing it
        # through avoids a real redundant OCR call). Falls back to a
        # fresh ocr_document() call for callers that don't have it handy
        # (measure_redaction_accuracy.py, this module's own self-checks).
        if table_ocr_preds is None:
            table_ocr_preds = ocr_document(image)["table_ocr_preds"]

        for field in BALANCE_SHEET_VALUE_PATTERNS:
            target = fields.get(field)
            if target is None:
                continue
            found = _find_balance_sheet_value_box(field, target, table_ocr_preds)
            if found is None:
                # Same "skip, don't fabricate" degradation as everywhere
                # else in this function -- no fragment run in any
                # detected table matched this value closely enough.
                continue
            value, box = found
            boxes.append(
                {
                    "field": field,
                    "value": value,
                    **_box_pct(box, img_h, img_w),
                    "detection_method": "table_ocr",
                }
            )

    return boxes


def boxes_to_composite_pct(per_page_boxes: list[dict], page_images: list[np.ndarray]) -> list[dict]:
    """Issue #286 -- a multi-page OCR/scanned-PDF document computes each
    box independently per page (find_sensitive_boxes called once per
    page's own enhanced image), but the redacted-preview endpoint renders
    one composite image (file_routing.stack_pages_vertically -- every
    enhanced page stacked top to bottom, left-aligned, narrower pages
    padded white on the right). This converts each box's page-local
    x_pct/y_pct/w_pct/h_pct (relative to `page_images[box["page_index"]]`
    alone) into that composite's own coordinate space, in real pixels
    (page_images are already-enhanced np.ndarray frames, unlike
    file_routing.resolve_item_boxes_via_pdf_text's PDF-points version of
    this same math for the text-native path). Drops "page_index" from the
    output -- downstream consumers (apply_redaction_image, BE storage)
    only ever expect the four pct keys."""
    heights = [img.shape[0] for img in page_images]
    widths = [img.shape[1] for img in page_images]
    total_h = sum(heights)
    max_w = max(widths)
    offsets = []
    acc = 0
    for h in heights:
        offsets.append(acc)
        acc += h

    converted = []
    for box in per_page_boxes:
        page_index = box["page_index"]
        page_h = heights[page_index]
        page_w = widths[page_index]
        offset = offsets[page_index]
        converted.append(
            {
                **{k: v for k, v in box.items() if k != "page_index"},
                "x_pct": (box["x_pct"] * page_w) / max_w,
                "y_pct": (offset + box["y_pct"] * page_h) / total_h,
                "w_pct": (box["w_pct"] * page_w) / max_w,
                "h_pct": (box["h_pct"] * page_h) / total_h,
            }
        )
    return converted


def apply_redaction_image(image: np.ndarray, items: list[dict]) -> np.ndarray:
    """Burns filled black rectangles over each item's box. Coordinates are
    percentages of `image`'s own dimensions -- caller must pass the same
    enhanced image the coordinates were originally computed against
    (module1_opencv.enhance() output), never the raw upload."""
    img_h, img_w = image.shape[:2]
    redacted = image.copy()
    for item in items:
        x1 = int(item["x_pct"] * img_w)
        y1 = int(item["y_pct"] * img_h)
        x2 = int((item["x_pct"] + item["w_pct"]) * img_w)
        y2 = int((item["y_pct"] + item["h_pct"]) * img_h)
        cv2.rectangle(redacted, (x1, y1), (x2, y2), (0, 0, 0), thickness=-1)
    return redacted


if __name__ == "__main__":
    def test_single_occurrence_regex_field():
        text = "ABN: 12 345 978 910\nEmployee: Jo Worker"
        fields = {"abn": ["12 345 978 910"]}
        spans = find_sensitive_spans(text, fields)
        abn_spans = [s for s in spans if s["field"] == "abn"]
        assert len(abn_spans) == 1
        assert abn_spans[0]["value"] == "12 345 978 910"
        assert text[abn_spans[0]["start"]:abn_spans[0]["end"]] == "12 345 978 910"

    def test_multiple_occurrences_regex_field():
        text = "Phone: 0412345678\nOther: 0398765432"
        fields = {"phone": ["0412345678", "0398765432"]}
        spans = find_sensitive_spans(text, fields)
        phone_spans = [s for s in spans if s["field"] == "phone"]
        assert len(phone_spans) == 2
        values = {s["value"] for s in phone_spans}
        assert values == {"0412345678", "0398765432"}

    def test_label_anchored_skips_rejected_candidate():
        # first "Employee Address:" candidate is an angle-bracket
        # placeholder (rejected by _clean_label_value), second is the real
        # address Module 2 would have accepted -- span must land on the
        # second, not the first.
        text = "Employee Address: <insert employee address>\nEmployee Address: 42 Example Street, Melbourne VIC 3000"
        fields = {"address": "42 Example Street, Melbourne VIC 3000"}
        spans = find_sensitive_spans(text, fields)
        address_spans = [s for s in spans if s["field"] == "address"]
        assert len(address_spans) == 1
        assert address_spans[0]["value"] == "42 Example Street, Melbourne VIC 3000"
        expected_start = text.index("42 Example Street")
        assert address_spans[0]["start"] == expected_start

    def test_label_anchored_field_redacts_every_occurrence():
        # Issue #205 -- a repeated address (header + footer) must get a
        # span for BOTH occurrences, not just the first.
        text = (
            "Employee Address: 42 Example Street, Melbourne VIC 3000\n"
            "Some other line in between.\n"
            "Employee Address: 42 Example Street, Melbourne VIC 3000"
        )
        fields = {"address": "42 Example Street, Melbourne VIC 3000"}
        spans = find_sensitive_spans(text, fields)
        address_spans = [s for s in spans if s["field"] == "address"]
        assert len(address_spans) == 2
        starts = {s["start"] for s in address_spans}
        assert starts == {text.index("42 Example Street"), text.rindex("42 Example Street")}

    def test_label_anchored_field_does_not_redact_a_different_value():
        # A second "Employee Address:" line with a genuinely different
        # address (not the accepted fields.address value) must NOT get a
        # span -- _matches_accepted_value is what keeps #205's fix from
        # over-redacting a different real value that happens to match the
        # same label pattern elsewhere in the document.
        text = (
            "Employee Address: 42 Example Street, Melbourne VIC 3000\n"
            "Employee Address: 1 Other Street, Sydney NSW 2000"
        )
        fields = {"address": "42 Example Street, Melbourne VIC 3000"}
        spans = find_sensitive_spans(text, fields)
        address_spans = [s for s in spans if s["field"] == "address"]
        assert len(address_spans) == 1
        assert address_spans[0]["value"] == "42 Example Street, Melbourne VIC 3000"

    def test_absent_field_produces_no_span():
        text = "Employee: Jo Worker"
        fields = {"bsb": None}
        spans = find_sensitive_spans(text, fields)
        assert [s for s in spans if s["field"] == "bsb"] == []

    def test_income_field_uses_matching_basis_pattern():
        text = "Total gross payment: $718.66\nNET PAY: $625.36"
        fields = {"income": 718.66, "income_basis": "gross"}
        spans = find_sensitive_spans(text, fields)
        income_spans = [s for s in spans if s["field"] == "income"]
        assert len(income_spans) == 1
        assert income_spans[0]["value"] == "$718.66"

    def test_annual_salary_field_produces_span():
        # Issue #305 -- annual_salary was in SENSITIVE_FIELD_KEYS but had
        # zero span detection: 25/25 real payslips with a correctly-
        # extracted annual_salary got no redaction span for it.
        text = "*Annual salary: [if applicable]\n$67,000\nOther figure: $50,000"
        fields = {"annual_salary": 67000.0}
        spans = find_sensitive_spans(text, fields)
        salary_spans = [s for s in spans if s["field"] == "annual_salary"]
        assert len(salary_spans) == 1
        assert salary_spans[0]["value"] == "$67,000"
        assert text[salary_spans[0]["start"]:salary_spans[0]["end"]] == "$67,000"

    def test_annual_salary_field_absent_produces_no_span():
        text = "Annual salary: $67,000"
        fields = {"annual_salary": None}
        spans = find_sensitive_spans(text, fields)
        assert [s for s in spans if s["field"] == "annual_salary"] == []

    def test_all_spans_satisfy_text_slice_invariant():
        text = (
            "ABN: 12 345 978 910\n"
            "Phone: 0412345678\n"
            "Employee Address: 42 Example Street, Melbourne VIC 3000\n"
            "Total gross payment: $718.66"
        )
        fields = {
            "abn": ["12 345 978 910"],
            "phone": ["0412345678"],
            "address": "42 Example Street, Melbourne VIC 3000",
            "income": 718.66,
            "income_basis": "gross",
        }
        spans = find_sensitive_spans(text, fields)
        assert len(spans) == 4
        for span in spans:
            assert text[span["start"]:span["end"]] == span["value"]

    from unittest.mock import patch
    import numpy as np

    _FAKE_IMAGE = np.zeros((100, 400, 3), dtype=np.uint8)  # 400x100 (w x h)

    def _fake_word_reconstruction(*args, **kwargs):
        text = "Account: 1234 5678"
        word_spans = [
            {"word": "Account:", "box": (10, 20, 90, 35), "start": 0, "end": 8},
            {"word": "1234", "box": (95, 20, 120, 35), "start": 9, "end": 13},
            {"word": "5678", "box": (125, 20, 150, 35), "start": 14, "end": 18},
        ]
        return text, word_spans

    def test_single_word_box():
        # Real confirmed fix, asymmetric: box height is 35-20=15, so
        # left margin = round(15*0.35) = 5px, right margin = round(15*0.15)
        # = 2px; x1=95-5=90, x2=150+2=152. y1 stays exact -- no ascender
        # clipping was ever observed. y2 gets a #310 bottom margin =
        # round(15*0.35) = 5px (no words below in this fixture to clamp
        # against) -> y2=35+5=40.
        with patch("module2_ocr_extraction.build_word_reconstruction", side_effect=_fake_word_reconstruction):
            fields = {"account_number": "1234 5678"}
            boxes = find_sensitive_boxes(_FAKE_IMAGE, fields)
        acct_boxes = [b for b in boxes if b["field"] == "account_number"]
        assert len(acct_boxes) == 1
        assert acct_boxes[0]["value"] == "1234 5678"
        assert abs(acct_boxes[0]["x_pct"] - 90 / 400) < 1e-6
        assert abs(acct_boxes[0]["y_pct"] - 20 / 100) < 1e-6
        assert abs(acct_boxes[0]["w_pct"] - (152 - 90) / 400) < 1e-6
        assert abs(acct_boxes[0]["h_pct"] - (40 - 20) / 100) < 1e-6


    def test_union_box_margin_clamps_at_image_edge():
        # Real edge case the margin introduces: a value sitting flush
        # against the left edge of the page must not produce a negative
        # x_pct (redaction coordinates are documented percentages, never
        # negative) -- _box_pct clamps x1 to 0 and x2 to img_w.
        def _fake_edge_reconstruction(*args, **kwargs):
            text = "Account: 1234 5678"
            word_spans = [
                {"word": "Account:", "box": (0, 20, 10, 35), "start": 0, "end": 8},
                {"word": "1234", "box": (0, 20, 20, 35), "start": 9, "end": 13},
                {"word": "5678", "box": (380, 20, 400, 35), "start": 14, "end": 18},
            ]
            return text, word_spans

        with patch("module2_ocr_extraction.build_word_reconstruction", side_effect=_fake_edge_reconstruction):
            fields = {"account_number": "1234 5678"}
            boxes = find_sensitive_boxes(_FAKE_IMAGE, fields)
        acct_boxes = [b for b in boxes if b["field"] == "account_number"]
        assert len(acct_boxes) == 1
        assert acct_boxes[0]["x_pct"] == 0.0
        assert abs(acct_boxes[0]["x_pct"] + acct_boxes[0]["w_pct"] - 1.0) < 1e-6

    def test_union_box_bottom_margin_clamped_by_gap_to_next_line():
        # Issue #310 -- without clamping, this box's own #310 bottom
        # margin (round(15*0.35)=5px) would push y2 from 35 to 40,
        # crossing into "Next" which starts at y=37 -- only a 2px real
        # gap. Clamped to half that gap (1px) instead: y2=35+1=36.
        def _fake_tight_line_spacing(*args, **kwargs):
            text = "Account: 1234 5678\nNext line"
            word_spans = [
                {"word": "Account:", "box": (10, 20, 90, 35), "start": 0, "end": 8},
                {"word": "1234", "box": (95, 20, 120, 35), "start": 9, "end": 13},
                {"word": "5678", "box": (125, 20, 150, 35), "start": 14, "end": 18},
                {"word": "Next", "box": (10, 37, 50, 50), "start": 20, "end": 24},
            ]
            return text, word_spans

        with patch("module2_ocr_extraction.build_word_reconstruction", side_effect=_fake_tight_line_spacing):
            fields = {"account_number": "1234 5678"}
            boxes = find_sensitive_boxes(_FAKE_IMAGE, fields)
        acct_boxes = [b for b in boxes if b["field"] == "account_number"]
        assert len(acct_boxes) == 1
        assert abs(acct_boxes[0]["y_pct"] - 20 / 100) < 1e-6
        assert abs(acct_boxes[0]["h_pct"] - (36 - 20) / 100) < 1e-6

    def test_absent_field_no_box():
        with patch("module2_ocr_extraction.build_word_reconstruction", side_effect=_fake_word_reconstruction):
            fields = {"account_number": None}
            boxes = find_sensitive_boxes(_FAKE_IMAGE, fields)
        assert [b for b in boxes if b["field"] == "account_number"] == []

    def test_value_not_in_fields_produces_no_box():
        with patch("module2_ocr_extraction.build_word_reconstruction", side_effect=_fake_word_reconstruction):
            fields = {"account_number": "9999 9999"}
            boxes = find_sensitive_boxes(_FAKE_IMAGE, fields)
        assert [b for b in boxes if b["field"] == "account_number"] == []

    def _fake_annual_salary_reconstruction(*args, **kwargs):
        text = "Annual salary: $67,000"
        word_spans = [
            {"word": "Annual", "box": (10, 20, 60, 35), "start": 0, "end": 6},
            {"word": "salary:", "box": (65, 20, 120, 35), "start": 7, "end": 14},
            {"word": "$67,000", "box": (125, 20, 180, 35), "start": 15, "end": 22},
        ]
        return text, word_spans

    def test_annual_salary_field_produces_box():
        # Issue #305 -- box-side counterpart to the span-side fix above.
        with patch("module2_ocr_extraction.build_word_reconstruction", side_effect=_fake_annual_salary_reconstruction):
            fields = {"annual_salary": 67000.0}
            boxes = find_sensitive_boxes(_FAKE_IMAGE, fields)
        salary_boxes = [b for b in boxes if b["field"] == "annual_salary"]
        assert len(salary_boxes) == 1
        assert salary_boxes[0]["value"] == "$67,000"

    def test_annual_salary_field_absent_produces_no_box():
        with patch("module2_ocr_extraction.build_word_reconstruction", side_effect=_fake_annual_salary_reconstruction):
            fields = {"annual_salary": None}
            boxes = find_sensitive_boxes(_FAKE_IMAGE, fields)
        assert [b for b in boxes if b["field"] == "annual_salary"] == []

    def _fake_label_value_split_reconstruction(*args, **kwargs):
        # Simulates the real confirmed failure (#306): label and value land
        # on separate OCR lines, so LABEL_PATTERNS's same-line capture is
        # empty and the loop above finds nothing to reject or accept.
        text = "Employee:\nRymer, Mark\n"
        word_spans = [
            {"word": "Employee:", "box": (10, 5, 70, 20), "start": 0, "end": 9},
            {"word": "Rymer,", "box": (10, 25, 60, 40), "start": 10, "end": 16},
            {"word": "Mark", "box": (65, 25, 100, 40), "start": 17, "end": 21},
        ]
        return text, word_spans

    def test_label_value_line_split_falls_back_to_value_search_for_box():
        with patch("module2_ocr_extraction.build_word_reconstruction", side_effect=_fake_label_value_split_reconstruction):
            fields = {"name": "Rymer, Mark"}
            boxes = find_sensitive_boxes(_FAKE_IMAGE, fields)
        name_boxes = [b for b in boxes if b["field"] == "name"]
        assert len(name_boxes) == 1
        assert name_boxes[0]["value"] == "Rymer, Mark"

    def test_label_value_fallback_does_not_duplicate_when_same_line_already_boxed():
        def _fake_same_line(*args, **kwargs):
            text = "Employee: Rymer, Mark\n"
            word_spans = [
                {"word": "Employee:", "box": (10, 5, 70, 20), "start": 0, "end": 9},
                {"word": "Rymer,", "box": (75, 5, 120, 20), "start": 10, "end": 16},
                {"word": "Mark", "box": (125, 5, 160, 20), "start": 17, "end": 21},
            ]
            return text, word_spans

        with patch("module2_ocr_extraction.build_word_reconstruction", side_effect=_fake_same_line):
            fields = {"name": "Rymer, Mark"}
            boxes = find_sensitive_boxes(_FAKE_IMAGE, fields)
        name_boxes = [b for b in boxes if b["field"] == "name"]
        assert len(name_boxes) == 1

    def test_income_line_split_falls_back_to_bare_amount_search_for_box():
        def _fake_income_split(*args, **kwargs):
            text = "Gross Pay\n$718.66\n"
            word_spans = [
                {"word": "Gross", "box": (10, 5, 50, 20), "start": 0, "end": 5},
                {"word": "Pay", "box": (55, 5, 80, 20), "start": 6, "end": 9},
                {"word": "$718.66", "box": (10, 25, 70, 40), "start": 10, "end": 17},
            ]
            return text, word_spans

        with patch("module2_ocr_extraction.build_word_reconstruction", side_effect=_fake_income_split):
            fields = {"income": 718.66, "income_basis": "gross"}
            boxes = find_sensitive_boxes(_FAKE_IMAGE, fields)
        income_boxes = [b for b in boxes if b["field"] == "income"]
        assert len(income_boxes) == 1
        assert income_boxes[0]["value"] == "$718.66"

    def test_apply_redaction_image_blacks_out_region_only():
        image = np.full((100, 200, 3), 255, dtype=np.uint8)  # all white
        items = [{"field": "bsb", "value": "x", "x_pct": 0.25, "y_pct": 0.25, "w_pct": 0.25, "h_pct": 0.25}]
        redacted = apply_redaction_image(image, items)
        # inside the box (x in [50,100), y in [25,50)) -> black
        assert redacted[35, 70].tolist() == [0, 0, 0]
        # outside the box -> untouched white
        assert redacted[5, 5].tolist() == [255, 255, 255]
        # input not mutated
        assert image[35, 70].tolist() == [255, 255, 255]

    def test_apply_redaction_image_no_items_returns_unchanged_copy():
        image = np.full((50, 50, 3), 200, dtype=np.uint8)
        redacted = apply_redaction_image(image, [])
        assert np.array_equal(redacted, image)

    def test_balance_sheet_totals_are_sensitive_field_keys():
        # #214 -- the fail-safe half of the fix: even if a specific
        # occurrence is never found in text (box or span), stripSensitiveFields
        # (BE) still nulls these out of aiResult.fields for non-owners.
        for key in ("total_current_assets", "total_assets", "total_current_liabilities", "total_liabilities", "total_equity"):
            assert key in SENSITIVE_FIELD_KEYS

    def test_balance_sheet_field_finds_value_on_docx_joined_row():
        # module2_text_extraction.py space-joins a docx table row onto one
        # line, no colon -- this is what that line looks like in practice.
        text = "Total Assets  $87,500.00\nTotal Current Assets  $45,000.00"
        fields = {"total_assets": 87500.0, "total_current_assets": 45000.0}
        spans = find_sensitive_spans(text, fields)
        assets_spans = [s for s in spans if s["field"] == "total_assets"]
        current_spans = [s for s in spans if s["field"] == "total_current_assets"]
        assert len(assets_spans) == 1
        assert assets_spans[0]["value"] == "$87,500.00"
        assert len(current_spans) == 1
        assert current_spans[0]["value"] == "$45,000.00"

    def test_balance_sheet_field_skips_parenthetical_alternate_name():
        # Real filled template (#215): "NET ASSETS (NET WORTH) $45,000" --
        # the parenthetical alternate-name sits between label and value.
        # Without skipping it, _clean_label_value rejects the value
        # (starts with "(") and the whole span silently drops.
        text = "NET ASSETS (NET WORTH) $45,000"
        fields = {"total_equity": 45000.0}
        spans = find_sensitive_spans(text, fields)
        equity_spans = [s for s in spans if s["field"] == "total_equity"]
        assert len(equity_spans) == 1
        assert equity_spans[0]["value"] == "$45,000"

    def test_balance_sheet_field_absent_produces_no_span():
        text = "Total Assets  $87,500.00"
        fields = {"total_assets": None}
        spans = find_sensitive_spans(text, fields)
        assert [s for s in spans if s["field"] == "total_assets"] == []

    def test_balance_sheet_field_falls_back_to_bare_value_when_label_absent():
        # Issue #303 -- confirmed real on Balance-sheet-template-FILLED-
        # 300.docx: total_current_assets/total_current_liabilities never
        # appear as literal "Total Current Assets ..." text (resolved via
        # the section-header + bare "Total" row shape instead), so the
        # label-based search above never matches -- even though
        # extraction resolved the value correctly. Falls back to finding
        # the already-known value directly.
        text = "Current Assets\nCash $10,000\nInventory $2,000\nTotal $92,000\nFixed Assets"
        fields = {"total_current_assets": 92000.0}
        spans = find_sensitive_spans(text, fields)
        matched = [s for s in spans if s["field"] == "total_current_assets"]
        assert len(matched) == 1
        assert matched[0]["value"] == "$92,000"
        assert text[matched[0]["start"]:matched[0]["end"]] == "$92,000"

    def test_balance_sheet_field_fallback_does_not_fire_when_label_already_matched():
        # The fallback must only run when the label search found nothing
        # -- a field whose label DOES appear literally should keep using
        # that match, not also add a second fallback span.
        text = "Total Assets  $87,500.00"
        fields = {"total_assets": 87500.0}
        spans = find_sensitive_spans(text, fields)
        matched = [s for s in spans if s["field"] == "total_assets"]
        assert len(matched) == 1

    def _empty_word_reconstruction(*args, **kwargs):
        return "", []

    def test_balance_sheet_field_box_found_via_table_cell():
        # Issue #289 -- balance-sheet boxes now come from table_ocr_preds
        # (cell_box_list used purely as spatial regions, matched to
        # fine-grained OCR fragments by containment), not
        # build_word_reconstruction's flat text -- a real, confirmed
        # word-wrap/reading-order problem for narrow balance-sheet
        # columns made the old regex-based approach fail 0/18 on every
        # real document. Models a value split across two fragments
        # ("$87," + "500", real observed shape) inside one cell box.
        table_ocr_preds = [
            {
                "texts": ["Total", "Assets", "$87,", "500"],
                "boxes": [[10, 20, 50, 35], [55, 20, 100, 35], [105, 20, 150, 35], [105, 35, 150, 50]],
                "cell_boxes": [[100, 15, 155, 55]],
            }
        ]
        with patch("module2_ocr_extraction.build_word_reconstruction", side_effect=_empty_word_reconstruction):
            fields = {"total_assets": 87500.0}
            boxes = find_sensitive_boxes(_FAKE_IMAGE, fields, table_ocr_preds=table_ocr_preds)
        assets_boxes = [b for b in boxes if b["field"] == "total_assets"]
        assert len(assets_boxes) == 1
        assert assets_boxes[0]["value"] == "$87,500"
        # Issue #291 -- box must be the tight union of the matched
        # fragments ($87,/500, pixel box [105,20,150,50]), NOT the
        # looser parent cell_box ([100,15,155,55]) -- confirmed real
        # against ground truth that the cell box is systematically too
        # wide/offset (predicted ~60% wider than a human-annotated tight
        # box, IoU stuck at 0.2-0.48). _FAKE_IMAGE is 400w x 100h.
        box = assets_boxes[0]
        assert abs(box["x_pct"] - 105 / 400) < 1e-9
        assert abs(box["y_pct"] - 20 / 100) < 1e-9
        assert abs(box["w_pct"] - 45 / 400) < 1e-9
        assert abs(box["h_pct"] - 30 / 100) < 1e-9

    def test_balance_sheet_field_no_matching_cell_produces_no_box():
        table_ocr_preds = [
            {
                "texts": ["Total", "Assets", "$12,", "345"],
                "boxes": [[10, 20, 50, 35], [55, 20, 100, 35], [105, 20, 150, 35], [105, 35, 150, 50]],
                "cell_boxes": [[100, 15, 155, 55]],
            }
        ]
        with patch("module2_ocr_extraction.build_word_reconstruction", side_effect=_empty_word_reconstruction):
            fields = {"total_assets": 87500.0}
            boxes = find_sensitive_boxes(_FAKE_IMAGE, fields, table_ocr_preds=table_ocr_preds)
        assert [b for b in boxes if b["field"] == "total_assets"] == []

    def test_balance_sheet_field_disambiguates_duplicate_value_by_row_label():
        # Issue #293 -- confirmed real: a synthetic document had three
        # separate cells sharing the exact same dollar value on one
        # page, and first-match-wins picked the wrong one every time.
        # Two cells here share $100,000: row A's label is "Total
        # Liabilities" (wrong field for this lookup), row B's is
        # "Total Equity" (correct). Row A's value cell is listed FIRST
        # in cell_boxes, to prove this isn't accidental first-match
        # luck -- the fix must actively prefer row B via its label.
        table_ocr_preds = [
            {
                "texts": ["Total", "Liabilities", "$100,", "000", "Total", "Equity", "$100,", "000"],
                "boxes": [
                    [10, 20, 50, 35], [55, 20, 100, 35],
                    [105, 20, 150, 35], [105, 35, 150, 50],
                    [10, 60, 50, 75], [55, 60, 100, 75],
                    [105, 60, 150, 75], [105, 75, 150, 90],
                ],
                "cell_boxes": [
                    [100, 15, 155, 55],
                    [100, 55, 155, 95],
                    [5, 15, 95, 55],
                    [5, 55, 95, 95],
                ],
            }
        ]
        with patch("module2_ocr_extraction.build_word_reconstruction", side_effect=_empty_word_reconstruction):
            fields = {"total_equity": 100000.0}
            boxes = find_sensitive_boxes(_FAKE_IMAGE, fields, table_ocr_preds=table_ocr_preds)
        equity_boxes = [b for b in boxes if b["field"] == "total_equity"]
        assert len(equity_boxes) == 1
        # Row B's value cell starts at pixel y=60 -- confirm the
        # returned box is row B's, not row A's (y=20, which
        # first-match-wins alone would have returned).
        assert abs(equity_boxes[0]["y_pct"] - 60 / 100) < 1e-9

    def test_balance_sheet_field_multi_column_tie_prefers_rightmost_labeled_candidate():
        # Issue #295 -- confirmed real on two independent documents: a
        # multi-column comparative balance sheet (e.g. year-over-year)
        # can have the SAME target value repeat across columns of one
        # row, so #293's row-label check alone isn't enough -- both
        # columns can legitimately match the same shared row label.
        # Ground truth always picked the RIGHTMOST matching column in
        # both real cases. Column A (leftmost, WRONG) is listed FIRST
        # in cell_boxes, to prove this isn't accidental list-order luck.
        table_ocr_preds = [
            {
                "texts": ["Total", "Equity", "$100,000", "$100,000"],
                "boxes": [
                    [10, 20, 50, 35], [55, 20, 95, 35],
                    [105, 20, 150, 35],
                    [205, 20, 250, 35],
                ],
                "cell_boxes": [
                    [100, 15, 155, 55],
                    [200, 15, 255, 55],
                    [5, 15, 95, 55],
                ],
            }
        ]
        with patch("module2_ocr_extraction.build_word_reconstruction", side_effect=_empty_word_reconstruction):
            fields = {"total_equity": 100000.0}
            boxes = find_sensitive_boxes(_FAKE_IMAGE, fields, table_ocr_preds=table_ocr_preds)
        equity_boxes = [b for b in boxes if b["field"] == "total_equity"]
        assert len(equity_boxes) == 1
        # Column B's value fragment starts at pixel x=205 -- confirm
        # the returned box is column B's, not column A's (x=105).
        assert abs(equity_boxes[0]["x_pct"] - 205 / 400) < 1e-9

    def test_boxes_to_composite_pct_single_page_is_identity():
        # Issue #286 -- a single-page document must reduce to exactly the
        # box's own original page-local pct, unchanged (offset 0,
        # composite dimensions == the one page's own).
        page = np.zeros((200, 100, 3), dtype=np.uint8)
        boxes = [{"field": "bsb", "value": "x", "x_pct": 0.1, "y_pct": 0.2, "w_pct": 0.3, "h_pct": 0.1, "page_index": 0}]
        converted = boxes_to_composite_pct(boxes, [page])
        assert converted[0]["x_pct"] == 0.1
        assert converted[0]["y_pct"] == 0.2
        assert converted[0]["w_pct"] == 0.3
        assert converted[0]["h_pct"] == 0.1
        assert "page_index" not in converted[0]

    def test_boxes_to_composite_pct_offsets_later_pages():
        # Two equal-height 100px pages stacked -> composite is 200px
        # tall. A page-1 (second page) box at y_pct=0.5 (its own 100px
        # page's midpoint, pixel 50) must land at composite pixel
        # 100+50=150, i.e. composite y_pct=0.75.
        page0 = np.zeros((100, 50, 3), dtype=np.uint8)
        page1 = np.zeros((100, 50, 3), dtype=np.uint8)
        boxes = [
            {"field": "name", "value": "a", "x_pct": 0.0, "y_pct": 0.1, "w_pct": 0.2, "h_pct": 0.1, "page_index": 0},
            {"field": "bsb", "value": "b", "x_pct": 0.0, "y_pct": 0.5, "w_pct": 0.2, "h_pct": 0.1, "page_index": 1},
        ]
        converted = boxes_to_composite_pct(boxes, [page0, page1])
        assert converted[0]["y_pct"] == 0.05  # page 0, unchanged (offset 0)
        assert converted[1]["y_pct"] == 0.75  # page 1, offset by page 0's full height

    def test_boxes_to_composite_pct_pads_narrower_page_width():
        # A box on a narrower page must have its x_pct rescaled against
        # the composite's own (wider) max width, matching
        # stack_pages_vertically's own right-padding of narrower pages.
        wide_page = np.zeros((50, 100, 3), dtype=np.uint8)
        narrow_page = np.zeros((50, 50, 3), dtype=np.uint8)
        boxes = [{"field": "abn", "value": "x", "x_pct": 0.5, "y_pct": 0.0, "w_pct": 0.1, "h_pct": 0.1, "page_index": 1}]
        converted = boxes_to_composite_pct(boxes, [wide_page, narrow_page])
        # narrow page's x_pct=0.5 is pixel 25 on its own 50px-wide page;
        # against the composite's 100px width, that's x_pct=0.25.
        assert converted[0]["x_pct"] == 0.25

    tests = [
        test_single_occurrence_regex_field,
        test_multiple_occurrences_regex_field,
        test_label_anchored_skips_rejected_candidate,
        test_label_anchored_field_redacts_every_occurrence,
        test_label_anchored_field_does_not_redact_a_different_value,
        test_absent_field_produces_no_span,
        test_income_field_uses_matching_basis_pattern,
        test_annual_salary_field_produces_span,
        test_annual_salary_field_absent_produces_no_span,
        test_all_spans_satisfy_text_slice_invariant,
        test_single_word_box,
        test_union_box_margin_clamps_at_image_edge,
        test_union_box_bottom_margin_clamped_by_gap_to_next_line,
        test_absent_field_no_box,
        test_value_not_in_fields_produces_no_box,
        test_annual_salary_field_produces_box,
        test_annual_salary_field_absent_produces_no_box,
        test_label_value_line_split_falls_back_to_value_search_for_box,
        test_label_value_fallback_does_not_duplicate_when_same_line_already_boxed,
        test_income_line_split_falls_back_to_bare_amount_search_for_box,
        test_apply_redaction_image_blacks_out_region_only,
        test_apply_redaction_image_no_items_returns_unchanged_copy,
        test_balance_sheet_totals_are_sensitive_field_keys,
        test_balance_sheet_field_finds_value_on_docx_joined_row,
        test_balance_sheet_field_skips_parenthetical_alternate_name,
        test_balance_sheet_field_absent_produces_no_span,
        test_balance_sheet_field_falls_back_to_bare_value_when_label_absent,
        test_balance_sheet_field_fallback_does_not_fire_when_label_already_matched,
        test_balance_sheet_field_box_found_via_table_cell,
        test_balance_sheet_field_no_matching_cell_produces_no_box,
        test_balance_sheet_field_disambiguates_duplicate_value_by_row_label,
        test_balance_sheet_field_multi_column_tie_prefers_rightmost_labeled_candidate,
        test_boxes_to_composite_pct_single_page_is_identity,
        test_boxes_to_composite_pct_offsets_later_pages,
        test_boxes_to_composite_pct_pads_narrower_page_width,
    ]
    for test in tests:
        test()
        print(f"PASS {test.__name__}")
    print(f"\n{len(tests)} tests passed")
