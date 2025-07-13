from text_chunker import TextFileChunker
from embed import VectorDB
from chat import AIChat

if __name__ == '__main__':
    # 初始化向量数据库
    db = VectorDB()
    
    # 获取文本块并创建数据库
    chunker = TextFileChunker()
    chunks = chunker.get_chunks()
    db.create_db(chunks)

    # 在向量数据库查询,最匹配的 top_k 条记录
    question = "猫的名字是？"
    results = db.query(question,top_k=3)

    print("向量数据库查询结果：")
    for i, res in enumerate(results, 1):
        print(f"{i}. {res}")
    print("-------------")

    prompt = "根据上下文回答用户的问题\n"
    prompt += f"问题: {question}\n"
    prompt += "上下文:\n"
    for res in results:
        prompt += f"{res}\n"
        prompt += "-------------\n"
    print("prompt:", prompt)

    # 使用chat模块进行对话
    chat = AIChat()
    response = chat.get_response(prompt)
    print("AI回答：", response)