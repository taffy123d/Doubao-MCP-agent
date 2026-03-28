"""天气查询技能实现（兼容中文+国内网络稳定版）"""
import httpx
from mcp.server.fastmcp import FastMCP
from config import settings
try:
    from pypinyin import lazy_pinyin
except Exception:
    lazy_pinyin = None

def _has_chinese(s: str) -> bool:
    return any('\u4e00' <= ch <= '\u9fff' for ch in s)

def _to_pinyin(name: str) -> str:
    if not lazy_pinyin or not _has_chinese(name):
        return name
    parts = lazy_pinyin(name)
    return "".join(p.capitalize() for p in parts)

def register_weather_tool(mcp: FastMCP):
    @mcp.tool()
    async def get_city_weather(city_name: str, forecast_days: int = 1) -> str:
        """查询城市天气，支持中文城市：北京/上海/广州/深圳/成都等"""
        # 核心修复：中文城市 → 动态拼音转换（支持全国城市）
        query_name = _to_pinyin(city_name)
        forecast_days = max(1, min(forecast_days, 2))

        try:
            async with httpx.AsyncClient(timeout=8) as client:
                # 1. 获取城市经纬度
                geo_resp = await client.get(settings.GEOCODING_API_URL, params={
                    "name": query_name, "count": 1, "language": "zh-CN", "format": "json"
                })
                geo_data = geo_resp.json()
                if not geo_data.get("results"):
                    return f"❌ 未找到城市：{city_name}\n支持城市：北京、上海、广州、深圳、成都、重庆"

                # 2. 获取天气
                city = geo_data["results"][0]
                weather_resp = await client.get(settings.WEATHER_API_URL, params={
                    "latitude": city["latitude"], "longitude": city["longitude"],
                    "current": "temperature_2m,weather_code,wind_speed_10m",
                    "daily": "temperature_2m_max,temperature_2m_min",
                    "timezone": "Asia/Shanghai", "forecast_days": forecast_days
                })
                data = weather_resp.json()

                # 3. 解析结果
                weather = settings.WEATHER_CODE_MAP.get(data["current"]["weather_code"], "未知")
                temp = data["current"]["temperature_2m"]
                return f"【{city_name}】实时天气\n天气：{weather}\n温度：{temp}℃"

        except httpx.TimeoutException:
            return "❌ 天气查询失败：国内网络无法访问Open-Meteo API"
        except Exception as e:
            return f"❌ 天气查询失败：{str(e)[:30]}"