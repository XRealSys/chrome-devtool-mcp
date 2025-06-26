# Chrome DevTools MCP Project Structure

```
chrome-devtool-mcp/
├── src/                      # 核心源代码
│   ├── __init__.py          # 包初始化文件
│   └── chrome_devtools_mcp.py  # MCP服务器主程序
│
├── tests/                    # 测试代码
│   ├── __init__.py          # 测试包初始化
│   ├── test_mcp_tools.py    # 完整的功能测试套件
│   └── test_baidu.py        # 百度网站测试示例
│
├── README.md                 # 项目文档
├── PROJECT_STRUCTURE.md      # 项目结构说明（本文件）
├── requirements.txt          # Python依赖
├── pyproject.toml           # 项目配置文件
├── start.sh                 # 启动脚本
├── run_tests.sh             # 测试运行脚本
└── .gitignore               # Git忽略文件配置
```

## 目录说明

### src/
核心代码目录，包含MCP服务器的实现：
- `chrome_devtools_mcp.py` - 实现了所有Chrome控制功能的MCP服务器

### tests/
测试目录，包含各种测试用例：
- `test_mcp_tools.py` - 测试所有MCP工具功能
- `test_baidu.py` - 实际网站测试示例

## 主要功能模块

1. **Chrome控制模块** (`ChromeInstance`)
   - Chrome浏览器启动和管理
   - WebSocket连接管理
   - Chrome DevTools Protocol通信

2. **MCP工具** (10个工具)
   - `launch_chrome` - 启动Chrome浏览器
   - `navigate_to` - 导航到URL
   - `get_dom_tree` - 获取DOM树
   - `query_elements` - 查询DOM元素
   - `get_network_logs` - 获取网络日志
   - `get_console_logs` - 获取控制台日志
   - `execute_javascript` - 执行JavaScript
   - `take_screenshot` - 截图
   - `get_page_info` - 获取页面信息
   - `close_chrome` - 关闭浏览器

3. **服务器端点**
   - `/health` - 健康检查
   - `/sse` - SSE连接端点
   - `/messages/` - 消息处理端点