"""时间查询技能"""
from datetime import datetime
import pytz
from mcp.server.fastmcp import FastMCP

def register_time_tool(mcp: FastMCP):
    """注册时间查询工具"""
    
    @mcp.tool()
    def get_current_time(timezone: str = "Asia/Shanghai") -> str:
        """
        获取当前时间和时区信息
        
        Args:
            timezone: 时区名称，默认 Asia/Shanghai
                     支持: Asia/Shanghai, Asia/Tokyo, America/New_York, Europe/London, UTC
        
        Returns:
            当前时间字符串
        """
        try:
            tz = pytz.timezone(timezone)
            now = datetime.now(tz)
            return f"【{timezone}】当前时间：{now.strftime('%Y-%m-%d %H:%M:%S %Z')}"
        except pytz.exceptions.UnknownTimeZoneError:
            return f"❌ 不支持的时区：{timezone}\n支持的时区：Asia/Shanghai, Asia/Tokyo, America/New_York, Europe/London, UTC"
        except Exception as e:
            return f"❌ 获取时间失败：{str(e)}"
    
    @mcp.tool()
    def get_time_diff(city1: str, city2: str) -> str:
        """
        计算两个城市时区的时间差
        
        Args:
            city1: 第一个城市（中文或英文）
            city2: 第二个城市
        
        Returns:
            时间差信息
        """
        tz_map = {
            "北京": "Asia/Shanghai", "上海": "Asia/Shanghai",
            "东京": "Asia/Tokyo", "日本": "Asia/Tokyo",
            "纽约": "America/New_York", "洛杉矶": "America/Los_Angeles",
            "伦敦": "Europe/London", "巴黎": "Europe/Paris"
        }
        
        try:
            tz1 = pytz.timezone(tz_map.get(city1, city1))
            tz2 = pytz.timezone(tz_map.get(city2, city2))
            
            now1 = datetime.now(tz1)
            now2 = datetime.now(tz2)
            
            diff = now1.utcoffset() - now2.utcoffset()
            hours = diff.total_seconds() / 3600
            
            return f"{city1} vs {city2}：时差 {hours:+.1f} 小时"
        except Exception as e:
            return f"❌ 计算失败：{str(e)}"
