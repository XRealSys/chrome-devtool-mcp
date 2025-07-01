# AI调试指南 - Chrome DevTools MCP

本指南介绍如何使用Chrome DevTools MCP工具进行非阻塞式调试，适用于Claude Code和Cursor等AI辅助开发工具。

## 核心理念

本工具采用**非阻塞式调试**方式，通过以下技术实现：
- 函数包装和拦截
- 事件监听器注入
- 日志增强输出
- 无需暂停执行即可获取调试信息

## 日志断点（Logpoints）支持

Chrome DevTools MCP 现在支持日志断点 - 这是一种不会暂停程序执行的特殊断点，只会在特定位置输出日志。这对 AI 辅助调试特别有用。

### 日志断点的优势

1. **非阻塞** - 不会中断程序执行流程
2. **条件输出** - 只在满足特定条件时记录
3. **性能友好** - 比传统断点开销更小
4. **易于批量设置** - 可以在多个位置设置而不影响用户体验

### 使用方法

```python
# 设置函数日志断点
await set_breakpoint('function', 'handleLogin', {
    'logMessage': 'User login attempt',
    'pause': False  # 关键：设置为 False 使其成为日志断点
})

# 设置条件日志断点
await set_breakpoint('function', 'validateAge', {
    'logMessage': 'Age validation failed',
    'condition': 'age < 18',
    'pause': False
})

# DOM 事件日志断点
await set_breakpoint('dom', '#submit-button', {
    'logMessage': 'Form submission triggered',
    'pause': False
})
```

## JavaScript 代码分析工具

在设置断点之前，AI 需要理解代码结构。以下工具提供了完整的代码可见性：

### 1. 发现脚本源

```python
# 获取所有加载的脚本
scripts = await get_script_sources()
for script in scripts['data']['scripts']:
    print(f"Script: {script['url']}, ID: {script['scriptId']}")

# 读取特定脚本的源代码
source = await get_script_source(script_id)
print(source['data']['source'])
```

### 2. 搜索代码

```python
# 搜索特定函数
results = await search_in_scripts('handleLogin', 'function')
for match in results['data']['matches']:
    print(f"Found at line {match['lineNumber']}: {match['line']}")

# 搜索错误处理
errors = await search_in_scripts('console.error', 'text')

# 搜索类定义
classes = await search_in_scripts('UserManager', 'class')
```

### 3. 智能断点设置流程

```python
# AI 工作流程示例
async def debug_login_issue():
    # 1. 找到登录按钮的处理函数
    elements = await query_elements('#login-button')
    onclick = elements['data']['elements'][0]['attributes']['onclick']
    
    # 2. 搜索该函数的定义
    func_name = extract_function_name(onclick)  # e.g., "handleLogin"
    search_result = await search_in_scripts(func_name, 'function')
    
    # 3. 读取函数代码以理解调用链
    if search_result['data']['matches']:
        script_id = search_result['data']['matches'][0]['scriptId']
        source = await get_script_source(script_id)
        
        # 4. 分析代码并设置策略性断点
        await set_breakpoint('function', func_name, {
            'logMessage': f'{func_name} called',
            'pause': False
        })
```

## 常用调试模式

### 1. 登录按钮调试示例

当用户问："请在点击登录按钮后，打断点并输出内容到console"

```python
# 步骤1：查找登录按钮
elements = await query_elements('#login-button')
# 或者使用更智能的选择器
elements = await query_elements('button[onclick*="login"]')

# 步骤2：设置非阻塞断点（推荐方式）
await execute_javascript("""
    // 找到登录函数
    const loginFnName = document.querySelector('#login-button').onclick.toString().match(/(\w+)\(/)[1];
    const originalFn = window[loginFnName];
    
    // 包装函数以添加调试输出
    window[loginFnName] = async function(...args) {
        console.log('🔍 DEBUG: Login function called');
        console.log('🔍 DEBUG: Arguments:', args);
        console.log('🔍 DEBUG: Current URL:', window.location.href);
        console.log('🔍 DEBUG: Form data:', {
            username: document.querySelector('input[type="text"]')?.value,
            password: document.querySelector('input[type="password"]')?.value
        });
        
        try {
            const result = await originalFn.apply(this, args);
            console.log('🔍 DEBUG: Function returned:', result);
            return result;
        } catch (error) {
            console.error('🔍 DEBUG: Error occurred:', error);
            throw error;
        }
    }
""")

# 步骤3：触发点击
await execute_javascript("document.querySelector('#login-button').click()")

# 步骤4：获取调试输出
logs = await get_console_logs()
for log in logs['data']['logs'][-20:]:
    if log['text']:
        print(f"[{log['level']}] {log['text']}")
```

### 2. 监控所有点击事件

```python
await execute_javascript("""
    // 全局点击事件监控
    document.addEventListener('click', function(e) {
        const target = e.target;
        console.log('🎯 CLICK:', {
            element: target.tagName,
            id: target.id,
            class: target.className,
            text: target.textContent.trim().substring(0, 50),
            coordinates: {x: e.clientX, y: e.clientY}
        });
    }, true);  // 使用捕获阶段
""")
```

### 3. API调用拦截

```python
await execute_javascript("""
    // 拦截fetch调用
    const originalFetch = window.fetch;
    window.fetch = async function(...args) {
        const [url, options = {}] = args;
        console.log('🌐 API Call:', {
            url: url,
            method: options.method || 'GET',
            headers: options.headers,
            body: options.body
        });
        
        const startTime = performance.now();
        try {
            const response = await originalFetch.apply(this, args);
            const duration = performance.now() - startTime;
            
            // 克隆响应以读取内容
            const clone = response.clone();
            const data = await clone.json().catch(() => null);
            
            console.log('🌐 API Response:', {
                url: url,
                status: response.status,
                duration: duration + 'ms',
                data: data
            });
            
            return response;
        } catch (error) {
            console.error('🌐 API Error:', error);
            throw error;
        }
    }
""")
```

