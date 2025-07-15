import os

def list_files(directory: str) -> str:
        """列出指定目录下的所有文件，每行一个文件名"""
        import os
        return '\n'.join(os.listdir(directory))

print(list_files("./"))