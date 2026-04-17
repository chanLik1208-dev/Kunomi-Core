import logging
import uvicorn
import yaml
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)

config = yaml.safe_load(Path("config/settings.yaml").read_text(encoding="utf-8"))

if __name__ == "__main__":
    uvicorn.run(
        "pc_agent.server:app",
        host="0.0.0.0",
        port=8100,
        reload=False,
    )
