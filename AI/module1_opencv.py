import cv2
import numpy as np

BLUR_THRESHOLD = 100.0
CONTRAST_THRESHOLD = 15.0
MAX_DESKEW_ANGLE = 15.0
# ponytail: fixed 2x, gated to inputs smaller than this on their short side.
# Measured (AI spot-check, 2026-08-08) against 3 real low-res payslip photos:
# 2x recovered most of the reachable salary-digit misses; 3x/4x plateaued and
# on one sample started misreading upscaling noise as a name where 1x/2x
# correctly returned None -- a wrong PII value is worse than a miss, so this
# stays capped at 2x rather than chasing more gain. Synthetic benchmark
# renders (measure_accuracy_tesseract.py, ~2000px+) are already well above
# this threshold and never trigger it -- upgrade the factor/threshold only
# after measuring against more real low-res samples, not synthetic ones.
UPSCALE_MIN_DIM = 1000
UPSCALE_FACTOR = 2.0


def to_grayscale(img: np.ndarray) -> np.ndarray:
    if len(img.shape) == 2:
        return img
    return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)


def upscale_if_small(gray: np.ndarray, min_dim: int = UPSCALE_MIN_DIM, factor: float = UPSCALE_FACTOR) -> np.ndarray:
    if min(gray.shape[:2]) >= min_dim:
        return gray
    return cv2.resize(gray, None, fx=factor, fy=factor, interpolation=cv2.INTER_CUBIC)


def denoise(gray: np.ndarray) -> np.ndarray:
    return cv2.fastNlMeansDenoising(gray, h=10, templateWindowSize=7, searchWindowSize=21)


def _skew_angle(gray: np.ndarray) -> float:
    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    coords = cv2.findNonZero(thresh)
    if coords is None:
        return 0.0
    angle = cv2.minAreaRect(coords)[-1]
    # normalize OpenCV's minAreaRect angle convention to a signed rotation
    if angle < -45:
        angle = -(90 + angle)
    else:
        angle = -angle
    # a scan that's off by more than this is a mis-detection, not real skew
    if abs(angle) > MAX_DESKEW_ANGLE:
        return 0.0
    return angle


def deskew(gray: np.ndarray) -> tuple[np.ndarray, float]:
    angle = _skew_angle(gray)
    if angle == 0.0:
        return gray, 0.0
    h, w = gray.shape[:2]
    matrix = cv2.getRotationMatrix2D((w / 2, h / 2), angle, 1.0)
    rotated = cv2.warpAffine(
        gray, matrix, (w, h), flags=cv2.INTER_CUBIC, borderValue=255
    )
    return rotated, angle


def autocrop(gray: np.ndarray, padding: int = 10) -> np.ndarray:
    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return gray
    x, y, w, h = cv2.boundingRect(np.vstack(contours))
    img_h, img_w = gray.shape[:2]
    x0 = max(x - padding, 0)
    y0 = max(y - padding, 0)
    x1 = min(x + w + padding, img_w)
    y1 = min(y + h + padding, img_h)
    return gray[y0:y1, x0:x1]


def quality_score(gray: np.ndarray) -> dict:
    blur_score = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    contrast_score = float(gray.std())
    low_quality = blur_score < BLUR_THRESHOLD or contrast_score < CONTRAST_THRESHOLD
    return {
        "blur_score": blur_score,
        "contrast_score": contrast_score,
        "low_quality": low_quality,
    }


def enhance(img: np.ndarray) -> dict:
    gray = to_grayscale(img)
    gray = upscale_if_small(gray)
    denoised = denoise(gray)
    deskewed, angle = deskew(denoised)
    cropped = autocrop(deskewed)
    metrics = quality_score(cropped)
    return {
        "image": cropped,
        "deskew_angle": angle,
        **metrics,
    }


if __name__ == "__main__":
    for path in ("sample_payslip.png", "sample_payslip_degraded.jpg"):
        img = cv2.imread(path)
        assert img is not None, f"could not load {path}"
        result = enhance(img)
        out_path = path.rsplit(".", 1)[0] + "_enhanced.png"
        cv2.imwrite(out_path, result["image"])
        print(
            f"{path}: angle={result['deskew_angle']:.2f} "
            f"blur={result['blur_score']:.1f} contrast={result['contrast_score']:.1f} "
            f"low_quality={result['low_quality']} -> {out_path}"
        )
