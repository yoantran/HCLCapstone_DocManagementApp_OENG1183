from PIL import Image, ImageDraw, ImageFont

lines = [
    "PHIẾU LƯƠNG THÁNG 06/2026",
    "Họ và tên: Nguyễn Văn An",
    "Số CCCD: 079201012345",
    "Chức vụ: Nhân viên Kế toán",
    "Lương cơ bản: 15,000,000 VND",
    "Phụ cấp: 2,000,000 VND",
    "Khấu trừ BHXH: 1,500,000 VND",
    "Thực lãnh: 15,500,000 VND",
    "Ngày thanh toán: 05/07/2026",
    "Số điện thoại: 0912345678",
]

img = Image.new("RGB", (900, 500), "white")
draw = ImageDraw.Draw(img)
font = ImageFont.truetype("arial.ttf", 24)

y = 20
for line in lines:
    draw.text((30, y), line, fill="black", font=font)
    y += 45

img.save("sample_payslip.png")
print("saved sample_payslip.png")
