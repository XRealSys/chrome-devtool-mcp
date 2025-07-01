# Chrome DevTools MCP Server

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

一个基于 Model Context Protocol (MCP) 的 Chrome DevTools 控制服务器，为 AI 辅助前端开发提供强大的浏览器调试能力。

## 功能特性

本项目提供了一套完整的 Chrome 浏览器控制工具，让 AI 能够：

- 🚀 **启动和控制 Chrome 浏览器** - 自动启动开发环境的 Chrome 实例
- 🔗 **远程连接 CDP** - 连接到已运行的 Chrome、Electron 或其他 V8 内核程序
- 🔍 **DOM 查询和分析** - 获取页面 DOM 树结构，查询特定元素
- 🌐 **网络请求监控** - 实时捕获和分析所有网络请求和响应
- 📝 **Console 日志捕获** - 获取所有控制台输出，包括错误、警告和日志
- 💻 **JavaScript 执行** - 在页面上下文中执行任意 JavaScript 代码
- 🎯 **页面导航** - 控制浏览器导航到指定 URL
- 📸 **截图功能** - 捕获当前页面的截图
- ℹ️ **页面信息获取** - 获取页面标题、URL、元数据等信息
- 🐛 **JavaScript 断点调试** - 设置各种类型的断点，支持条件断点
- 🎮 **调试控制** - 暂停、继续、单步执行等调试操作

## 第一部分：开发、安装和启动

### 环境要求

- Python 3.7+
- Google Chrome 浏览器
- macOS/Linux/Windows

### 安装步骤

1. 克隆项目：
```bash
git clone https://github.com/yourusername/chrome-devtool-mcp.git
cd chrome-devtool-mcp
```

2. 创建虚拟环境（推荐）：
```bash
python -m venv venv
source venv/bin/activate  # macOS/Linux
# 或
venv\Scripts\activate  # Windows
```

3. 安装依赖：
```bash
pip install -r requirements.txt
```

### 启动服务器

使用以下命令启动服务器：

```bash
python src/chrome_devtools_mcp.py
```

或使用启动脚本：

```bash
./start.sh
```

服务器将在 `http://localhost:12524` 启动。

### 自定义端口

如果需要使用其他端口，修改脚本中的端口号或设置环境变量：

```bash
MCP_PORT=8080 python src/chrome_devtools_mcp.py
```

## 第二部分：Claude Code 接入指南

### 方法一：使用 MCP 配置文件

1. 创建或编辑 Claude Code 的 MCP 配置文件：

macOS/Linux:
```bash
mkdir -p ~/.config/claude/mcp
nano ~/.config/claude/mcp/chrome-devtools.json
```

Windows:
```powershell
mkdir -p $env:APPDATA\claude\mcp
notepad $env:APPDATA\claude\mcp\chrome-devtools.json
```

2. 添加以下配置：

```json
{
  "mcpServers": {
    "chrome-devtools": {
      "command": "python",
      "args": ["/path/to/chrome-devtool-mcp/mcp_server.py"],
      "env": {}
    }
  }
}
```

3. 重启 Claude Code 以加载配置。

### 方法二：在已接入 agent 的情况下启动

如果你已经有其他 MCP 服务器在运行，可以通过以下方式添加 Chrome DevTools 服务器：

1. 修改现有的 MCP 配置文件，添加 chrome-devtools 配置：

```json
{
  "mcpServers": {
    "existing-server": {
      // ... 现有配置
    },
    "chrome-devtools": {
      "command": "python",
      "args": ["/path/to/chrome-devtool-mcp/mcp_server.py"],
      "env": {}
    }
  }
}
```

2. 或者使用环境变量方式：

```bash
export CLAUDE_MCP_CHROME_DEVTOOLS="python /path/to/chrome-devtool-mcp/mcp_server.py"
claude-code
```

### 验证接入

在 Claude Code 中，你可以通过以下方式验证工具是否成功接入：

```
请列出所有可用的 MCP 工具
```

你应该能看到以下工具：
- launch_chrome
- connect_remote_chrome
- connect_websocket_url
- list_available_targets
- navigate_to
- get_dom_tree
- query_elements
- get_network_logs
- get_console_logs
- execute_javascript
- take_screenshot
- get_page_info
- get_script_sources
- get_script_source
- search_in_scripts
- get_page_functions
- set_breakpoint
- list_breakpoints
- remove_breakpoint
- get_paused_info
- resume_execution
- step_over
- close_chrome

## 第三部分：Cursor 接入指南

### 方法一：通过配置文件接入（推荐）

1. 首先确保 MCP 服务器已启动：
   ```bash
   python simple_mcp_server.py
   # 服务器运行在 http://localhost:12524
   ```

2. 打开 Cursor 设置（`Cmd+,` 或 `Ctrl+,`）

3. 搜索 "Model Context Protocol" 或 "MCP"

4. 在 MCP 配置中添加：
   ```json
   {
     "mcpServers": {
       "chrome-devtools": {
         "command": "python3",
         "args": ["/path/to/chrome-devtool-mcp/src/chrome_devtools_mcp.py"]
       }
     }
   }
   ```

