import os
from mn_agent.rag.rag_engine import rag_answer
from mn_agent.config.agent_config import AgentConfig
import dotenv
dotenv.load_dotenv("../.env")

def test_rag_answer():
    # 创建一个临时测试文档
    test_file = 'tests/input.txt'
    
    # 测试问题
    question = '猫的名字是什么？'
    answer = rag_answer(test_file, question)
    print('RAG回答:', answer)

def test_rag_answer_with_config():
    test_file = 'tests/input.txt'
    question = '猫的名字是什么？'
    config = AgentConfig(model='deepseek-chat', 
                         openai_api_key=os.getenv('SECRET_KEY') or '',
                         base_url=os.getenv('BASE_URL') or '',
                         document_path=test_file)
    answer = rag_answer(test_file, question, config)
    print('llm回答:', answer)


if __name__ == '__main__':
    test_rag_answer_with_config() 