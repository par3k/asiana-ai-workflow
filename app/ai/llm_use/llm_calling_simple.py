import os
from anthropic import Anthropic
from .classification_list import TOOLS

client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

# TOOLS는 OpenAI function-calling 포맷(type/function/parameters)으로 정의되어 있어
# Anthropic SDK가 요구하는 포맷({name, description, input_schema})으로 변환
ANTHROPIC_TOOLS = [
    {
        "name": tool["function"]["name"],
        "description": tool["function"]["description"],
        "input_schema": tool["function"]["parameters"],
    }
    for tool in TOOLS
]


def classify_message(message: str) -> str:
    response = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=100,
        messages=[{"role": "user", "content": message}],
        tools=ANTHROPIC_TOOLS,
        tool_choice={"type": "any"},
    )
    tool_use_blocks = [block for block in response.content if block.type == "tool_use"]
    if not tool_use_blocks:
        return "답변이 어려운 질문입니다."
    return tool_use_blocks[0].name


def generate_response(user_message: str, data: str) -> str:
    response = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=500,
        system=f"사용자의 질문에 대해 아래 참고 데이터를 바탕으로 사용자의 질문에 답변해. "
               f"만약 참고데이터에 적절한 내용이 없으면 응답불가합니다 라고 답변해. \n\n[참고 데이터]\n{data}",
        messages=[
            {
                "role": "user",
                "content": user_message,
            },
        ],
    )
    text_blocks = [block for block in response.content if block.type == "text"]
    return text_blocks[0].text.strip() if text_blocks else ""
