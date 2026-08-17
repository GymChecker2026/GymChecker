import anthropic

client = anthropic.Anthropic()
res = client.messages.create(
    model="claude-haiku-4-5-20251001",
    max_tokens=100,
    messages=[{"role": "user", "content": "こんにちはとだけ返して"}],
)
print(res.content[0].text)