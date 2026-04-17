import base64
import logging
import time
from pathlib import Path

logger = logging.getLogger(__name__)

_SAVE_DIR = Path("screenshots")
_SAVE_DIR.mkdir(exist_ok=True)


def capture() -> tuple[bytes, str]:
    """
    截取主螢幕畫面，回傳 (PNG bytes, 存檔路徑)。
    需在 4070 PC 上執行，依賴 dxcam（Windows only）。
    """
    try:
        import dxcam
        camera = dxcam.create(output_color="BGR")
        frame = camera.grab()
        camera.release()
        if frame is None:
            raise RuntimeError("DXcam 擷取回傳 None，請確認螢幕未關閉")
    except ImportError:
        # 開發環境 fallback：用 PIL 截圖
        logger.warning("dxcam 未安裝，使用 PIL 截圖代替")
        from PIL import ImageGrab
        import numpy as np
        frame = np.array(ImageGrab.grab())

    import cv2
    timestamp = int(time.time())
    save_path = _SAVE_DIR / f"screenshot_{timestamp}.png"
    cv2.imwrite(str(save_path), frame)

    _, buf = cv2.imencode(".png", frame)
    return buf.tobytes(), str(save_path)


def capture_base64() -> tuple[str, str]:
    """回傳 (base64 編碼的 PNG 字串, 存檔路徑)，供 Vision 模型使用。"""
    raw, path = capture()
    return base64.b64encode(raw).decode(), path
