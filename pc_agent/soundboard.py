import logging
import yaml
from pathlib import Path

logger = logging.getLogger(__name__)

_config = yaml.safe_load(Path("config/settings.yaml").read_text(encoding="utf-8"))
_SOUNDS_DIR = Path(_config.get("soundboard", {}).get("sounds_dir", "assets/sounds"))
_MAPPING: dict[str, str] = yaml.safe_load(
    Path("config/soundboard.yaml").read_text(encoding="utf-8")
)


def play(name: str) -> str:
    """
    播放音效。回傳實際播放的檔案路徑。
    優先使用 pygame（跨平台），fallback 用 winsound（Windows only）。
    """
    filename = _MAPPING.get(name)
    if not filename:
        raise ValueError(f"未知音效名稱：{name}，請檢查 config/soundboard.yaml")

    path = _SOUNDS_DIR / filename
    if not path.exists():
        raise FileNotFoundError(f"音效檔不存在：{path}")

    try:
        import pygame
        pygame.mixer.init()
        pygame.mixer.Sound(str(path)).play()
        logger.info("播放音效（pygame）：%s", path)
    except ImportError:
        import winsound
        winsound.PlaySound(str(path), winsound.SND_FILENAME | winsound.SND_ASYNC)
        logger.info("播放音效（winsound）：%s", path)

    return str(path)
