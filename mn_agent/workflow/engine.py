import logging
import traceback
import json
import re
from typing import Dict, Any, List, Optional
from datetime import datetime
import asyncio

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class WorkflowContext:
    """工作流上下文管理器"""
    
    def __init__(self, initial_data: Optional[Dict[str, Any]] = None):
        self.data = initial_data or {}
        self.execution_history = []
        self.errors = []
        self.start_time = datetime.now()
    
    def update(self, new_data: Dict[str, Any]):
        """更新上下文数据"""
        if new_data:
            self.data.update(new_data)
            self.execution_history.append({
                'timestamp': datetime.now().isoformat(),
                'data_update': new_data
            })
    
    def get(self, key: str, default=None):
        """获取上下文数据"""
        return self.data.get(key, default)
    
    def set(self, key: str, value: Any):
        """设置上下文数据"""
        self.data[key] = value
    
    def add_error(self, error: Exception, node_id: str):
        """添加错误信息"""
        self.errors.append({
            'node_id': node_id,
            'error': str(error),
            'timestamp': datetime.now().isoformat(),
            'traceback': traceback.format_exc()
        })
    
    def get_execution_summary(self) -> Dict[str, Any]:
        """获取执行摘要"""
        return {
            'start_time': self.start_time.isoformat(),
            'end_time': datetime.now().isoformat(),
            'total_updates': len(self.execution_history),
            'total_errors': len(self.errors),
            'context': self.data
        }

