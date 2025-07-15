from typing import Dict, List
from .base import ToolBase
from mn_agent.llm.utils import Tool

class FileSystemTool(ToolBase):
    """文件系统工具类"""
    
    def __init__(self):
        pass

    async def cleanup(self) -> None:
        pass


    async def get_tools(self) -> Dict[str, List[Tool]]:
        return {
            'file_system': [
                Tool(
                    tool_name='read_file',
                    server_name='file_system',
                    description='Read the content of a file',
                    parameters={
                        'type': 'object',
                        'properties': {
                            'path': {
                                'type': 'string',
                                'description': 'The relative path of the file',
                            }
                        },
                        'required': ['path'],
                        'additionalProperties': False
                    }),
                Tool(
                    tool_name='list_files',
                    server_name='file_system',
                    description='List all files in a directory',
                    parameters={
                        'type': 'object',
                        'properties': {
                            'directory': {
                                'type': 'string',
                                'description': 'The directory to list files from'
                            }
                        },
                        'required': ['directory'],
                        'additionalProperties': False
                    })
            ]
        }
    
    async def call_tool(self, server_name: str, *, tool_name: str, tool_args: dict) -> str:
        if server_name != 'file_system':
            raise ValueError(f"Unknown server: {server_name}")
        
        if tool_name == 'read_file':
            return self.read_file(tool_args['path'])
        elif tool_name == 'list_files':
            return self.list_files(tool_args['directory'])
        else:
            raise ValueError(f"Unknown tool: {tool_name}")

    def list_files(self, directory: str) -> str:
        """列出指定目录下的所有文件，每行一个文件名"""
        import os
        return '\n'.join(os.listdir(directory))

    def read_file(self, file_path: str) -> str:
        """读取指定文件的内容"""
        with open(file_path, 'r', encoding='utf-8') as file:
            return file.read()