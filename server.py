"""
豆包本地技能助手 - Flask 后端服务
"""
import asyncio
import json
import os
import sqlite3
from collections import defaultdict
from flask import Flask, request, jsonify, send_from_directory, Response, g
from flask_cors import CORS
import httpx
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

app = Flask(__name__)
CORS(app, resources={
    r"/api/*": {
        "origins": "*",
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"]
    }
})

# MCP 服务配置
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
MCP_SERVER = StdioServerParameters(
    command="python",
    args=["-u", os.path.join(ROOT_DIR, "mcp_server.py")],
    cwd=ROOT_DIR
)

# 缓存 MCP 工具列表
_cached_tools = None

# 数据库路径
DB_PATH = os.path.join(ROOT_DIR, "chat_history.db")
MAX_HISTORY = 20


# ====================== MCP 工具管理 ======================
async def get_mcp_tools():
    """获取 MCP 工具列表（缓存）"""
    global _cached_tools
    if _cached_tools is not None:
        return _cached_tools
    
    async with stdio_client(MCP_SERVER) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools_result = await session.list_tools()
            _cached_tools = [
                {
                    "type": "function",
                    "function": {
                        "name": t.name,
                        "description": t.description,
                        "parameters": t.inputSchema
                    }
                }
                for t in tools_result.tools
            ]
            return _cached_tools


async def run_mcp_tool(tool_name: str, arguments: dict, max_retries: int = 2):
    """运行 MCP 工具（带重试和 fallback）"""
    for attempt in range(max_retries):
        try:
            async with stdio_client(MCP_SERVER) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    result = await session.call_tool(name=tool_name, arguments=arguments)
                    return result.content[0].text
        except Exception as e:
            if attempt < max_retries - 1:
                print(f"⚠️ 工具调用失败，重试 {attempt + 1}/{max_retries}: {str(e)}")
                await asyncio.sleep(0.5)
                continue
            else:
                # 最后一次尝试也失败，返回 fallback 提示
                error_msg = f"工具 {tool_name} 调用失败：{str(e)}"
                print(f"⚠️ {error_msg}")
                return f"[工具调用失败] {error_msg}，请直接回答问题"


# ====================== SQLite 数据库 ======================
def get_db():
    """获取数据库连接"""
    if 'db' not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db


def init_db():
    """初始化数据库表"""
    with sqlite3.connect(DB_PATH) as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        db.execute("CREATE INDEX IF NOT EXISTS idx_session ON messages(session_id)")
        db.commit()


def get_history(session_id: str, limit: int = MAX_HISTORY) -> list:
    """获取对话历史"""
    db = get_db()
    rows = db.execute("""
        SELECT role, content FROM messages
        WHERE session_id = ?
        ORDER BY id DESC
        LIMIT ?
    """, (session_id, limit)).fetchall()
    return [{"role": row["role"], "content": row["content"]} for row in reversed(rows)]


def save_message(session_id: str, role: str, content: str):
    """保存消息到数据库"""
    db = get_db()
    db.execute("""
        INSERT INTO messages (session_id, role, content)
        VALUES (?, ?, ?)
    """, (session_id, role, content))
    db.commit()


def trim_history(session_id: str, limit: int = MAX_HISTORY):
    """清理超过限制的历史记录"""
    db = get_db()
    db.execute("""
        DELETE FROM messages WHERE id IN (
            SELECT id FROM messages
            WHERE session_id = ?
            ORDER BY id DESC
            LIMIT -1 OFFSET ?
        )
    """, (session_id, limit))
    db.commit()


def clear_history_db(session_id: str):
    """清空会话历史"""
    db = get_db()
    db.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
    db.commit()


# ====================== 请求关闭时清理 ======================
@app.teardown_appcontext
def close_db(error):
    """关闭数据库连接"""
    db = g.pop('db', None)
    if db is not None:
        db.close()