### 4. 表单验证调试

```python
await execute_javascript("""
    // 监控所有表单提交
    document.addEventListener('submit', function(e) {
        const form = e.target;
        const formData = new FormData(form);
        const data = {};
        for (let [key, value] of formData.entries()) {
            data[key] = value;
        }
        
        console.log('📝 Form Submit:', {
            formId: form.id,
            action: form.action,
            method: form.method,
            data: data
        });
    }, true);
    
    // 监控输入变化
    document.addEventListener('input', function(e) {
        if (e.target.tagName === 'INPUT') {
            console.log('⌨️ Input Change:', {
                field: e.target.name || e.target.id,
                value: e.target.value,
                valid: e.target.checkValidity()
            });
        }
    }, true);
""")
```

### 5. 错误边界设置

```python
await execute_javascript("""
    // 全局错误捕获
    window.addEventListener('error', function(e) {
        console.error('❌ Global Error:', {
            message: e.message,
            filename: e.filename,
            line: e.lineno,
            column: e.colno,
            stack: e.error?.stack
        });
    });
    
    // Promise拒绝捕获
    window.addEventListener('unhandledrejection', function(e) {
        console.error('❌ Unhandled Promise:', {
            reason: e.reason,
            promise: e.promise
        });
    });
""")
```

## 完整调试流程示例

```python
async def debug_user_login_flow():
    """完整的用户登录流程调试"""
    
    # 1. 连接到页面
    await navigate_to("https://example.com/login")
    
    # 2. 设置全面的调试环境
    await execute_javascript("""
        // 调试助手
        window.DEBUG = {
            log: function(category, message, data) {
                const timestamp = new Date().toISOString();
                console.log(`[${timestamp}] [${category}] ${message}`, data || '');
            }
        };
        
        // 监控所有网络请求
        const observer = new PerformanceObserver((list) => {
            for (const entry of list.getEntries()) {
                if (entry.initiatorType === 'fetch' || entry.initiatorType === 'xmlhttprequest') {
                    DEBUG.log('NETWORK', 'Request completed', {
                        url: entry.name,
                        duration: entry.duration,
                        size: entry.transferSize
                    });
                }
            }
        });
        observer.observe({ entryTypes: ['resource'] });
        
        console.log('🚀 Debug environment ready');
    """)
    
    # 3. 查找并增强登录功能
    elements = await query_elements('button[type="submit"], #login-btn, .login-button')
    if elements['success'] and elements['data']['elements']:
        print(f"Found {len(elements['data']['elements'])} potential login buttons")
    
    # 4. 填充表单并触发登录
    await execute_javascript("""
        // 填充表单
        document.querySelector('input[name="username"]').value = 'testuser';
        document.querySelector('input[name="password"]').value = 'testpass';
        
        // 触发登录
        document.querySelector('button[type="submit"]').click();
    """)
    
    # 5. 等待并收集日志
    await asyncio.sleep(2)
    
    # 6. 分析结果
    logs = await get_console_logs()
    
    # 分类日志
    debug_logs = []
    error_logs = []
    network_logs = []
    
    for log in logs['data']['logs']:
        if log['text']:
            if 'DEBUG' in log['text'] or '🔍' in log['text']:
                debug_logs.append(log)
            elif log['level'] == 'error':
                error_logs.append(log)
            elif 'NETWORK' in log['text'] or '🌐' in log['text']:
                network_logs.append(log)
    
    return {
        'debug': debug_logs,
        'errors': error_logs,
        'network': network_logs
    }
```

## 最佳实践

### 1. 使用明确的日志标记

```javascript
console.log('🔍 DEBUG:', data);      // 调试信息
console.log('🌐 NETWORK:', data);    // 网络请求
console.log('❌ ERROR:', data);      // 错误信息
console.log('✅ SUCCESS:', data);    // 成功信息
console.log('⚠️ WARNING:', data);    // 警告信息
```

### 2. 结构化日志输出

```javascript
// 不好的做法
console.log('User logged in');

// 好的做法
console.log('🔍 AUTH', {
    event: 'login',
    user: username,
    timestamp: new Date().toISOString(),
    success: true
});
```

### 3. 性能监控

```javascript
const measure = (name, fn) => {
    const start = performance.now();
    const result = fn();
    const duration = performance.now() - start;
    console.log(`⏱️ PERF: ${name} took ${duration.toFixed(2)}ms`);
    return result;
};
```

### 4. 条件调试

```javascript
// 只在开发环境启用调试
if (location.hostname === 'localhost' || location.search.includes('debug=true')) {
    window.DEBUG_MODE = true;
    // 启用所有调试功能
}
```

## 故障排除

### Console日志为空
- 确保已启用Console domain：检查`_connect_websocket`中的domain启用
- 使用`console.clear()`清除旧日志后重试
- 检查页面是否有覆盖console方法

### 断点导致页面卡住
- 避免使用`debugger`语句
- 使用函数包装而非真实断点
- 设置`auto_resume`标志（如需要）

### WebSocket连接失败
- 确认Chrome启动时包含`--remote-debugging-port`
- 检查防火墙设置
- 使用`list_available_targets()`查看可用目标

## 总结

Chrome DevTools MCP为AI辅助开发提供了强大的非阻塞调试能力。通过函数拦截、事件监听和日志增强，可以在不中断程序执行的情况下获取详细的调试信息，非常适合AI工具进行自动化调试和问题诊断。