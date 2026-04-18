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

from tools import load_all

load_all()

if __name__ == "__main__":
    uvicorn.run(
        "api.server:app",
        host=config["api"]["host"],
        port=config["api"]["port"],
        reload=False,   # reload=True 會 fork 子行程，導致 ASR 執行緒失效
    )
