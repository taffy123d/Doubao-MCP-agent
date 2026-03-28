"""网络搜索技能实现"""
import httpx
from mcp.server.fastmcp import FastMCP

# 免费搜索引擎 API（DuckDuckGo 简化版）
SEARCH_API_URL = "https://api.duckduckgo.com/"

def register_web_search_tool(mcp: FastMCP):
    """注册网络搜索工具到MCP服务"""

    @mcp.tool()
    async def web_search(query: str, num_results: int = 5) -> str:
        """
        在互联网上搜索信息，返回相关搜索结果摘要
        示例：web_search(query="Python最新版本", num_results=3)

        适用场景：
        - 查询实时新闻、最新资讯
        - 搜索技术文档、教程
        - 获取生活常识、百科信息
        - 查找产品信息、价格对比

        不适用场景：
        - 需要精确计算的问题（请使用计算器工具）
        - 查询当前天气（请使用天气工具）

        Args:
            query: 搜索关键词，支持中英文
            num_results: 返回结果数量，范围 1-10，默认 5

        Returns:
            搜索结果摘要，包含标题、摘要和链接
        """
        try:
            # 参数校验
            num_results = max(1, min(num_results, 10))

            # 使用 DuckDuckGo 即时回答 API
            params = {
                "q": query,
                "format": "json",
                "no_html": 1,
                "skip_disambig": 1
            }

            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(SEARCH_API_URL, params=params)
                resp.raise_for_status()
                data = resp.json()

                # 解析搜索结果
                if not data:
                    return f"未找到与「{query}」相关的搜索结果"

                # 构建结果摘要
                results_text = [f"🔍 搜索「{query}」的结果：\n"]

                # 主要答案
                if data.get("Abstract"):
                    results_text.append(f"\n【摘要】\n{data['Abstract'][:300]}")

                if data.get("AbstractURL"):
                    results_text.append(f"\n来源: {data['AbstractURL']}")

                # 相关主题
                if data.get("RelatedTopics"):
                    results_text.append(f"\n【相关结果】\n")
                    count = 0
                    for topic in data["RelatedTopics"][:num_results]:
                        if isinstance(topic, dict) and "Text" in topic:
                            results_text.append(f"\n{count + 1}. {topic['Text'][:200]}")
                            if "FirstURL" in topic:
                                results_text.append(f"   {topic['FirstURL']}")
                            count += 1
                        if count >= num_results:
                            break

                return "\n".join(results_text)

        except httpx.TimeoutException:
            return "❌ 搜索超时，请稍后重试"
        except httpx.HTTPStatusError as e:
            return f"❌ 搜索服务暂时不可用 (HTTP {e.response.status_code})"
        except Exception as e:
            return f"❌ 搜索失败: {str(e)[:100]}"
