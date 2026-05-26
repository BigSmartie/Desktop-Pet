from langchain_core.tools import tool

from config import settings
from core.logger import get_logger

logger = get_logger(__name__)


WEATHER_CODE_MAP = {
    0: "晴",
    1: "大致晴朗",
    2: "局部多云",
    3: "阴",
    45: "雾",
    48: "凝霜雾",
    51: "小毛毛雨",
    53: "中等毛毛雨",
    55: "强毛毛雨",
    56: "冻毛毛雨",
    57: "强冻毛毛雨",
    61: "小雨",
    63: "中雨",
    65: "大雨",
    66: "冻雨",
    67: "强冻雨",
    71: "小雪",
    73: "中雪",
    75: "大雪",
    77: "雪粒",
    80: "小阵雨",
    81: "中阵雨",
    82: "强阵雨",
    85: "小阵雪",
    86: "强阵雪",
    95: "雷暴",
    96: "伴小冰雹雷暴",
    99: "伴大冰雹雷暴",
}


DISTRICT_SUFFIXES = [
    "区", "县", "市", "旗", "新区", "自治县", "自治州"
]


def _weather_code_to_text(code: int) -> str:
    return WEATHER_CODE_MAP.get(code, f"未知天气代码({code})")


def _safe_get(lst, idx, default="未知"):
    try:
        return lst[idx]
    except Exception:
        return default


def _normalize_location(text: str) -> str:
    """
    轻量清洗地点文本。
    """
    if not text:
        return ""

    text = text.strip()
    for junk in ["今天天气", "明天天气", "后天天气", "天气情况", "天气", "气温", "温度", "降水", "风力"]:
        text = text.replace(junk, "")
    return text.strip(" ，,。？?！!；;")


def _build_location_candidates(location: str) -> list:
    """
    构造地点候选，优先尝试原始地点，失败时逐级回退。
    例如：
    长春市南关区 -> ["长春市南关区", "长春市", "长春"]
    """
    location = _normalize_location(location)
    candidates = []

    if not location:
        return candidates

    # 原始
    candidates.append(location)

    # 自动加市 (如果是典型的城市简称)
    has_suffix = any(s in location for s in DISTRICT_SUFFIXES)
    if not has_suffix and len(location) >= 2:
        candidates.insert(0, location + "市")

    # 如果含“市”且后面还有更细粒度，回退到“xxx市”
    if "市" in location:
        city_part = location.split("市")[0] + "市"
        if city_part not in candidates:
            candidates.append(city_part)

        city_short = city_part.replace("市", "")
        if city_short and city_short not in candidates:
            candidates.append(city_short)

    # 如果没有“市”，尝试去掉区县后缀
    for suffix in DISTRICT_SUFFIXES:
        if location.endswith(suffix):
            short = location[: -len(suffix)].strip()
            if short and short not in candidates:
                candidates.append(short)

    # 去重保序
    final_candidates = []
    seen = set()
    for item in candidates:
        if item and item not in seen:
            final_candidates.append(item)
            seen.add(item)

    return final_candidates


