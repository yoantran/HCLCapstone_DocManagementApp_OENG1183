"""
Keep-alive ping for the Modal GPU deployment during a live demo. NOT
meant to run continuously/permanently -- that would burn real budget for
no reason outside an actual demo window. Pings a cheap endpoint (/demo,
static HTML, never touches the OCR pipeline) more often than Modal's own
scaledown_window (300s, see modal_app.py) so the container never scales
to zero mid-demo.

Auto-stops after MAX_DURATION_HOURS regardless of Ctrl+C -- forgetting
to stop this manually can't silently burn budget for hours/overnight.

Usage:
    python keep_alive_demo.py
    (Ctrl+C to stop early; auto-stops after 3 hours either way)

stdlib only, no new dependency -- this is a throwaway ops script, not
shipped in the Docker image or added to requirements.txt.
"""

import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta

MODAL_URL = "https://kiev2k4--hcl-tco-ai-service-aiservice-fastapi-app.modal.run"
PING_INTERVAL_SECONDS = 240  # under modal_app.py's 300s scaledown_window
MAX_DURATION_HOURS = 3


def ping() -> str:
    try:
        with urllib.request.urlopen(f"{MODAL_URL}/demo", timeout=30) as resp:
            return "ok" if resp.status == 200 else f"HTTP {resp.status}"
    except urllib.error.URLError as e:
        return f"failed: {e}"


def main():
    deadline = datetime.now() + timedelta(hours=MAX_DURATION_HOURS)
    print(
        f"Keep-alive started. Pinging every {PING_INTERVAL_SECONDS}s, "
        f"auto-stop at {deadline.strftime('%H:%M:%S')} "
        f"(or Ctrl+C to stop early)."
    )

    try:
        while datetime.now() < deadline:
            status = ping()
            remaining = deadline - datetime.now()
            print(
                f"[{datetime.now().strftime('%H:%M:%S')}] ping {status} "
                f"-- auto-stop in {remaining}"
            )
            time.sleep(PING_INTERVAL_SECONDS)
    except KeyboardInterrupt:
        print("\nStopped manually.")
        return

    print("Max duration reached, stopping automatically.")


if __name__ == "__main__":
    main()
