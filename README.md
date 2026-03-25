# 豆包本地技能助手

一个基于 MCP (Model Context Protocol) 协议的本地技能助手，支持计算器、天气查询等自定义技能，提供 Web 界面和 API 接口。

## 项目结构

```
d:\agent\
├── .env                    # 大模型api配置
├── index.html              # 前端 Web 界面
├── main.py                 # 主入口（可选）
├── mcp_server.py          # MCP 服务端（核心）
├── server.py               # Flask 后端服务
├── requirements.txt        # 依赖清单
├── README.md               # 项目说明
├── tree.txt                # 目录结构
├── client/                 # 客户端目录
│   ├── doubao_mcp_client.py  # 豆包 API 客户端
│   └── __init__.py
├── config/                 # 配置目录
│   ├── settings.py         # 全局配置
│   └── __init__.py
└── skills/                 # 技能实现目录
    ├── calculator.py       # 计算器技能
    ├── weather.py          # 天气查询技能
    └── __init__.py
```

## 核心组件

1. **前端** (`index.html`) - 基于 HTML/CSS/JavaScript 的 Web 界面
2. **后端** (`server.py`) - Flask 服务，提供 API 接口
3. **MCP 服务** (`mcp_server.py`) - 处理技能调用的核心服务
4. **技能模块** (`skills/`) - 各种自定义技能的实现
5. **配置** (`config/`) - 全局配置和常量

## 环境要求

- Python 3.11+
- 火山引擎豆包 API 密钥（获取 AK/SK）

## 安装

1. **克隆项目**
   ```bash
   git clone https://github.com/taffy123d/Doubao-MCP-agent
   cd <项目目录>
   ```

2. **安装依赖**
   ```bash
   pip install -r requirements.txt
   ```

3. **配置环境变量**
   复制 `.env.example` 为 `.env` 并填写 API 密钥：
   ```env
   # 火山引擎豆包 API 密钥
   DOUBAO_API_KEY=你的API密钥
   DOUBAO_ENDPOINT_ID=你的终端ID
   DOUBAO_BASE_URL=https://ark.cn-beijing.volces.com/api/v3/chat/completions
   ```

## 运行

### 方法一：完整启动（推荐）

```bash
python server.py
```

- 前端访问：`http://localhost:5000`
- API 接口：`http://localhost:5000/api/*`

### 方法二：单独启动

1. **启动 MCP 服务**
   ```bash
   python mcp_server.py
   ```

2. **启动后端服务**
   ```bash
   python server.py
   ```

3. **打开前端**
   直接用浏览器打开 `index.html`

## 如何使用

1. **配置 API**
   - 在左侧配置面板填写 API Key 和 Endpoint ID
   - 点击「测试」按钮验证连接

2. **聊天**
   - 在输入框中输入问题
   - 支持的技能：
     - 计算器：`计算 123+456`
     - 天气查询：`北京天气`

3. **查看结果**
   - 系统会自动调用相应的技能并返回结果
   - 支持多轮对话

## 如何增加新技能

### 步骤 1：创建技能文件

在 `skills/` 目录下创建新的技能文件，例如 `my_skill.py`：

```python
"""我的自定义技能"""
from mcp.server.fastmcp import FastMCP

def register_my_skill(mcp: FastMCP):
    """注册技能到 MCP 服务"""
    
    @mcp.tool()
    def my_skill(param1: str, param2: int = 1) -> str:
        """
        我的自定义技能描述
        示例：my_skill(param1="值", param2=2)
        
        Args:
            param1: 参数1描述
            param2: 参数2描述（默认值）
        Returns:
            技能执行结果
        """
        try:
            # 技能逻辑实现
            result = f"处理结果: {param1} - {param2}"
            return result
        except Exception as e:
            return f"处理失败: {str(e)}"
```

### 步骤 2：注册技能

编辑 `skills/__init__.py`，添加新技能的注册函数：

```python
from .calculator import register_calculator_tool
from .weather import register_weather_tool
from .my_skill import register_my_skill

__all__ = [
    "register_calculator_tool", 
    "register_weather_tool",
    "register_my_skill"
]
```

### 步骤 3：更新 MCP 服务

编辑 `mcp_server.py`，添加新技能的注册：

```python
from skills import register_calculator_tool, register_weather_tool, register_my_skill

# 注册所有技能工具
register_calculator_tool(mcp)
register_weather_tool(mcp)
register_my_skill(mcp)  # 添加这一行
```

### 步骤 4：重启服务

重新启动 MCP 服务和后端服务，新技能即可使用。

## API 接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/` | GET | 前端页面 |
| `/api/health` | GET | 健康检查 |
| `/api/tools` | GET | 获取技能列表 |
| `/api/test-connection` | POST | 测试 API 连接 |
| `/api/chat` | POST | 聊天（调用技能） |
| `/api/chat/stream` | POST | 流式聊天（预留） |

## 技能开发规范

1. **文件命名**：使用小写字母和下划线
2. **函数命名**：`register_xxx_tool` 格式
3. **工具装饰器**：使用 `@mcp.tool()` 装饰
4. **文档字符串**：包含功能描述、示例和参数说明
5. **错误处理**：捕获异常并返回友好提示
6. **参数类型**：使用类型注解

## 示例技能

### 计算器技能
- **功能**：支持加减乘除、括号、幂运算
- **调用**：`计算 (10+5)*2`

### 天气查询技能
- **功能**：查询城市天气和预报
- **调用**：`上海天气` 或 `北京天气 3天`

## 注意事项

1. **API 密钥安全**：不要将 API 密钥提交到版本控制
2. **技能安全性**：避免在技能中执行危险操作
3. **性能优化**：对于耗时操作，考虑使用异步处理
4. **错误处理**：确保技能能优雅处理异常情况

## 故障排除

- **连接失败**：检查 API 密钥和网络连接
- **技能不响应**：检查 MCP 服务是否正常运行
- **前端不显示**：检查浏览器控制台是否有错误

## 扩展建议

1. **更多技能**：添加翻译、股票查询、新闻等技能
2. **多语言支持**：添加多语言界面
3. **部署优化**：使用 Docker 容器化部署

---