# ====================== 辅助函数 ======================
def run_in_thread(func, *args, **kwargs):
    """在线程中运行异步函数"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(func(*args, **kwargs))
    finally:
        loop.close()


# ====================== 路由处理 ======================



async def get_mcp_tools():
    """获取 MCP 工具列表"""
    global _cached_tools
    if _cached_tools is not None:
        return _cached_tools
    
    async with stdio_client(MCP_SERVER) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools_result = await session.list_tools()
            _cached_tools = [
                {
                    "type": "function",
                    "function": {
                        "name": t.name,
                        "description": t.description,
                        "parameters": t.inputSchema
                    }
                }
                for t in tools_result.tools
            ]
            return _cached_tools


async def run_mcp_tool(tool_name: str, arguments: dict):
    """运行 MCP 工具"""
    async with stdio_client(MCP_SERVER) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(name=tool_name, arguments=arguments)
            return result.content[0].text


@app.route('/api/health', methods=['GET'])
def health_check():
    """健康检查接口"""
    return jsonify({"status": "ok", "message": "服务正常运行"})


@app.route('/api/config', methods=['GET'])
def get_config():
    """获取配置"""
    config = {}
    if os.path.exists('.env'):
        with open('.env', 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and '=' in line:
                    key, value = line.split('=', 1)
                    config[key.strip()] = value.strip().strip("'").strip('"')
    return jsonify(config)


@app.route('/api/config', methods=['POST'])
def save_config():
    """保存配置到 .env 文件"""
    data = request.json
    try:
        # 读取现有配置
        existing_config = {}
        if os.path.exists('.env'):
            with open('.env', 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and '=' in line:
                        key, value = line.split('=', 1)
                        existing_config[key.strip()] = value.strip()
        
        # 更新配置
        if 'DOUBAO_API_KEY' in data:
            existing_config['DOUBAO_API_KEY'] = f"'{data['DOUBAO_API_KEY']}'"
        if 'DOUBAO_ENDPOINT_ID' in data:
            existing_config['DOUBAO_ENDPOINT_ID'] = f"'{data['DOUBAO_ENDPOINT_ID']}'"
        if 'DOUBAO_BASE_URL' in data:
            existing_config['DOUBAO_BASE_URL'] = f"'{data['DOUBAO_BASE_URL']}'"
        
        # 写入配置文件
        with open('.env', 'w', encoding='utf-8') as f:
            for key, value in existing_config.items():
                f.write(f"{key}={value}\n")
        
        return jsonify({"success": True, "message": "配置保存成功"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


def get_tools_in_thread():
    """在线程中获取工具列表"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(get_mcp_tools())
    finally:
        loop.close()

@app.route('/api/tools', methods=['GET'])
def get_tools():
    """获取可用工具列表"""
    try:
        tools = run_in_thread(get_mcp_tools)
        return jsonify({"tools": tools})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


def test_connection_in_thread(api_key, endpoint_id, base_url):
    """在线程中测试连接"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    async def _test():
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(
                    url=base_url,
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": endpoint_id,
                        "messages": [{"role": "user", "content": "test"}],
                        "temperature": 0.1
                    }
                )
                return resp.status_code == 200
        except Exception:
            return False
    
    try:
        return loop.run_until_complete(_test())
    finally:
        loop.close()

@app.route('/api/test-connection', methods=['POST'])
def test_connection():
    """测试 API 连接"""
    data = request.json
    api_key = data.get('api_key', '')
    endpoint_id = data.get('endpoint_id', '')
    base_url = data.get('base_url', '')
    
    if not api_key or not endpoint_id:
        return jsonify({"connected": False, "error": "缺少 API Key 或 Endpoint ID"})
    
    try:
        is_connected = test_connection_in_thread(api_key, endpoint_id, base_url)
        return jsonify({"connected": is_connected})
    except Exception as e:
        return jsonify({"connected": False, "error": str(e)})


def chat_in_thread(api_key, endpoint_id, base_url, message, history):
    """在线程中执行异步聊天函数"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(
            _chat_async(api_key, endpoint_id, base_url, message, history)
        )
    finally:
        loop.close()

async def _chat_async(api_key, endpoint_id, base_url, user_message, history):
    """异步聊天函数"""
    # 获取 MCP 工具
    tools = await get_mcp_tools()
    
    async with httpx.AsyncClient(timeout=60) as http_client:
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        # 使用历史消息
        messages = history.copy()
        messages.append({"role": "user", "content": user_message})
        
        # 第一次调用豆包 API
        resp = await http_client.post(
            url=base_url,
            headers=headers,
            json={
                "model": endpoint_id,
                "messages": messages,
                "tools": tools,
                "temperature": 0.1
            }
        )
        
        if resp.status_code != 200:
            return {"response": f"API 调用失败: {resp.status_code}", "messages": messages}
        
        result = resp.json()
        msg = result["choices"][0]["message"]
        
        # 检查是否需要调用工具
        if "tool_calls" in msg:
            tool_call = msg["tool_calls"][0]
            tool_name = tool_call["function"]["name"]
            tool_args = json.loads(tool_call["function"]["arguments"])
            
            # 调用 MCP 工具（带 fallback）
            tool_result = await run_mcp_tool(tool_name, tool_args)
            
            # 构建第二次调用的消息
            messages.append(msg)
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call["id"],
                "content": tool_result
            })
            
            # 第二次调用豆包 API（让模型处理工具调用失败的情况）
            final_resp = await http_client.post(
                url=base_url,
                headers=headers,
                json={
                    "model": endpoint_id,
                    "messages": messages,
                    "temperature": 0.1
                }
            )
            
            if final_resp.status_code == 200:
                final_result = final_resp.json()
                final_msg = final_result["choices"][0]["message"]
                messages.append(final_msg)
                response_content = final_msg.get("content") or tool_result
                return {"response": f"【调用了工具：{tool_name}】\n\n{response_content}", "messages": messages}
            else:
                messages.append({"role": "assistant", "content": tool_result})
                return {"response": f"【调用了工具：{tool_name}】\n\n{tool_result}", "messages": messages}
        
        messages.append(msg)
        return {"response": msg.get("content", "无响应内容"), "messages": messages}