def _search_location_once(requests, query: str):
    """
    使用 Open-Meteo 地理编码 API 查地点。
    """
    geo_url = "https://geocoding-api.open-meteo.com/v1/search"
    resp = requests.get(
        geo_url,
        params={
            "name": query,
            "count": 5,
            "language": "zh",
            "format": "json",
        },
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()
    return data.get("results") or []


def _pick_best_result(results: list, original_query: str):
    """
    尝试从 geocoding 结果里挑更合适的一项。
    优先：
    1. 名称完全相同 (去除市、县等后缀后)
    2. 如果有多个同名，优先取 population(人口) 最大的，或者 admin 层级更接近的（通常中国市级行政区匹配精度更高）
    3. 否则取第一项
    """
    if not results:
        return None

    original_query = (original_query or "").strip().replace("市", "").replace("区", "").replace("县", "")

    # 按人口规模倒序排列（如果有 population 字段），这样大城市优先
    sorted_results = sorted(results, key=lambda x: x.get("population", 0), reverse=True)

    # 1. 寻找完全精准同名的
    for item in sorted_results:
        name = item.get("name", "").replace("市", "").replace("区", "").replace("县", "")
        if name == original_query:
            return item

    # 2. 如果没有完全同名，那么找名字或 admin 区域中包含的
    for item in sorted_results:
        name = item.get("name", "")
        admin1 = item.get("admin1", "")
        admin2 = item.get("admin2", "")
        admin3 = item.get("admin3", "")
        merged = " ".join([name, admin1, admin2, admin3])

        if original_query and original_query in merged.replace("市", "").replace("区", ""):
            return item

    return sorted_results[0]


def _resolve_location(requests, location: str):
    """
    解析地点。
    返回：
    {
        "status": "success"/"not_found",
        "used_query": "...",
        "fallback_used": bool,
        "resolved_name": "...",
        "latitude": ...,
        "longitude": ...,
        "timezone": "...",
        "admin_text": "...",
    }
    """
    candidates = _build_location_candidates(location)

    if not candidates:
        return {"status": "not_found"}

    original = candidates[0]

    for i, query in enumerate(candidates):
        try:
            results = _search_location_once(requests, query)
            if not results:
                continue

            best = _pick_best_result(results, original_query=original)
            if not best:
                continue

            name = best.get("name", query)
            country = best.get("country", "")
            admin1 = best.get("admin1", "")
            admin2 = best.get("admin2", "")
            admin3 = best.get("admin3", "")

            admin_text = " / ".join([x for x in [name, admin3, admin2, admin1, country] if x])

            return {
                "status": "success",
                "used_query": query,
                "fallback_used": i > 0,
                "resolved_name": name,
                "latitude": best.get("latitude"),
                "longitude": best.get("longitude"),
                "timezone": best.get("timezone", "auto"),
                "admin_text": admin_text,
            }

        except Exception:
            logger.exception("地点解析失败 | query=%s", query)

    return {"status": "not_found"}


def _fetch_weather(requests, latitude, longitude, timezone: str):
    """
    拉取天气预报。
    """
    forecast_url = "https://api.open-meteo.com/v1/forecast"
    resp = requests.get(
        forecast_url,
        params={
            "latitude": latitude,
            "longitude": longitude,
            "timezone": timezone or "auto",
            "current": [
                "temperature_2m",
                "relative_humidity_2m",
                "wind_speed_10m",
                "weather_code",
            ],
            "daily": [
                "weather_code",
                "temperature_2m_max",
                "temperature_2m_min",
                "precipitation_probability_max",
            ],
            "forecast_days": 3,
        },
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()


def _format_weather_result(location_input: str, resolved: dict, forecast: dict) -> str:
    current = forecast.get("current", {})
    daily = forecast.get("daily", {})

    current_temp = current.get("temperature_2m", "未知")
    current_humidity = current.get("relative_humidity_2m", "未知")
    current_wind = current.get("wind_speed_10m", "未知")
    current_code = current.get("weather_code", None)

    daily_time = daily.get("time", [])
    daily_code = daily.get("weather_code", [])
    daily_max = daily.get("temperature_2m_max", [])
    daily_min = daily.get("temperature_2m_min", [])
    daily_precip = daily.get("precipitation_probability_max", [])

    lines = []

    if resolved.get("fallback_used"):
        lines.append(
            f"未能精确定位到“{location_input}”的更细粒度天气，当前已回退为较接近地点：{resolved.get('admin_text', '未知地点')}"
        )
    else:
        lines.append(f"地点：{resolved.get('admin_text', '未知地点')}")

    lines.append("")
    lines.append("当前天气：")
    lines.append(f"- 天气状况：{_weather_code_to_text(current_code) if current_code is not None else '未知'}")
    lines.append(f"- 当前气温：{current_temp}°C")
    lines.append(f"- 湿度：{current_humidity}%")
    lines.append(f"- 风速：{current_wind} km/h")

    if daily_time:
        lines.append("")
        lines.append("未来几天预报：")

        for i in range(min(3, len(daily_time))):
            day_text = daily_time[i]
            if i == 0:
                day_label = f"{day_text}（今天）"
            elif i == 1:
                day_label = f"{day_text}（明天）"
            elif i == 2:
                day_label = f"{day_text}（后天）"
            else:
                day_label = day_text

            lines.append(
                f"- {day_label}："
                f"{_weather_code_to_text(_safe_get(daily_code, i, None)) if _safe_get(daily_code, i, None) is not None else '未知'}，"
                f"{_safe_get(daily_min, i)}°C 到 {_safe_get(daily_max, i)}°C，"
                f"降水概率 {_safe_get(daily_precip, i)}%"
            )

    # 简单建议
    lines.append("")
    try:
        current_temp_num = float(current_temp)
        humidity_num = float(current_humidity)

        tips = []
        if current_temp_num <= 5:
            tips.append("气温偏低，注意保暖")
        elif current_temp_num >= 28:
            tips.append("气温较高，注意补水防晒")

        if humidity_num <= 25:
            tips.append("空气较干燥，可适当补水")
        if float(current_wind) >= 20:
            tips.append("风较大，外出注意防风")

        if not tips:
            tips.append("天气整体较平稳，可按正常安排出行")

        lines.append("建议：")
        lines.append(f"- {'；'.join(tips)}")

    except Exception:
        pass

    return "\n".join(lines)


def build_weather_tool():
    @tool
    def get_weather(location: str) -> str:
        """
        查询指定地点天气。
        支持城市、区县等输入；如果无法精确解析到区级，会自动回退到市级并明确说明。
        """
        try:
            if not settings.ENABLE_WEATHER_TOOL:
                return "天气工具当前已禁用。"

            if not location or not location.strip():
                return "天气查询失败：location 不能为空。"

            try:
                import requests
            except ImportError:
                return "天气工具不可用：缺少 requests 依赖，请先安装 requests。"

            normalized_location = _normalize_location(location)
            logger.info("调用天气工具 | location=%s", normalized_location)

            resolved = _resolve_location(requests, normalized_location)
            if resolved.get("status") != "success":
                return f"未找到地点：{location}"

            forecast = _fetch_weather(
                requests=requests,
                latitude=resolved["latitude"],
                longitude=resolved["longitude"],
                timezone=resolved["timezone"],
            )

            result = _format_weather_result(
                location_input=location,
                resolved=resolved,
                forecast=forecast,
            )

            logger.info(
                "天气工具执行成功 | input=%s | used_query=%s | fallback=%s",
                location,
                resolved.get("used_query"),
                resolved.get("fallback_used"),
            )
            return result

        except Exception as e:
            logger.exception("天气工具调用失败")
            return f"天气查询失败：{e}"

    return get_weather