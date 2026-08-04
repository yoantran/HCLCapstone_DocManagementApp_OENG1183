import random
import re
import sys
from pathlib import Path

import docx
from faker import Faker

fake = Faker("vi_VN")

VN_STREETS = ["Nguyễn Trãi", "Lê Lợi", "Trần Hưng Đạo", "Hai Bà Trưng", "Điện Biên Phủ",
              "Cách Mạng Tháng Tám", "Nguyễn Văn Cừ", "Hoàng Diệu", "Lý Thường Kiệt", "Phan Đình Phùng"]
VN_WARDS = ["Phường 1", "Phường Bến Nghé", "Phường Tân Định", "Phường 5", "Phường An Phú", "Phường Bình Hưng"]
VN_DISTRICTS = ["Quận 1", "Quận 3", "Quận Bình Thạnh", "Quận Gò Vấp", "Huyện Nhà Bè", "Quận Cầu Giấy"]
VN_CITIES = ["TP. Hồ Chí Minh", "Hà Nội", "Đà Nẵng", "Cần Thơ", "Hải Phòng"]
COMPANIES = [
    "CÔNG TY TNHH GIẢI PHÁP CÔNG NGHỆ VIỆT", "CÔNG TY CỔ PHẦN ĐẦU TƯ MINH PHÁT",
    "CÔNG TY TNHH THƯƠNG MẠI DỊCH VỤ AN KHANG", "CÔNG TY CỔ PHẦN XÂY DỰNG HOÀNG LONG",
    "CÔNG TY TNHH SẢN XUẤT THƯƠNG MẠI PHÚ CƯỜNG",
]
POSITIONS = [
    "Nhân viên Kế toán", "Nhân viên Kinh doanh", "Chuyên viên Nhân sự", "Kỹ sư phần mềm",
    "Trưởng phòng Marketing", "Nhân viên Hành chính", "Chuyên viên Chăm sóc khách hàng",
    "Nhân viên Kho vận", "Kế toán trưởng", "Nhân viên Bảo trì",
]


def fake_name():
    return fake.name()


def fake_address():
    return (f"Số {random.randint(1, 300)} {random.choice(VN_STREETS)}, "
            f"{random.choice(VN_WARDS)}, {random.choice(VN_DISTRICTS)}, {random.choice(VN_CITIES)}")


def fake_phone():
    prefix = random.choice(["03", "05", "07", "08", "09"])
    return f"{prefix}{random.randint(10000000, 99999999)}"


def fake_cccd():
    return "".join(str(random.randint(0, 9)) for _ in range(12))


def fake_salary():
    return f"{random.randint(5, 50) * 1_000_000:,}"


def fake_date():
    d = fake.date_between(start_date="-5y", end_date="today")
    return d.strftime("%d/%m/%Y")


def fake_position():
    return random.choice(POSITIONS)


def fake_company():
    return random.choice(COMPANIES)


# field_key matches field_extraction.py's output dict keys (name, address,
# cccd, phone, salary) so a generated value can be checked against what
# extraction actually found. None means this filler doesn't correspond to
# any field our extraction logic tries to recover (position, company,
# employee ID) -- generated for document realism, not scored.

# colon-anchored -- for inline "Label: value" text within a single paragraph
LABEL_FILLERS = [
    (re.compile(r"(?:H[oọ]?\s*(?:và)?\s*t[eê]n|BÊN\s*B|T[eê]n\s*NV|[ÔO]ng\s*/\s*[Bb][àa])\s*:", re.I), fake_name, "name"),
    (re.compile(r"[ĐD][iị]a\s*ch[iỉ]\s*:", re.I), fake_address, "address"),
    (re.compile(r"[Ss][ốo]\s*CCCD|CCCD\s*/\s*H[ộo]\s*chi[ếe]u", re.I), fake_cccd, "cccd"),
    (re.compile(r"[Đđ]i[ệe]n\s*tho[ạa]i\s*:", re.I), fake_phone, "phone"),
    (re.compile(r"M[ứu]c\s*l[ưu][ơo]ng(?:\s*ch[íi]nh)?\s*:", re.I), fake_salary, "salary"),
    (re.compile(r"[Cc]h[ứu]c\s*danh|[Cc]h[ứu]c\s*v[ụu]|[Vv][ịi]\s*tr[íi]\s*c[ôo]ng\s*t[áa]c", re.I), fake_position, None),
    (re.compile(r"BÊN\s*A\s*:\s*C[ÔO]NG\s*TY", re.I), fake_company, None),
]

