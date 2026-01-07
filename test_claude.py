import anthropic
import os
from dotenv import load_dotenv

# Load API key from .env file
load_dotenv()

client = anthropic.Anthropic(
    api_key=os.environ.get("ANTHROPIC_API_KEY")
)

message = client.messages.create(
    model="claude-sonnet-4-20250514",
    max_tokens=1024,
    messages=[
        {"role": "user", "content": "Say hello and confirm you're working!"}
    ]
)

print(message.content[0].text)