5. 重启 Cursor 以加载 MCP 工具

### 方法二：使用环境变量配置

如果需要自定义端口或主机：

1. 设置环境变量并启动服务器：
   ```bash
   MCP_PORT=8080 MCP_HOST=127.0.0.1 python src/chrome_devtools_mcp.py
   ```

2. 在 Cursor 配置中使用相应的端口：
   ```json
   {
     "mcpServers": {
       "chrome-devtools": {
         "command": "python3",
         "args": ["/path/to/chrome-devtool-mcp/src/chrome_devtools_mcp.py"],
         "env": {
           "MCP_PORT": "8080",
           "MCP_HOST": "127.0.0.1"
         }
       }
     }
   }
   ```

### 验证连接

连接成功后，你可以在 Cursor 中：

1. 使用 `@` 符号查看可用的 MCP 工具
2. 或者询问 "列出所有可用的 Chrome DevTools 工具"

你应该能看到以下工具：
- launch_chrome
- connect_remote_chrome
- connect_websocket_url
- list_available_targets
- navigate_to
- get_dom_tree
- query_elements
- get_network_logs
- get_console_logs
- execute_javascript
- take_screenshot
- get_page_info
- get_script_sources
- get_script_source
- search_in_scripts
- get_page_functions
- set_breakpoint
- list_breakpoints
- remove_breakpoint
- get_paused_info
- resume_execution
- step_over
- close_chrome

### 故障排除

如果无法连接：

1. 确保服务器正在运行：
   ```bash
   curl http://localhost:12524/health
   ```

2. 检查防火墙设置，确保端口 12524 可访问

3. 查看服务器日志了解详细错误信息

4. 尝试在浏览器中访问 `http://localhost:12524/docs` 查看 API 文档

## 使用示例

### 基础使用流程

1. **启动 Chrome**：
```
使用 launch_chrome 工具启动一个 Chrome 浏览器实例
```

2. **导航到目标页面**：
```
使用 navigate_to 工具访问 http://localhost:3000
```

3. **检查页面结构**：
```
使用 get_dom_tree 工具获取页面的 DOM 结构
```

4. **查询特定元素**：
```
使用 query_elements 工具查找所有 class 为 "button" 的元素
```

5. **监控网络请求**：
```
使用 get_network_logs 工具查看所有 API 请求
```

6. **执行 JavaScript**：
```
使用 execute_javascript 工具在页面上执行 console.log('Hello from AI!')
```

### 高级调试场景

#### 场景1：调试 React 应用的状态

```
1. 启动 Chrome 并导航到 React 应用
2. 使用 execute_javascript 执行：
   window.__REACT_DEVTOOLS_GLOBAL_HOOK__.renderers.values().next().value.findFiberByHostInstance(document.querySelector('#root'))._debugOwner.stateNode.state
3. 分析返回的状态数据
```

#### 场景2：监控和分析 API 调用

```
1. 清空网络日志
2. 触发应用中的某个操作
3. 使用 get_network_logs 筛选特定 API 端点
4. 分析请求和响应数据
```

#### 场景3：性能分析

```
1. 使用 execute_javascript 执行 performance.mark('start')
2. 执行一系列操作
3. 使用 execute_javascript 执行 performance.mark('end') 和 performance.measure('operation', 'start', 'end')
4. 获取性能数据
```

#### 场景4：调试登录按钮点击事件

```
1. 使用 connect_remote_chrome 连接到已运行的应用
2. 使用 query_elements 找到登录按钮选择器（如 '#login-btn'）
3. 使用 set_breakpoint('dom', '#login-btn') 在登录按钮上设置断点
4. 点击登录按钮，调试器会暂停
5. 使用 get_console_logs 查看控制台输出
6. 使用 get_paused_info 查看暂停位置和调用栈
7. 使用 resume_execution 继续执行
```

#### 场景5：调试远程 Electron 应用

```
1. 启动 Electron 应用时添加 --remote-debugging-port=9222 参数
2. 使用 connect_remote_chrome('localhost', 9222) 连接
3. 使用各种调试工具进行分析
4. 设置断点并调试特定功能
```

#### 场景6：在多个标签页之间切换

```
1. 使用 list_available_targets() 列出所有可用的标签页
2. 选择目标标签页的 webSocketDebuggerUrl
3. 使用 connect_websocket_url(ws_url) 切换到该标签页
4. 现在所有操作都会在新的标签页上执行
```

示例代码：
```
# 列出所有标签页
targets = list_available_targets()
# 选择第二个标签页
ws_url = targets['data']['targets'][1]['webSocketDebuggerUrl']
# 切换到该标签页
connect_websocket_url(ws_url)
```

## API 工具详细说明

### launch_chrome
启动 Chrome 浏览器实例，支持 headless 模式。

参数：
- `headless` (bool): 是否无头模式运行，默认 false
- `port` (int): 远程调试端口，默认 9222

### connect_remote_chrome
连接到远程 Chrome/Chromium 实例（如 Electron 应用）。