class WorkflowEngine:
    def __init__(self, workflow_def: Dict[str, Any], node_registry: Dict[str, Any]):
        self.workflow = workflow_def
        self.node_registry = node_registry
        self.context = WorkflowContext()
        self.nodes = {node['id']: node for node in workflow_def.get('nodes', [])}
        self.connections = workflow_def.get('connections', [])
        self.max_retries = 3
        self.retry_delay = 1  # 秒
        
        # 验证工作流定义
        self._validate_workflow()
    
    def _validate_workflow(self):
        """验证工作流定义"""
        if not self.nodes:
            raise ValueError("工作流必须包含至少一个节点")
        
        # 检查节点类型是否已注册
        for node_id, node in self.nodes.items():
            node_type = node.get('type')
            if node_type not in self.node_registry:
                raise ValueError(f"未注册的节点类型: {node_type} (节点: {node_id})")
        
        # 检查连接的有效性
        node_ids = set(self.nodes.keys())
        for conn in self.connections:
            if conn.get('from') not in node_ids:
                raise ValueError(f"连接中的源节点不存在: {conn.get('from')}")
            if conn.get('to') not in node_ids:
                raise ValueError(f"连接中的目标节点不存在: {conn.get('to')}")

    def find_start_nodes(self) -> List[Dict[str, Any]]:
        """查找所有起始节点（没有前驱的节点）"""
        node_ids = set(self.nodes.keys())
        to_ids = set(conn['to'] for conn in self.connections)
        start_ids = node_ids - to_ids
        
        if not start_ids:
            raise Exception('未找到起始节点')
        
        return [self.nodes[node_id] for node_id in start_ids]

    def get_node_executor(self, node_type: str):
        """获取节点执行器"""
        return self.node_registry.get(node_type)

    def process_data_mapping(self, mapping: Dict[str, Any], source_context: Dict[str, Any]) -> Dict[str, Any]:
        """处理数据映射"""
        if not mapping:
            return {}
        
        result = {}
        for target_key, source_template in mapping.items():
            if isinstance(source_template, str):
                # 处理模板变量
                result[target_key] = self._process_template(source_template, source_context)
            else:
                result[target_key] = source_template
        
        return result

    def _process_template(self, template: str, context: Dict[str, Any]) -> str:
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

    def find_next_nodes(self, current_node: Dict[str, Any], result: Dict[str, Any]) -> List[Dict[str, Any]]:
        """查找下一个要执行的节点，支持条件分支"""
        next_nodes = []
        
        for conn in self.connections:
            if conn['from'] == current_node['id']:
                condition = conn.get('condition')
                
                # 如果没有条件或条件为真，则添加到下一个节点列表
                if not condition or self.eval_condition(condition, result):
                    next_node = self.nodes[conn['to']]
                    next_nodes.append(next_node)
        
        return next_nodes

    def eval_condition(self, condition: str, context: Dict[str, Any]) -> bool:
        """评估条件表达式"""
        try:
            # 处理模板变量
            processed_condition = self._process_template(condition, context)
            
            # 安全地执行表达式，添加布尔值到上下文
            eval_context = context.copy()
            eval_context.update({"True": True, "False": False})
            return eval(processed_condition, {"__builtins__": {}}, eval_context)
        except Exception as e:
            logger.warning(f"条件评估失败: {condition}, 错误: {str(e)}")
            return False

    def _log_node_input(self, node_id: str, node_type: str, input_data: Dict[str, Any]):
        """记录节点输入"""
        logger.info(f"节点执行开始 - ID: {node_id}, 类型: {node_type}")
        logger.debug(f"节点输入数据: {input_data}")

    def _log_node_output(self, node_id: str, output_data: Dict[str, Any]):
        """记录节点输出"""
        logger.info(f"节点执行成功 - ID: {node_id}")
        logger.debug(f"节点输出数据: {output_data}")

    def _log_node_error(self, node_id: str, node_type: str, error: Exception):
        """记录节点错误"""
        logger.error(f"节点执行失败 - ID: {node_id}, 类型: {node_type}")
        logger.error(f"错误信息: {str(error)}")
        logger.debug(f"错误堆栈: {traceback.format_exc()}")

    async def execute_node_with_retry(self, node: Dict[str, Any]) -> Dict[str, Any]:
        """带重试机制的节点执行"""
        node_id = node['id']
        node_type = node['type']
        
        for attempt in range(self.max_retries):
            try:
                # 获取节点执行器
                node_executor = self.get_node_executor(node_type)
                if not node_executor:
                    raise Exception(f'未注册节点类型: {node_type}')
                
                # 执行节点
                result = await node_executor.execute(node, self.context.data)
                return result
                
            except Exception as e:
                if attempt < self.max_retries - 1:
                    logger.warning(f"节点 {node_id} 执行失败，尝试重试 ({attempt + 1}/{self.max_retries}): {str(e)}")
                    await asyncio.sleep(self.retry_delay * (attempt + 1))  # 指数退避
                else:
                    raise e

    async def execute_workflow(self, initial_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """执行完整的工作流"""
        try:
            # 初始化上下文
            if initial_context:
                self.context.update(initial_context)
            
            logger.info(f"工作流开始执行: {self.workflow.get('name', '未命名工作流')}")
            
            # 查找起始节点
            start_nodes = self.find_start_nodes()
            if not start_nodes:
                raise Exception("未找到起始节点")
            
            # 执行起始节点
            for start_node in start_nodes:
                await self._execute_node_and_continue(start_node)
            
            # 生成执行摘要
            summary = self.context.get_execution_summary()
            logger.info(f"工作流执行完成: {self.workflow.get('name', '未命名工作流')}")
            logger.info(f"执行摘要: {summary}")
            
            return {
                'success': True,
                'context': self.context.data,
                'summary': summary,
                'errors': self.context.errors
            }
            
        except Exception as e:
            logger.error(f"工作流执行过程中发生错误: {str(e)}")
            self.context.add_error(e, 'workflow_engine')
            
            return {
                'success': False,
                'error': str(e),
                'context': self.context.data,
                'summary': self.context.get_execution_summary(),
                'errors': self.context.errors
            }

    async def _execute_node_and_continue(self, node: Dict[str, Any]):
        """执行单个节点并继续后续节点"""
        node_id = node['id']
        node_type = node['type']
        
        # 记录节点输入
        self._log_node_input(node_id, node_type, self.context.data)
        
        try:
            # 执行节点（带重试）
            result = await self.execute_node_with_retry(node)
            
            # 处理数据映射
            data_mapping = node.get('dataMapping', {})
            if data_mapping:
                mapped_result = self.process_data_mapping(data_mapping, result)
                result.update(mapped_result)
            
            # 记录节点输出
            self._log_node_output(node_id, result)
            
            # 更新上下文，所有节点输出都加命名空间
            self.context.update({node_id: result})
            
            # 查找并执行下一个节点
            next_nodes = self.find_next_nodes(node, result)
            for next_node in next_nodes:
                await self._execute_node_and_continue(next_node)
                
        except Exception as e:
            # 记录错误
            self._log_node_error(node_id, node_type, e)
            self.context.add_error(e, node_id)
            
            # 根据配置决定是否继续执行
            error_handling = node.get('errorHandling', 'stop')
            if error_handling == 'stop':
                raise e
            elif error_handling == 'continue':
                logger.warning(f"节点 {node_id} 执行失败，但继续执行后续节点")
            # 可以添加更多错误处理策略

    async def execute(self, initial_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """兼容旧接口的执行方法"""
        return await self.execute_workflow(initial_context) 