@app.route('/api/chat', methods=['POST'])
def chat():
    """聊天接口 - 调用豆包 API 和 MCP 工具"""
    data = request.json
    api_key = data.get('api_key', '')
    endpoint_id = data.get('endpoint_id', '')
    base_url = data.get('base_url', '')
    user_message = data.get('message', '')
    session_id = data.get('session_id', 'default')
    
    if not api_key or not endpoint_id:
        return jsonify({"error": "缺少 API Key 或 Endpoint ID"}), 400
    
    if not user_message:
        return jsonify({"error": "消息内容不能为空"}), 400
    
    # 获取会话历史（从数据库）
    messages_history = get_history(session_id)
    
    try:
        result = chat_in_thread(api_key, endpoint_id, base_url, user_message, messages_history)
        
        # 保存历史到数据库
        if "messages" in result:
            messages = result["messages"]
            # 保存最后 MAX_HISTORY 条
            for msg in messages[-MAX_HISTORY:]:
                save_message(session_id, msg["role"], msg["content"])
            # 清理旧数据
            trim_history(session_id)
        
        return jsonify({"response": result["response"], "session_id": session_id})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/chat/clear', methods=['POST'])
def clear_history():
    """清除对话历史"""
    data = request.json
    session_id = data.get('session_id', 'default')
    
    clear_history_db(session_id)
    
    return jsonify({"success": True, "message": "对话历史已清除"})


async def _stream_generator(api_key, endpoint_id, base_url, message, history):
    """异步流式生成器"""
    async for chunk in _chat_stream_async(api_key, endpoint_id, base_url, message, history):
        yield chunk

