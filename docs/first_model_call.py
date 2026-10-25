from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:11434/v1/",
    api_key="ollama",
)

response = client.chat.completions.create(
    model="gemma3:1b",
    messages=[
        {"role": "system", "content": "Answer clearly in one sentence."},
        {"role": "user", "content": "What does a database index do?"},
    ],
)

print("Answer:", response.choices[0].message.content)
print("Input tokens:", response.usage.prompt_tokens)
print("Output tokens:", response.usage.completion_tokens)