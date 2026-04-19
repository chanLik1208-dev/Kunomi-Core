"""
Idle motion loop for PC Agent.
Continuously injects breathing, head sway, eye movement, and random blinks
into VTube Studio at 50ms intervals to keep the model alive.

Parameter names follow Live2D Cubism defaults; override in settings.yaml
under vtube_studio.idle_motion.
"""
import asyncio
import logging
import math
import random
import yaml
from pathlib import Path

logger = logging.getLogger(__name__)

_cfg = yaml.safe_load(Path("config/settings.yaml").read_text(encoding="utf-8"))
_idle_cfg = _cfg.get("vtube_studio", {}).get("idle_motion", {})

_P_ANGLE_X    = _idle_cfg.get("param_angle_x",    "FaceAngleX")
_P_ANGLE_Y    = _idle_cfg.get("param_angle_y",    "FaceAngleY")
_P_ANGLE_Z    = _idle_cfg.get("param_angle_z",    "FaceAngleZ")
_P_BREATH     = _idle_cfg.get("param_breath",     "Breathing")
_P_EYE_BALL_X = _idle_cfg.get("param_eye_ball_x", "EyeRightX")
_P_EYE_BALL_Y = _idle_cfg.get("param_eye_ball_y", "EyeRightY")
_P_EYE_L_OPEN = _idle_cfg.get("param_eye_l_open", "EyeOpenLeft")
_P_EYE_R_OPEN = _idle_cfg.get("param_eye_r_open", "EyeOpenRight")
_P_MOUTH_OPEN = _idle_cfg.get("param_mouth_open",  "MouthOpen")

TICK = 0.05  # 50 ms

_task: asyncio.Task | None = None
_mouth_value: float | None = None  # set by lip sync, None = closed


def set_mouth(value: float | None) -> None:
    global _mouth_value
    _mouth_value = value


async def _loop(_get_vts_unused=None) -> None:
    t = 0.0
    blink_timer = random.uniform(3.0, 6.0)
    blink_state = 0.0   # 0 = open, 1 = closed
    blink_closing = False

    while True:
        await asyncio.sleep(TICK)
        t += TICK
        blink_timer -= TICK

        # ── Breathing (0.25 Hz, gentle 0→1 sine) ────────────────────────────
        breath = (math.sin(t * 2 * math.pi * 0.25) + 1) / 2

        # ── Head sway (multi-frequency for organic feel) ─────────────────────
        head_x = (math.sin(t * 2 * math.pi * 0.07) * 4.0
                  + math.sin(t * 2 * math.pi * 0.13) * 1.5)
        head_y = (math.sin(t * 2 * math.pi * 0.05) * 3.0
                  + math.sin(t * 2 * math.pi * 0.11) * 1.0)
        head_z = head_x * -0.2

        # ── Eye drift ────────────────────────────────────────────────────────
        eye_x = (math.sin(t * 2 * math.pi * 0.04) * 0.40
                 + math.sin(t * 2 * math.pi * 0.09) * 0.15)
        eye_y = math.sin(t * 2 * math.pi * 0.06) * 0.25

        # ── Blink ────────────────────────────────────────────────────────────
        if blink_timer <= 0 and not blink_closing:
            blink_closing = True
        if blink_closing:
            blink_state = min(blink_state + TICK / 0.08, 1.0)  # close in 80 ms
            if blink_state >= 1.0:
                blink_closing = False
        else:
            blink_state = max(blink_state - TICK / 0.12, 0.0)  # open in 120 ms
            if blink_state <= 0.0:
                blink_timer = random.uniform(3.0, 7.0)
        eye_open = 1.0 - blink_state

        # ── Mouth ────────────────────────────────────────────────────────────
        mouth = _mouth_value if _mouth_value is not None else 0.0

        params = {
            _P_ANGLE_X:    head_x,
            _P_ANGLE_Y:    head_y,
            _P_ANGLE_Z:    head_z,
            _P_BREATH:     breath,
            _P_EYE_BALL_X: eye_x,
            _P_EYE_BALL_Y: eye_y,
            _P_EYE_L_OPEN: eye_open,
            _P_EYE_R_OPEN: eye_open,
            _P_MOUTH_OPEN: mouth,
        }

        try:
            from pc_agent.vts import vts_inject
            await vts_inject(list(params.keys()), list(params.values()))
        except Exception:
            await asyncio.sleep(1.0)  # back off on VTS error


def start() -> None:
    global _task
    if _task and not _task.done():
        return
    _task = asyncio.create_task(_loop())
    logger.info("Idle motion loop started")
