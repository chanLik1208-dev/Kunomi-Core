"""
Idle motion + emotion blend loop for PC Agent.

Single master loop at 50ms:
- Computes idle values (breathing, head sway, eye drift, blink)
- Smoothly blends toward emotion target when emotion is active
- Blends back to idle after emotion duration expires
- Drives MouthOpen via lip sync during TTS playback
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
_P_EYE_BALL_X = _idle_cfg.get("param_eye_ball_x", "EyeRightX")
_P_EYE_BALL_Y = _idle_cfg.get("param_eye_ball_y", "EyeRightY")
_P_EYE_L_OPEN = _idle_cfg.get("param_eye_l_open", "EyeOpenLeft")
_P_EYE_R_OPEN = _idle_cfg.get("param_eye_r_open", "EyeOpenRight")
_P_MOUTH_OPEN = _idle_cfg.get("param_mouth_open",  "MouthOpen")

TICK        = 0.05  # 50 ms
BLEND_SPEED = 5.0   # blend units/second → 0→1 in 0.2s

_task: asyncio.Task | None = None

# Emotion state (written from set_emotion, read by _loop)
_emotion_params: dict[str, float] = {}
_emotion_blend_target: float = 0.0
_emotion_expire_at: float = 0.0

# Lip sync
_mouth_value: float | None = None


def set_mouth(value: float | None) -> None:
    global _mouth_value
    _mouth_value = value


def set_emotion(params: dict, duration: float) -> None:
    """Blend into emotion. duration=0 holds forever until next set_emotion()."""
    global _emotion_params, _emotion_blend_target, _emotion_expire_at
    _emotion_params = {k: float(v) for k, v in params.items()}
    _emotion_blend_target = 1.0
    try:
        loop = asyncio.get_event_loop()
        _emotion_expire_at = (loop.time() + duration) if duration > 0 else float("inf")
    except RuntimeError:
        _emotion_expire_at = float("inf")


async def _loop() -> None:
    global _emotion_blend_target

    t = 0.0
    blend = 0.0
    blink_timer = random.uniform(3.0, 6.0)
    blink_state = 0.0
    blink_closing = False

    while True:
        await asyncio.sleep(TICK)
        t += TICK
        blink_timer -= TICK

        # ── Check emotion expiry ─────────────────────────────────────────────
        now = asyncio.get_event_loop().time()
        if now >= _emotion_expire_at and _emotion_blend_target > 0.0:
            _emotion_blend_target = 0.0

        # ── Smooth blend ─────────────────────────────────────────────────────
        step = BLEND_SPEED * TICK
        blend = blend + step if blend < _emotion_blend_target else blend - step
        blend = max(0.0, min(1.0, blend))

        # ── Idle values ───────────────────────────────────────────────────────
        head_x = (math.sin(t * 2 * math.pi * 0.07) * 4.0
                  + math.sin(t * 2 * math.pi * 0.13) * 1.5)
        head_y = (math.sin(t * 2 * math.pi * 0.05) * 3.0
                  + math.sin(t * 2 * math.pi * 0.11) * 1.0)
        head_z = head_x * -0.2

        eye_x = (math.sin(t * 2 * math.pi * 0.04) * 0.40
                 + math.sin(t * 2 * math.pi * 0.09) * 0.15)
        eye_y = math.sin(t * 2 * math.pi * 0.06) * 0.25

        if blink_timer <= 0 and not blink_closing:
            blink_closing = True
        if blink_closing:
            blink_state = min(blink_state + TICK / 0.08, 1.0)
            if blink_state >= 1.0:
                blink_closing = False
        else:
            blink_state = max(blink_state - TICK / 0.12, 0.0)
            if blink_state <= 0.0:
                blink_timer = random.uniform(3.0, 7.0)
        eye_open = 1.0 - blink_state

        mouth = _mouth_value if _mouth_value is not None else 0.0

        idle: dict[str, float] = {
            _P_ANGLE_X:    head_x,
            _P_ANGLE_Y:    head_y,
            _P_ANGLE_Z:    head_z,
            _P_EYE_BALL_X: eye_x,
            _P_EYE_BALL_Y: eye_y,
            _P_EYE_L_OPEN: eye_open,
            _P_EYE_R_OPEN: eye_open,
            _P_MOUTH_OPEN: mouth,
        }

        # ── Blend idle + emotion ──────────────────────────────────────────────
        all_keys = set(idle.keys()) | set(_emotion_params.keys())
        final: dict[str, float] = {
            k: idle.get(k, 0.0) + (_emotion_params.get(k, idle.get(k, 0.0)) - idle.get(k, 0.0)) * blend
            for k in all_keys
        }

        # ── Inject ───────────────────────────────────────────────────────────
        try:
            from pc_agent.vts import vts_inject
            await vts_inject(list(final.keys()), list(final.values()))
        except Exception as _e:
            logger.warning("idle inject error: %s", _e)
            await asyncio.sleep(0.5)


def start() -> None:
    global _task
    if _task and not _task.done():
        return
    _task = asyncio.create_task(_loop())
    logger.info("Idle motion loop started")
