"""
Idle motion + emotion blend loop for PC Agent.

Single master loop at 50ms with rich idle behavior:
- Continuous head sway + eye drift (sine waves)
- Random gaze targets (look at viewer / look away / thinking)
- Double blink, slow blink, random blink timing
- Eyebrow micro-expressions
- Smooth emotion blend in/out
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
_P_BROW_L     = _idle_cfg.get("param_brow_l",      "BrowLeftY")
_P_BROW_R     = _idle_cfg.get("param_brow_r",      "BrowRightY")
_P_MOUTH_SMILE = _idle_cfg.get("param_mouth_smile", "MouthSmile")

TICK        = 0.05   # 50 ms
BLEND_SPEED = 5.0    # emotion blend units/second

_task: asyncio.Task | None = None

_emotion_params: dict[str, float] = {}
_emotion_blend_target: float = 0.0
_emotion_expire_at: float = 0.0

_mouth_value: float | None = None


def set_mouth(value: float | None) -> None:
    global _mouth_value
    _mouth_value = value


def set_emotion(params: dict, duration: float) -> None:
    global _emotion_params, _emotion_blend_target, _emotion_expire_at
    _emotion_params = {k: float(v) for k, v in params.items()}
    _emotion_blend_target = 1.0
    try:
        loop = asyncio.get_event_loop()
        _emotion_expire_at = (loop.time() + duration) if duration > 0 else float("inf")
    except RuntimeError:
        _emotion_expire_at = float("inf")


# ── Gaze state machine ────────────────────────────────────────────────────────

class _GazeState:
    IDLE       = "idle"        # gentle sine sway
    LOOK_AWAY  = "look_away"   # head/eyes drifted off-screen
    THINKING   = "thinking"    # looking up + slight tilt
    AT_VIEWER  = "at_viewer"   # direct gaze, slightly forward

_gaze = _GazeState.IDLE
_gaze_timer   = random.uniform(4.0, 8.0)
_gaze_target  = (0.0, 0.0, 0.0, 0.0, 0.0)  # (head_x, head_y, head_z, eye_x, eye_y)
_gaze_current = (0.0, 0.0, 0.0, 0.0, 0.0)
_GAZE_LERP    = 0.06  # per-tick lerp speed for gaze transitions


def _new_gaze_target() -> tuple:
    state = random.choices(
        [_GazeState.IDLE, _GazeState.LOOK_AWAY, _GazeState.THINKING, _GazeState.AT_VIEWER],
        weights=[40, 25, 20, 15],
    )[0]
    if state == _GazeState.IDLE:
        return state, random.uniform(3.0, 7.0), (0.0, 0.0, 0.0, 0.0, 0.0)
    if state == _GazeState.LOOK_AWAY:
        side = random.choice([-1, 1])
        hx = side * random.uniform(6.0, 14.0)
        hy = random.uniform(-3.0, 3.0)
        ex = side * random.uniform(0.3, 0.6)
        ey = random.uniform(-0.1, 0.2)
        return state, random.uniform(2.0, 5.0), (hx, hy, hx * -0.15, ex, ey)
    if state == _GazeState.THINKING:
        side = random.choice([-1, 0, 1]) * random.uniform(2.0, 6.0)
        return state, random.uniform(1.5, 3.5), (side, random.uniform(3.0, 8.0), side * -0.1, side * 0.05, 0.2)
    # AT_VIEWER
    return state, random.uniform(2.0, 4.0), (
        random.uniform(-2.0, 2.0), random.uniform(-1.0, 1.0), 0.0,
        random.uniform(-0.1, 0.1), random.uniform(-0.05, 0.1),
    )


async def _loop() -> None:
    global _gaze, _gaze_timer, _gaze_target, _gaze_current, _emotion_blend_target

    t = 0.0
    blend = 0.0

    # Blink state
    blink_timer  = random.uniform(2.5, 5.0)
    blink_state  = 0.0
    blink_closing = False
    blink_count  = 0   # for double-blink
    blink_pause  = 0.0

    # Eyebrow drift
    brow_val = 0.0
    brow_target = 0.0
    brow_timer = random.uniform(3.0, 8.0)

    _gaze, _gaze_timer, _gaze_target = _new_gaze_target()

    while True:
        await asyncio.sleep(TICK)
        t += TICK
        blink_timer  -= TICK
        brow_timer   -= TICK
        _gaze_timer  -= TICK

        # ── Emotion expiry ────────────────────────────────────────────────────
        if asyncio.get_event_loop().time() >= _emotion_expire_at and _emotion_blend_target > 0.0:
            _emotion_blend_target = 0.0
        step = BLEND_SPEED * TICK
        blend = max(0.0, min(1.0, blend + step if blend < _emotion_blend_target else blend - step))

        # ── Base sine sway ────────────────────────────────────────────────────
        base_hx = (math.sin(t * 2 * math.pi * 0.07) * 2.5
                   + math.sin(t * 2 * math.pi * 0.13) * 0.8)
        base_hy = (math.sin(t * 2 * math.pi * 0.05) * 1.8
                   + math.sin(t * 2 * math.pi * 0.11) * 0.6)
        base_hz = base_hx * -0.15
        base_ex = math.sin(t * 2 * math.pi * 0.04) * 0.15
        base_ey = math.sin(t * 2 * math.pi * 0.06) * 0.10

        # ── Gaze state machine ────────────────────────────────────────────────
        if _gaze_timer <= 0:
            _gaze, _gaze_timer, _gaze_target = _new_gaze_target()

        # Lerp current gaze toward target
        gc = _gaze_current
        gt = _gaze_target
        lr = _GAZE_LERP
        _gaze_current = tuple(gc[i] + (gt[i] - gc[i]) * lr for i in range(5))
        g_hx, g_hy, g_hz, g_ex, g_ey = _gaze_current

        head_x = base_hx + g_hx
        head_y = base_hy + g_hy
        head_z = base_hz + g_hz
        eye_x  = base_ex + g_ex
        eye_y  = base_ey + g_ey

        # ── Eyebrow micro-drift ───────────────────────────────────────────────
        if brow_timer <= 0:
            brow_target = random.uniform(-0.15, 0.10)
            brow_timer  = random.uniform(3.0, 8.0)
        brow_val += (brow_target - brow_val) * 0.04

        # ── Blink ─────────────────────────────────────────────────────────────
        if blink_pause > 0:
            blink_pause -= TICK
        elif blink_timer <= 0 and not blink_closing:
            blink_closing = True
            blink_count  = 2 if random.random() < 0.25 else 1  # 25% double-blink

        if blink_closing:
            speed = 0.06 if blink_count == 1 else 0.05  # slow blink vs normal
            blink_state = min(blink_state + TICK / speed, 1.0)
            if blink_state >= 1.0:
                blink_closing = False
        else:
            blink_state = max(blink_state - TICK / 0.10, 0.0)
            if blink_state <= 0.0 and blink_count > 1:
                blink_count -= 1
                blink_closing = True
                blink_pause   = 0.06
            elif blink_state <= 0.0:
                blink_timer = random.uniform(2.5, 6.0)
        eye_open = 1.0 - blink_state

        mouth = _mouth_value if _mouth_value is not None else 0.0

        idle: dict[str, float] = {
            _P_ANGLE_X:     head_x,
            _P_ANGLE_Y:     head_y,
            _P_ANGLE_Z:     head_z,
            _P_EYE_BALL_X:  eye_x,
            _P_EYE_BALL_Y:  eye_y,
            _P_EYE_L_OPEN:  eye_open,
            _P_EYE_R_OPEN:  eye_open,
            _P_MOUTH_OPEN:  mouth,
            _P_BROW_L:      brow_val,
            _P_BROW_R:      brow_val,
            _P_MOUTH_SMILE: 0.0,
        }

        # ── Blend idle + emotion ──────────────────────────────────────────────
        all_keys = set(idle.keys()) | set(_emotion_params.keys())
        final: dict[str, float] = {
            k: idle.get(k, 0.0) + (_emotion_params.get(k, idle.get(k, 0.0)) - idle.get(k, 0.0)) * blend
            for k in all_keys
        }

        # ── Inject ────────────────────────────────────────────────────────────
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
