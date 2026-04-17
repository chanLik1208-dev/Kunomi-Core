# 工具箱模組 — 第三階段實作
# 每個工具寫成獨立函數，LLM 輸出 JSON 決定呼叫哪個

TOOL_REGISTRY: dict = {}


def register_tool(name: str):
    def decorator(fn):
        TOOL_REGISTRY[name] = fn
        return fn
    return decorator


async def dispatch(tool_name: str, args: dict):
    fn = TOOL_REGISTRY.get(tool_name)
    if not fn:
        raise ValueError(f"未知工具：{tool_name}")
    return await fn(**args)


def load_all():
    """匯入所有工具子模組，觸發 @register_tool 裝飾器完成註冊。"""
    import importlib
    _modules = ["tools.screenshot", "tools.soundboard", "tools.expression", "tools.memory"]
    for mod in _modules:
        importlib.import_module(mod)
