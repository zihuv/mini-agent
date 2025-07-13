class TextFileChunker:
    def __init__(self, file_path='./input.txt', encoding='utf-8'):
        self.file_path = file_path
        self.encoding = encoding
    
    def get_chunks(self):
        """读取文件并按行分割内容"""
        with open(self.file_path, encoding=self.encoding) as file:
            content = file.read()
        return content.split('\n')
    
    def display_chunks(self):
        """打印每个chunk并在之间显示分隔线"""
        chunks = self.get_chunks()
        for chunk in chunks:
            print(chunk)
            print("--------------")


if __name__ == '__main__':
    chunker = TextFileChunker()
    chunker.display_chunks()