def stream_in_thread(api_key, endpoint_id, base_url, message, history):
    """在线程中执行异步流式聊天函数"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        generator = _stream_generator(api_key, endpoint_id, base_url, message, history)
        while True:
            try:
                chunk = loop.run_until_complete(generator.__anext__())
                yield chunk
            except StopAsyncIteration:
                break
    finally:
        loop.close()

async def _chat_stream_async(api_key, endpoint_id, base_url, user_message, history):
    """异步流式聊天函数"""
    # 获取 MCP 工具
    tools = await get_mcp_tools()
    
    # 使用历史消息
    messages = history.copy()
    messages.append({"role": "user", "content": user_message})
    
    async with httpx.AsyncClient(timeout=60) as http_client:
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        # 第一次调用豆包 API
        async with http_client.stream(
            "POST",
            url=base_url,
            headers=headers,
            json={
                "model": endpoint_id,
                "messages": messages,
                "tools": tools,
                "temperature": 0.1,
                "stream": True
            }
        ) as resp:
            if resp.status_code != 200:
                yield f"data: {{\"error\": \"API 调用失败: {resp.status_code}\"}}\n\n"
                return
            
            full_response = ""
            tool_calls = None
            tool_call_id = None
            tool_name = None
            tool_args = None
            
            # 处理流式响应
            async for line in resp.aiter_lines():
                line = line.strip()
                if not line:
                    continue
                
                if line.startswith("data: "):
                    data = line[6:]
                    if data == "[DONE]":
                        break
                    
                    try:
                        chunk = json.loads(data)
                        if "choices" in chunk:
                            choice = chunk["choices"][0]
                            if "delta" in choice:
                                delta = choice["delta"]
                                if "content" in delta:
                                    content = delta["content"]
                                    full_response += content
                                    yield f"data: {{\"response\": \"{content.replace('\\n', '\\\\n')}\"}}\n\n"
                                elif "tool_calls" in delta:
                                    tool_calls = delta["tool_calls"]
                    except json.JSONDecodeError:
                        pass
            
            # 检查是否需要调用工具
            if tool_calls:
                tool_call = tool_calls[0]
                tool_call_id = tool_call["id"]
                tool_name = tool_call["function"]["name"]
                tool_args = json.loads(tool_call["function"]["arguments"])
                
                # 调用 MCP 工具（带 fallback）
                tool_result = await run_mcp_tool(tool_name, tool_args)
                
                # 构建第二次调用的消息
                messages.append({"role": "assistant", "tool_calls": tool_calls})
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call_id,
                    "content": tool_result
                })
                
                # 发送工具调用提示
                yield f"data: {{\"response\": \"【调用了工具：{tool_name}】\\n\\n\"}}\n\n"
                
                # 第二次调用豆包 API
                async with http_client.stream(
                    "POST",
                    url=base_url,
                    headers=headers,
                    json={
                        "model": endpoint_id,
                        "messages": messages,
                        "temperature": 0.1,
                        "stream": True
                    }
                ) as final_resp:
                    if final_resp.status_code != 200:
                        yield f"data: {{\"response\": \"{tool_result.replace('\\n', '\\\\n')}\"}}\n\n"
                        yield "data: [DONE]\n\n"
                        return
                    
                    async for line in final_resp.aiter_lines():
                        line = line.strip()
                        if not line:
                            continue
                        
                        if line.startswith("data: "):
                            data = line[6:]
                            if data == "[DONE]":
                                break
                            
                            try:
                                chunk = json.loads(data)
                                if "choices" in chunk:
                                    choice = chunk["choices"][0]
                                    if "delta" in choice:
                                        delta = choice["delta"]
                                        if "content" in delta:
                                            content = delta["content"]
                                            yield f"data: {{\"response\": \"{content.replace('\\n', '\\\\n')}\"}}\n\n"
                            except json.JSONDecodeError:
                                pass
            
            yield "data: [DONE]\n\n"

@app.route('/api/chat/stream', methods=['POST'])
def chat_stream():
    """流式聊天接口（SSE）"""
    data = request.json
    api_key = data.get('api_key', '')
    endpoint_id = data.get('endpoint_id', '')
    base_url = data.get('base_url', '')
    user_message = data.get('message', '')
    session_id = data.get('session_id', 'default')
    
    if not api_key or not endpoint_id:
        return jsonify({"error": "缺少 API Key 或 Endpoint ID"}), 400
    
    if not user_message:
        return jsonify({"error": "消息内容不能为空"}), 400
    
    # 获取会话历史（从数据库）
    messages_history = get_history(session_id)
    
    def generate():
        # 收集完整消息用于保存历史
        full_user_message = {"role": "user", "content": user_message}
        full_assistant_messages = []
        
        for chunk in stream_in_thread(api_key, endpoint_id, base_url, user_message, messages_history):
            yield chunk
            
            # 尝试解析 chunk 并收集消息
            if chunk.startswith("data: ") and chunk.strip() != "data: [DONE]\n\n":
                try:
                    data_str = chunk[6:].strip()
                    if data_str.startswith("{") and data_str.endswith("}\n\n"):
                        data_obj = json.loads(data_str[:-2])
                        if "response" in data_obj:
                            response = data_obj["response"]
                            if not response.startswith("【"):
                                if not full_assistant_messages:
                                    full_assistant_messages.append({"role": "assistant", "content": response})
                                else:
                                    full_assistant_messages[0]["content"] += response
                except:
                    pass
        
        # 保存历史到数据库
        save_message(session_id, full_user_message["role"], full_user_message["content"])
        for msg in full_assistant_messages:
            save_message(session_id, msg["role"], msg["content"])
        trim_history(session_id)
    
    return Response(generate(), mimetype='text/event-stream')


@app.route('/')
def index():
    """返回前端页面"""
    return send_from_directory('.', 'index.html')


@app.route('/<path:path>')
def static_files(path):
    """返回静态文件"""
    return send_from_directory('.', path)


if __name__ == '__main__':
    print("=" * 50)
    print("豆包本地技能助手 - Flask 后端服务")
    print("=" * 50)
    print("服务地址: http://localhost:5000")
    print("API 文档:")
    print("  GET  /api/health          - 健康检查")
    print("  GET  /api/tools           - 获取工具列表")
    print("  POST /api/test-connection - 测试连接")
    print("  POST /api/chat            - 聊天")
    print("=" * 50)
    
    # 确保 MCP 服务文件存在
    mcp_server_path = os.path.join(ROOT_DIR, "mcp_server.py")
    if not os.path.exists(mcp_server_path):
        print(f"\n警告: 未找到 MCP 服务文件: {mcp_server_path}")
        print("请先创建 mcp_server.py 文件\n")
    
    # 初始化数据库
    init_db()
    print("✅ 数据库已初始化")
    
    app.run(host='0.0.0.0', port=5000, debug=True)
