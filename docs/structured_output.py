from ollama import chat
from pydantic import BaseModel, Field, ValidationError


class Answer(BaseModel):
    answer: str
    citations: list[str]
    confidence: float = Field(ge=0, le=1)


messages = [
    {
        "role": "system",
        "content": (
            "Answer clearly. There are no source documents, "
            "so citations should be an empty list."
        ),
    },
    {
        "role": "user",
        "content": "What does a database index do?",
    },
]

for attempt in range(2):
    response = chat(
        model="gemma3:1b",
        messages=messages,
        format=Answer.model_json_schema(),
    )
    raw_answer = response.message.content

    try:
        result = Answer.model_validate_json(raw_answer)
        break
    except ValidationError as error:
        if attempt == 1:
            raise
        messages.append({"role": "assistant", "content": raw_answer})
        messages.append(
            {
                "role": "user",
                "content": (
                    "Fix your previous response to match the required fields. "
                    f"Validation error: {error}"
                ),
            }
        )

print(result.model_dump_json(indent=2))