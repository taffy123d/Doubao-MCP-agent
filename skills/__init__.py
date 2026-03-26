<<<<<<< HEAD
from .calculator import register_calculator_tool
from .weather import register_weather_tool

__all__ = ["register_calculator_tool", "register_weather_tool"]
=======
"""技能模块"""
from .calculator import register_calculator_tool
from .weather import register_weather_tool
from .time_query import register_time_tool

__all__ = [
    "register_calculator_tool",
    "register_weather_tool",
    "register_time_tool"
]
>>>>>>> 4020d96 (✨ 添加时间查询技能和优化文档)
