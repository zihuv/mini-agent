from dotenv import load_dotenv
from openai import OpenAI
import os

load_dotenv("../../.env");
client = OpenAI(api_key=os.getenv("SECRET_KEY"), base_url="https://api.deepseek.com")

response = client.chat.completions.create(
    model="deepseek-chat",
    messages=[
        {"role": "system", "content": "You are a helpful assistant"},
        {"role": "user", "content": "1+1=?"},
    ],
    stream=False
)

print(response.choices[0].message.content)