"""Run the live loop against the demo account. Ctrl+C to stop."""
import logging

from trader.config import CONFIG
from trader.live import run_live

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[logging.StreamHandler(),
              logging.FileHandler("trader.log", encoding="utf-8")],
)

if __name__ == "__main__":
    run_live(CONFIG)