# bare (no colon required) -- for table cells where the whole cell is just
# the label and the value lives in an adjacent cell, e.g. "Họ Và Tên" alone
# in one cell with the value expected in the next cell over.
LABEL_FILLERS_BARE = [
    (re.compile(r"H[oọ]?\s*[Vv][àa]?\s*T[eê]n|BÊN\s*B|T[eê]n\s*NV|[ÔO]ng\s*/\s*[Bb][àa]", re.I), fake_name, "name"),
    (re.compile(r"[ĐD][iị]a\s*ch[iỉ]", re.I), fake_address, "address"),
    (re.compile(r"[Ss][ốo]\s*CCCD|CCCD\s*/\s*H[ộo]\s*chi[ếe]u|CMND", re.I), fake_cccd, "cccd"),
    (re.compile(r"[Đđ]i[ệe]n\s*tho[ạa]i", re.I), fake_phone, "phone"),
    (re.compile(r"M[ứu]c\s*l[ưu][ơo]ng(?:\s*ch[íi]nh)?|L[ưu][ơo]ng\s*ch[íi]nh|L[ưu][ơo]ng\s*c[ơo]\s*b[ảa]n", re.I), fake_salary, "salary"),
    (re.compile(r"[Cc]h[ứu]c\s*danh|[Cc]h[ứu]c\s*v[ụu]|[Vv][ịi]\s*tr[íi]\s*c[ôo]ng\s*t[áa]c", re.I), fake_position, None),
    (re.compile(r"M[ãa]\s*Nh[âa]n\s*Vi[êe]n", re.I), lambda: str(random.randint(1000, 9999)), None),
]

_PLACEHOLDER_RE = re.compile(r"^[\s.…_\-]*$")


def _is_placeholder(text: str) -> bool:
    return bool(_PLACEHOLDER_RE.match(text.strip())) or not text.strip()


def _try_fill_paragraph_text(text: str) -> tuple[str, bool, str | None, str | None]:
    for label_re, generator, field_key in LABEL_FILLERS:
        m = label_re.search(text)
        if not m:
            continue
        after = text[m.end():]
        if _is_placeholder(after):
            value = generator()
            return text[:m.end()] + " " + value, True, field_key, value
    return text, False, None, None


def _set_paragraph_text(p, new_text: str) -> None:
    for run in p.runs:
        run.text = ""
    if p.runs:
        p.runs[0].text = new_text
    else:
        p.add_run(new_text)


def fill_docx(src_path: str, dst_path: str, seed: int | None = None) -> tuple[int, dict[str, list[str]]]:
    if seed is not None:
        random.seed(seed)
        Faker.seed(seed)

    doc = docx.Document(src_path)
    filled = 0
    ground_truth: dict[str, list[str]] = {}

    def record(field_key: str | None, value: str | None) -> None:
        if field_key is not None:
            ground_truth.setdefault(field_key, []).append(value)

    for p in doc.paragraphs:
        new_text, did_fill, field_key, value = _try_fill_paragraph_text(p.text)
        if did_fill:
            _set_paragraph_text(p, new_text)
            filled += 1
            record(field_key, value)

    for table in doc.tables:
        for row in table.rows:
            cells = row.cells
            for i, cell in enumerate(cells):
                # same-cell "Label: value" first (colon-anchored)
                new_text, did_fill, field_key, value = _try_fill_paragraph_text(cell.text)
                if did_fill and cell.paragraphs:
                    _set_paragraph_text(cell.paragraphs[0], new_text)
                    filled += 1
                    record(field_key, value)
                    continue
                # bare label alone in this cell, value expected in the next cell
                matched_generator = None
                matched_field_key = None
                for label_re, generator, field_key in LABEL_FILLERS_BARE:
                    if label_re.search(cell.text):
                        matched_generator = generator
                        matched_field_key = field_key
                        break
                if matched_generator is None:
                    continue
                if i + 1 < len(cells) and _is_placeholder(cells[i + 1].text):
                    target = cells[i + 1]
                    if target.paragraphs:
                        value = matched_generator()
                        _set_paragraph_text(target.paragraphs[0], value)
                        filled += 1
                        record(matched_field_key, value)

    Path(dst_path).parent.mkdir(parents=True, exist_ok=True)
    doc.save(dst_path)
    return filled, ground_truth


if __name__ == "__main__":
    src = sys.argv[1]
    dst = sys.argv[2]
    seed = int(sys.argv[3]) if len(sys.argv) > 3 else None
    n, gt = fill_docx(src, dst, seed=seed)
    print(f"filled {n} fields: {dst}")
    print(f"ground truth: {gt}")
