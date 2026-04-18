import sys
import logging
import uvicorn
import yaml
from pathlib import Path

# Ensure project root is in sys.path so 'pc_agent' package is importable
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)

config = yaml.safe_load((_ROOT / "config/settings.yaml").read_text(encoding="utf-8"))

if __name__ == "__main__":
    uvicorn.run(
        "pc_agent.server:app",
        host="0.0.0.0",
        port=8100,
        reload=False,
    )
