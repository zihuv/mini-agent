import asyncio
import aiohttp
import json
import re
from datetime import datetime
from typing import Dict, Any, List
from mini_agent.agent.agent import Agent
from mini_agent.config.agent_config import AgentConfig

class BaseNode:
    @staticmethod
    async def execute(node, context):
        raise NotImplementedError

    @staticmethod
    def process_template(template: str, context: Dict[str, Any]) -> str:
        """处理模板变量替换"""
        if not isinstance(template, str):
            return template
        
        def replace_var(match):
            var_path = match.group(1).strip()
            keys = var_path.split('.')
            value = context
            try:
                for key in keys:
                    value = value[key]
                return str(value)
            except (KeyError, TypeError):
                return match.group(0)
        
        return re.sub(r'\{\{([^}]+)\}\}', replace_var, template)

# ==================== 触发器节点 ====================

class TriggerManualNode(BaseNode):
    @staticmethod
    async def execute(node, context):
        print(f"手动触发节点: {node['id']}")
        return {"triggered": True, "timestamp": datetime.now().isoformat()}

class TriggerTimerNode(BaseNode):
    @staticmethod
    async def execute(node, context):
        print(f"定时触发节点: {node['id']}")
        config = node.get('config', {})
        interval = config.get('interval', '1m')
        return {
            "triggered": True, 
            "timestamp": datetime.now().isoformat(),
            "interval": interval
        }

class TriggerWebhookNode(BaseNode):
    @staticmethod
    async def execute(node, context):
        print(f"Webhook触发节点: {node['id']}")
        # 从上下文中获取webhook数据
        webhook_data = context.get('webhook_data', {})
        return {
            "triggered": True,
            "webhook_data": webhook_data,
            "timestamp": datetime.now().isoformat()
        }

# ==================== 操作节点 ====================

class ActionHttpNode(BaseNode):
    @staticmethod
    async def execute(node, context):
        print(f"HTTP请求节点: {node['id']}")
        config = node.get('config', {})
        
        # 处理模板变量
        url = BaseNode.process_template(config.get('url'), context)
        method = config.get('method', 'GET').upper()
        headers = config.get('headers', {})
        body = config.get('body', None)
        params = config.get('params', None)
        timeout = config.get('timeout', 10)
        
        # 处理模板变量
        if body:
            body = BaseNode.process_template(json.dumps(body), context)
            try:
                body = json.loads(body)
            except json.JSONDecodeError:
                pass
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.request(
                    method, url, headers=headers, json=body, 
                    params=params, timeout=timeout
                ) as resp:
                    resp_data = await resp.text()
                    return {
                        "status": resp.status, 
                        "body": resp_data,
                        "headers": dict(resp.headers)
                    }
            except Exception as e:
                raise Exception(f"HTTP请求失败: {str(e)}")

class ActionEmailNode(BaseNode):
    @staticmethod
    async def execute(node, context):
        print(f"邮件发送节点: {node['id']}")
        config = node.get('config', {})
        
        # 处理模板变量
        to_email = BaseNode.process_template(config.get('to'), context)
        subject = BaseNode.process_template(config.get('subject'), context)
        body = BaseNode.process_template(config.get('body'), context)
        
        # 模拟邮件发送
        print(f"发送邮件到: {to_email}")
        print(f"主题: {subject}")
        print(f"内容: {body}")
        
        return {
            "email_sent": True,
            "to": to_email,
            "subject": subject,
            "timestamp": datetime.now().isoformat()
        }

class ActionDatabaseNode(BaseNode):
    @staticmethod
    async def execute(node, context):
        print(f"数据库操作节点: {node['id']}")
        config = node.get('config', {})
        operation = config.get('operation', 'select')
        table = config.get('table', '')
        data = config.get('data', {})
        
        # 处理模板变量
        if data:
            data = BaseNode.process_template(json.dumps(data), context)
            try:
                data = json.loads(data)
            except json.JSONDecodeError:
                pass
        
        # 模拟数据库操作
        print(f"执行数据库操作: {operation} on {table}")
        print(f"数据: {data}")
        
        return {
            "db_operation": operation,
            "table": table,
            "affected_rows": 1,
            "data": data
        }

class ActionAIAgentNode(BaseNode):
    @staticmethod
    async def execute(node, context):
        print(f"AI Agent节点: {node['id']}")
        try:
            config = node.get('config', {})
            
            # 处理模板变量
            user_prompt = BaseNode.process_template(config.get('prompt'), context)
            
            # 构建Agent配置（不包含prompt）
            agent_config = {
                "model": config.get('model', 'deepseek-chat'),
                "base_url": config.get('base_url'),
                "openai_api_key": config.get('openai_api_key'),
                "system_prompt": config.get('system_prompt', '你是一个有用的助手。')
            }
            
            agent = Agent(AgentConfig.from_dict(agent_config))
            # 将用户提示作为输入传递给Agent
            result = await agent.run(user_prompt)
            # 处理输出映射
            output_mapping = config.get('outputMapping', {})
            mapped_result = {}
            
            if result and hasattr(result[-1], 'content'):
                ai_output = result[-1].content
                mapped_result["ai_output"] = ai_output
                
                # 应用输出映射
                for output_key, template in output_mapping.items():
                    mapped_result[output_key] = BaseNode.process_template(template, {"aiOutput": ai_output})
            
            return mapped_result
            
        except Exception as e:
            raise Exception(f"AI Agent执行失败: {str(e)}")

# ==================== 转换节点 ====================

