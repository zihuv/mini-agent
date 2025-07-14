from dotenv import load_dotenv
from openai import OpenAI
import os

load_dotenv("../../.env");
client = OpenAI(api_key=os.getenv("SECRET_KEY"), base_url="https://api.deepseek.com")

url = "http://localhost:9000"

resp = client.responses.create(
    model="deepseek-chat",
    tools=[
        {
            "type": "mcp",
            "server_label": "dice_server",
            "server_url": f"{url}/mcp/",
            "require_approval": "never",
        },
    ],
    input="Roll a few dice!",
)

print(resp.output_text)