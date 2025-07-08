from openai import OpenAI
import json
import re
import time

class Agent:
    def __init__(self, api_key, base_url="https://api.deepseek.com", max_steps=5, model="deepseek-chat"):
        self.client = OpenAI(
            api_key=api_key,
            base_url=base_url,
        )
        self.model = model
        self.max_steps = max_steps
        self.tools = {}  # 工具名称 -> 函数实现
        self.tool_specs = []  # OpenAI 格式的工具描述
        
    def register_tool(self, tool_name, description, parameters, tool_function):
        """
        注册工具到 Agent
        :param tool_name: 工具名称 (e.g. "get_weather")
        :param description: 工具描述
        :param parameters: 参数规范 (OpenAI 格式)
        :param tool_function: 实际执行的函数
        """
        self.tools[tool_name] = tool_function
        self.tool_specs.append({
            "type": "function",
            "function": {
                "name": tool_name,
                "description": description,
                "parameters": parameters
            }
        })
    
    def execute_tool(self, tool_name, arguments):
        """执行工具并处理错误"""
        try:
            # 尝试解析 JSON 参数
            if isinstance(arguments, str):
                arguments = json.loads(arguments)
                
            # 检查工具是否存在
            if tool_name not in self.tools:
                return f"错误: 未知工具 '{tool_name}'"
                
            # 执行工具
            return self.tools[tool_name](**arguments)
            
        except json.JSONDecodeError:
            # 处理非 JSON 格式参数
            try:
                # 尝试从字符串中提取参数
                params = {}
                for param in self.get_required_params(tool_name):
                    # 简单模式匹配提取参数值
                    match = re.search(fr'{param}[:=]\s*([^,}}]+)', arguments)
                    if match:
                        params[param] = match.group(1).strip('"\' ')
                
                return self.tools[tool_name](**params)
            except Exception as e:
                return f"参数解析错误: {str(e)}"
                
        except Exception as e:
            return f"工具执行错误: {str(e)}"
    
    def get_required_params(self, tool_name):
        """获取工具的必需参数列表"""
        for spec in self.tool_specs:
            if spec["function"]["name"] == tool_name:
                return spec["function"]["parameters"].get("required", [])
        return []
    
    def run(self, user_input, verbose=True):
        """运行 Agent 处理用户查询"""
        messages = [{"role": "user", "content": user_input}]
        
        if verbose:
            print(f"\n[用户] {user_input}")
        
        for step in range(self.max_steps):
            try:
                # 调用 LLM
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    tools=self.tool_specs if self.tool_specs else None,
                    tool_choice="auto" if self.tool_specs else None,
                    temperature=0.3
                )
                
                message = response.choices[0].message
                messages.append(message.to_dict())
                
                # 检查是否调用了工具
                if not message.tool_calls:
                    if verbose:
                        print(f"[Agent] {message.content}")
                    return message.content
                
                # 处理所有工具调用
                for tool_call in message.tool_calls:
                    tool_name = tool_call.function.name
                    arguments = tool_call.function.arguments
                    
                    if verbose:
                        print(f"[工具调用] {tool_name}({arguments})")
                    
                    # 执行工具
                    tool_result = self.execute_tool(tool_name, arguments)
                    
                    if verbose:
                        print(f"[工具结果] {tool_result}")
                    
                    # 添加工具结果到消息历史
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "name": tool_name,
                        "content": str(tool_result)
                    })
            
            except Exception as e:
                error_msg = f"API错误: {str(e)}"
                if verbose:
                    print(f"[错误] {error_msg}")
                messages.append({
                    "role": "system",
                    "content": error_msg
                })
            
            # 避免请求过速
            time.sleep(0.5)
        
        return "达到最大执行步骤，未完成请求"


# ===== 工具函数定义 =====
def get_weather(location):
    """模拟天气查询工具"""
    # 实际应用中这里会调用天气API
    weather_data = {
        "Hangzhou": "24℃, 晴",
        "Beijing": "18℃, 多云",
        "Shanghai": "22℃, 小雨",
        "New York": "15℃, 阴",
        "London": "12℃, 雨"
    }
    return weather_data.get(location, f"未找到 {location} 的天气信息")

def calculator(expression):
    """计算器工具"""
    try:
        # 安全评估数学表达式
        allowed_chars = "0123456789+-*/(). "
        if all(c in allowed_chars for c in expression):
            result = eval(expression)
            return f"结果: {result}"
        return "错误: 表达式包含非法字符"
    except Exception as e:
        return f"计算错误: {str(e)}"

def web_search(query):
    """模拟网络搜索工具"""
    # 实际应用中这里会调用搜索引擎API
    return f"关于 '{query}' 的搜索结果: ..."


# ===== 使用示例 =====
if __name__ == "__main__":
    # 替换为你的 DeepSeek API 密钥
    API_KEY = "sk-d8ff179980db4bf8a8d1b8e89d22e0c6"
    
    # 创建 Agent 实例
    agent = Agent(api_key=API_KEY, max_steps=5)
    
    # 注册工具
    agent.register_tool(
        tool_name="get_weather",
        description="获取指定地点的天气信息",
        parameters={
            "type": "object",
            "properties": {
                "location": {
                    "type": "string",
                    "description": "城市名称的英文，如 Hangzhou, Beijing"
                }
            },
            "required": ["location"]
        },
        tool_function=get_weather
    )
    
    agent.register_tool(
        tool_name="calculator",
        description="执行数学计算",
        parameters={
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "数学表达式，如 '2 + 3 * 4'"
                }
            },
            "required": ["expression"]
        },
        tool_function=calculator
    )
    
    agent.register_tool(
        tool_name="web_search",
        description="在互联网上搜索信息",
        parameters={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "搜索关键词或问题"
                }
            },
            "required": ["query"]
        },
        tool_function=web_search
    )
    
    # 测试用例
    test_cases = [
        "杭州今天的天气怎么样？",
        "计算(15 + 8) * 3的结果是多少？"
    ]
    
    for query in test_cases:
        print("\n" + "="*50)
        print(f"测试问题: {query}")
        response = agent.run(query)
        print(f"最终回答: {response}")
        print("="*50)
        time.sleep(2)  # 避免请求过速