class TransformMapNode(BaseNode):
    @staticmethod
    async def execute(node, context):
        print(f"数据映射节点: {node['id']}")
        config = node.get('config', {})
        mappings = config.get('mappings', {})
        
        result = {}
        for output_key, template in mappings.items():
            result[output_key] = BaseNode.process_template(template, context)
        
        return result

class TransformFilterNode(BaseNode):
    @staticmethod
    async def execute(node, context):
        print(f"数据过滤节点: {node['id']}")
        config = node.get('config', {})
        condition = config.get('condition', 'true')
        input_data = config.get('input', context)
        
        # 简单条件过滤
        try:
            # 安全起见，只支持简单的布尔表达式
            if isinstance(input_data, list):
                filtered_data = []
                for item in input_data:
                    # 将当前项添加到上下文中进行评估
                    eval_context = context.copy()
                    eval_context['item'] = item
                    if eval(condition, {"__builtins__": {}}, eval_context):
                        filtered_data.append(item)
                return {"filtered_data": filtered_data}
            else:
                # 单个数据项过滤
                if eval(condition, {"__builtins__": {}}, context):
                    return {"filtered_data": input_data}
                else:
                    return {"filtered_data": None}
        except Exception as e:
            return {"error": f"过滤条件执行失败: {str(e)}"}

class TransformValidateNode(BaseNode):
    @staticmethod
    async def execute(node, context):
        print(f"数据验证节点: {node['id']}")
        config = node.get('config', {})
        rules = config.get('rules', {})
        input_data = config.get('input', context)
        
        validation_result = {"valid": True, "errors": []}
        
        for field, rule_str in rules.items():
            value = input_data.get(field)
            rules_list = rule_str.split('|')
            
            for rule in rules_list:
                rule = rule.strip()
                if rule == 'required' and not value:
                    validation_result["errors"].append(f"{field} 是必填字段")
                    validation_result["valid"] = False
                elif rule.startswith('min:') and value:
                    min_len = int(rule.split(':')[1])
                    if len(str(value)) < min_len:
                        validation_result["errors"].append(f"{field} 最小长度为 {min_len}")
                        validation_result["valid"] = False
                elif rule == 'email' and value:
                    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
                    if not re.match(email_pattern, str(value)):
                        validation_result["errors"].append(f"{field} 不是有效的邮箱格式")
                        validation_result["valid"] = False
        
        return validation_result

# ==================== 逻辑节点 ====================

class LogicIfNode(BaseNode):
    @staticmethod
    async def execute(node, context):
        print(f"条件判断节点: {node['id']}")
        config = node.get('config', {})
        condition = config.get('condition', 'true')
        
        try:
            result = eval(condition, {"__builtins__": {}}, context)
            return {"condition_result": bool(result)}
        except Exception as e:
            return {"error": f"条件执行失败: {str(e)}"}

class LogicSwitchNode(BaseNode):
    @staticmethod
    async def execute(node, context):
        print(f"多条件分支节点: {node['id']}")
        config = node.get('config', {})
        expression = config.get('expression', '')
        cases = config.get('cases', {})
        default = config.get('default', '')
        
        try:
            # 计算表达式值
            expr_value = eval(expression, {"__builtins__": {}}, context)
            
            # 查找匹配的case
            if str(expr_value) in cases:
                return {"switch_result": cases[str(expr_value)]}
            else:
                return {"switch_result": default}
        except Exception as e:
            return {"error": f"Switch执行失败: {str(e)}"}

class LogicLoopNode(BaseNode):
    @staticmethod
    async def execute(node, context):
        print(f"循环节点: {node['id']}")
        config = node.get('config', {})
        items = config.get('items', [])
        loop_var = config.get('loop_var', 'item')
        
        results = []
        for item in items:
            # 创建循环上下文
            loop_context = context.copy()
            loop_context[loop_var] = item
            loop_context['loop_index'] = len(results)
            
            # 这里可以执行循环体内的逻辑
            results.append({
                'item': item,
                'index': len(results),
                'context': loop_context
            })
        
        return {"loop_results": results, "total_items": len(results)}

class LogicMergeNode(BaseNode):
    @staticmethod
    async def execute(node, context):
        print(f"合并节点: {node['id']}")
        config = node.get('config', {})
        merge_strategy = config.get('strategy', 'append')  # append, union, custom
        
        # 从上下文中获取需要合并的数据
        merge_data = context.get('merge_data', [])
        
        if merge_strategy == 'append':
            result = []
            for data in merge_data:
                if isinstance(data, list):
                    result.extend(data)
                else:
                    result.append(data)
        elif merge_strategy == 'union':
            result = {}
            for data in merge_data:
                if isinstance(data, dict):
                    result.update(data)
        else:
            result = merge_data
        
        return {"merged_result": result}

# ==================== 节点注册表 ====================

NODE_REGISTRY = {
    # 触发器节点
    'trigger/manual': TriggerManualNode,
    'trigger/timer': TriggerTimerNode,
    'trigger/webhook': TriggerWebhookNode,
    
    # 操作节点
    'action/http': ActionHttpNode,
    'action/email': ActionEmailNode,
    'action/db': ActionDatabaseNode,
    'action/ai_agent': ActionAIAgentNode,
    
    # 转换节点
    'transform/map': TransformMapNode,
    'transform/filter': TransformFilterNode,
    'transform/validate': TransformValidateNode,
    
    # 逻辑节点
    'logic/if': LogicIfNode,
    'logic/switch': LogicSwitchNode,
    'logic/loop': LogicLoopNode,
    'logic/merge': LogicMergeNode,
} 