参数：
- `host` (str): 远程主机地址，默认 localhost
- `port` (int): 远程调试端口，默认 9222

### connect_websocket_url
直接使用 WebSocket URL 连接到特定的调试会话。

参数：
- `ws_url` (str): WebSocket 调试器 URL，如 'ws://localhost:9222/devtools/page/ABC123'

使用场景：
- 切换不同的标签页/页面
- 连接到特定的调试会话
- 从其他工具获取的 WebSocket URL

### list_available_targets
列出所有可用的 Chrome 标签页/页面及其 WebSocket URL。

参数：
- `host` (str): Chrome 主机地址，默认 localhost
- `port` (int): Chrome 调试端口，默认 9222

### navigate_to
导航到指定 URL。

参数：
- `url` (str): 目标 URL

### get_dom_tree
获取当前页面的 DOM 树结构。

参数：
- `depth` (int): DOM 树的最大深度，默认 3

### query_elements
使用 CSS 选择器查询 DOM 元素。

参数：
- `selector` (str): CSS 选择器

### get_network_logs
获取网络请求日志。

参数：
- `filter_url` (str, optional): URL 过滤模式

### get_console_logs
获取控制台日志。

参数：
- `level` (str, optional): 日志级别过滤（error, warning, log, info）

### execute_javascript
在页面上下文中执行 JavaScript 代码。

参数：
- `code` (str): 要执行的 JavaScript 代码

### take_screenshot
截取当前页面的屏幕截图。

参数：
- `full_page` (bool): 是否截取整个页面，默认 false

### get_page_info
获取当前页面的基本信息。

无参数。

### close_chrome
关闭 Chrome 浏览器实例。

无参数。

### set_breakpoint
设置 JavaScript 断点。支持传统断点和日志断点（logpoint）。

参数：
- `breakpoint_type` (str): 断点类型 - 'dom', 'event', 'function', 'xhr', 'line', 'logpoint'
- `target` (str): 断点目标（如 DOM 选择器、函数名、URL:行号）
- `options` (dict, optional): 额外选项
  - `condition`: 条件表达式，只在条件为真时触发
  - `logMessage`: 日志消息（用于日志断点）
  - `pause`: 是否暂停执行（默认：logpoint 为 False，其他为 True）

示例：
- DOM 断点：`set_breakpoint('dom', '#login-button')`
- 函数断点：`set_breakpoint('function', 'handleLogin')`
- 行断点：`set_breakpoint('line', 'app.js:42')`
- XHR 断点：`set_breakpoint('xhr', '/api/login')`
- 日志断点：`set_breakpoint('function', 'processData', {'logMessage': 'Processing data...', 'pause': False})`
- 条件日志断点：`set_breakpoint('function', 'validate', {'condition': 'value < 0', 'logMessage': 'Invalid value', 'pause': False})`

### list_breakpoints
列出所有活动断点。

无参数。

### remove_breakpoint
移除指定断点。

参数：
- `breakpoint_id` (str): 断点 ID

### get_paused_info
获取调试器暂停时的信息。

无参数。

### resume_execution
从断点恢复执行。

无参数。

### step_over
单步跳过当前行。

无参数。

### get_script_sources
获取当前页面加载的所有 JavaScript 源代码列表。

无参数。

返回：
- scripts: 脚本列表，包含 scriptId、url、startLine、endLine
- count: 脚本总数

### get_script_source
获取特定脚本的源代码。

参数：
- `script_id` (str): 脚本 ID（从 get_script_sources 获取）

### search_in_scripts
在所有加载的脚本中搜索函数、类或文本。

参数：
- `pattern` (str): 搜索模式（如函数名、类名、文本）
- `search_type` (str): 搜索类型 - 'function'、'class'、'variable'、'text'

### get_page_functions
获取页面中定义的所有函数。

无参数。

## 故障排除

### Chrome 无法启动

1. 确保 Chrome 已安装
2. 检查端口 9222 是否被占用：
   ```bash
   lsof -i :9222  # macOS/Linux
   netstat -an | findstr 9222  # Windows
   ```

### WebSocket 连接失败

1. 确保 Chrome 以调试模式启动
2. 检查防火墙设置
3. 尝试使用不同的端口

### MCP 工具无法识别

1. 确保 MCP 服务器正在运行
2. 检查配置文件路径是否正确
3. 重启 Claude Code 或 Cursor

## 贡献指南

欢迎提交 Issue 和 Pull Request！

## 许可证

本项目采用 [MIT 许可证](LICENSE) 开源。

MIT License - 详细信息请查看 [LICENSE](LICENSE) 文件。

该许可证允许您：
- ✅ 商业使用
- ✅ 修改
- ✅ 分发
- ✅ 私人使用

只要您：
- 📄 包含版权声明和许可证声明
- 📝 说明所做的更改（如有修改）

## 相关链接

- [Chrome DevTools Protocol](https://chromedevtools.github.io/devtools-protocol/)
- [Model Context Protocol](https://github.com/anthropics/mcp)
- [FastMCP](https://github.com/anthropics/fastmcp)