import json, os, requests
from datetime import datetime, timedelta
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

JST = timedelta(hours=9)
ORIGIN = os.environ.get("ORIGIN_API", "https://super-duper-octo-carnival-production.up.railway.app")  # 查岗系统 Railway 域名
BARK_KEY = os.environ.get("BARK_API_KEY", "e4xKQoCEQ4fnzNW6UnqiBU")

def _get_device_state():
    """从查岗系统拉取最新手机状态"""
    try:
        r = requests.get(f"{ORIGIN}/device/state", timeout=10)
        data = r.json()
        return (data.get("state") or {}), None
    except Exception as e:
        return {}, f"获取状态失败：{e}"

def check_on_wife(limit=10):
    try:
        r = requests.get(f"{ORIGIN}/activity/summary", timeout=10)
        data = r.json()
    except Exception as e:
        return f"查岗失败：{e}"
    apps = data.get("recent_apps", [])
    ses = data.get("sessions", {})
    lines = [f"最近打开：{', '.join(apps)}" if apps else "暂无记录"]
    if ses:
        for app, secs in sorted(ses.items(), key=lambda x: x[1], reverse=True):
            m, s = divmod(secs, 60)
            lines.append(f"  {app}: {m}分{s}秒")
    return "\n".join(lines)

def bark_alert(title="Reditus", content=""):
    if not content: return "内容不能为空"
    # ★ 自定义推送图标（岁岁给哥哥选的）★
    icon_url = "https://img.remit.ee/api/file/BQACAgUAAyEGAASHRsPbAAEYleJqcwJlzjN1GqNeJJDAdTX9f5ll1AACmi4AAniTmFevtIeddud6zz0E.jpeg"
    url = f"https://api.day.app/{BARK_KEY}/{title}/{content}?icon={icon_url}"
    try:
        r = requests.get(url, timeout=10)
        return "推送成功" if r.status_code == 200 else "推送失败"
    except Exception as e:
        return f"推送异常：{e}"

def get_battery():
    state, err = _get_device_state()
    if err: return err
    return f"电池电量：{state.get('battery', '未知')}%"

def get_location():
    state, err = _get_device_state()
    if err: return err
    return f"当前位置：{state.get('location', '未知')}"

def get_device():
    state, err = _get_device_state()
    if err: return err
    return f"设备名称：{state.get('device', '未知')}"

def get_weather():
    state, err = _get_device_state()
    if err: return err
    return f"天气：{state.get('weather', '未知')}"

def get_brightness():
    state, err = _get_device_state()
    if err: return err
    return f"屏幕亮度：{state.get('brightness', '未知')}"

def get_volume():
    state, err = _get_device_state()
    if err: return err
    return f"音量：{state.get('volume', '未知')}"

TOOLS = [
    {"name": "check_on_wife", "description": "查岗老婆的手机活动", "inputSchema": {"type": "object", "properties": {"limit": {"type": "integer"}}}},
    {"name": "bark_alert", "description": "给老婆手机发推送弹窗", "inputSchema": {"type": "object", "properties": {"title": {"type": "string"}, "content": {"type": "string"}}, "required": ["content"]}},
    {"name": "get_battery", "description": "查看老婆手机电池电量", "inputSchema": {"type": "object", "properties": {}}},
    {"name": "get_location", "description": "查看老婆当前位置", "inputSchema": {"type": "object", "properties": {}}},
    {"name": "get_device", "description": "查看老婆手机设备名称", "inputSchema": {"type": "object", "properties": {}}},
    {"name": "get_weather", "description": "查看老婆所在位置的天气", "inputSchema": {"type": "object", "properties": {}}},
    {"name": "get_brightness", "description": "查看老婆手机屏幕亮度", "inputSchema": {"type": "object", "properties": {}}},
    {"name": "get_volume", "description": "查看老婆手机音量", "inputSchema": {"type": "object", "properties": {}}},
]
FUNCS = {"check_on_wife": check_on_wife, "bark_alert": bark_alert,
         "get_battery": get_battery, "get_location": get_location,
         "get_device": get_device, "get_weather": get_weather,
         "get_brightness": get_brightness, "get_volume": get_volume}

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.post("/mcp")
async def mcp(req: Request):
    body = await req.json()
    method, params = body.get("method"), body.get("params") or {}
    rid = body.get("id")
    if method == "initialize":
        return {"jsonrpc": "2.0", "id": rid, "result": {"protocolVersion": "2024-11-05", "capabilities": {"tools": {}}, "serverInfo": {"name": "查岗MCP", "version": "2.0"}}}
    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": rid, "result": {"tools": TOOLS}}
    if method == "tools/call":
        name = params.get("name")
        args = params.get("arguments") or {}
        if name not in FUNCS:
            return {"jsonrpc": "2.0", "id": rid, "error": {"code": -32601, "message": "未知工具"}}
        result = FUNCS[name](**args)
        return {"jsonrpc": "2.0", "id": rid, "result": {"content": [{"type": "text", "text": str(result)}]}}
    return {"jsonrpc": "2.0", "id": rid, "error": {"code": -32601, "message": f"未知方法: {method}"}}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
