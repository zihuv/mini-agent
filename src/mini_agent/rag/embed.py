from sentence_transformers import SentenceTransformer
import faiss
import numpy as np
from .text_chunker import TextFileChunker

class VectorDB:
    def __init__(self, model_name='all-MiniLM-L6-v2'):
        """初始化向量数据库"""
        self.model = SentenceTransformer(model_name)
        self.index = None
        self.documents = []
    
    def embed(self, texts):
        """将文本转换为向量"""
        return self.model.encode(texts, show_progress_bar=False)
    
    def create_db(self, texts):
        """构建向量数据库"""
        self.documents = texts
        embeddings = self.embed(texts)
        dim = embeddings.shape[1]
        self.index = faiss.IndexFlatL2(dim)
        self.index.add(np.array(embeddings))
    
    def query(self, question, top_k=3):
        """查询最相关文档"""
        if self.index is None:
            raise ValueError("数据库尚未创建，请先调用create_db()方法")
        q_embedding = self.embed([question])
        D, I = self.index.search(np.array(q_embedding), top_k)
        return [self.documents[i] for i in I[0]] 