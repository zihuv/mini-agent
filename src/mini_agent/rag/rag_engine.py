from .text_chunker import TextFileChunker
from .embed import VectorDB
from mini_agent.llm.llm import OpenAILLM
from mini_agent.llm.utils import Message
from mini_agent.config.agent_config import AgentConfig
from typing import Optional

# 可选：你可以用自己的 LLM 封装，也可以用 AIChat 方式

def rag_answer(document_path: str, question: str, config: Optional[AgentConfig] = None) -> str:
    """
    基于指定文档和问题，返回 RAG 增强答案。
    config 可选，用于 LLM 选择和 API KEY。
    """
    # 1. 文档分块
    chunker = TextFileChunker(file_path=document_path)
    chunks = chunker.get_chunks()
    # 2. 建立向量数据库
    db = VectorDB()
    db.create_db(chunks)
    # 3. 检索相关内容
    results = db.query(question, top_k=3)
    # 4. 构建prompt
    prompt = "请根据上下文回答用户的问题\n"
    prompt += f"问题: {question}\n"
    prompt += "上下文:\n"
    for res in results:
        prompt += f"{res}\n"
        prompt += "-------------\n"
    # 5. 用 LLM 生成回答
    if config is not None:
        llm = OpenAILLM(config.openai_api_key, config.model, config.base_url)
        response = llm.generate([
            Message(role="system", content="你是一个有用的助手。"),
            Message(role="user", content=prompt)
        ])
        return response.content
    else:
        # fallback: 直接返回 prompt
        return prompt 