from dotenv import load_dotenv
from openai import OpenAI
import os


class AIChat:
    def __init__(self, base_url="https://api.deepseek.com", env_path="../../.env"):
        load_dotenv(env_path)
        self.client = OpenAI(api_key=os.getenv("SECRET_KEY"), base_url=base_url)

    def get_response(self, prompt, system_message="You are a helpful assistant"):
        response = self.client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": prompt},
            ],
            stream=False,
        )

        return response.choices[0].message.content


if __name__ == "__main__":
    chat = AIChat()
    response = chat.get_response("1+1=?")
    print(response)
