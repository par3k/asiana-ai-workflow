import logging
import os
import time
from openai import OpenAI
from .classification_list import TOOLS

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
logger = logging.getLogger("api.llm")

_PREVIEW_LEN = 200  # 질문/응답 로그 미리보기 길이


def _preview(text) -> str:
    text = "" if text is None else str(text)
    return text if len(text) <= _PREVIEW_LEN else text[:_PREVIEW_LEN] + f"...(총 {len(text)}자)"


def _usage(response) -> str:
    u = getattr(response, "usage", None)
    if not u:
        return "-"
    return f"prompt={u.prompt_tokens} completion={u.completion_tokens} total={u.total_tokens}"


def classify_message(message: str) -> str:
    model = "gpt-4.1-mini"
    logger.info("OpenAI 분류 요청 model=%s tools=%d 질문=%r", model, len(TOOLS), _preview(message))
    start = time.perf_counter()
    try:
        response = client.chat.completions.create(
            # temperature는 분류 작업에 맞는 낮은 값으로 설정. 기본값은 1
            model=model,
            messages=[{"role": "user", "content": message}],
            tools=TOOLS,
            tool_choice="auto",
            temperature=0
            )
    except Exception:
        logger.exception("OpenAI 분류 호출 실패 (%.0fms)", (time.perf_counter() - start) * 1000)
        raise
    elapsed = (time.perf_counter() - start) * 1000
    choice = response.choices[0]
    tool_calls = choice.message.tool_calls
    if not tool_calls:
        logger.info("OpenAI 분류 응답 tool_call=없음 finish=%s tokens[%s] (%.0fms)",
                    choice.finish_reason, _usage(response), elapsed)
        return "답변이 어려운 질문입니다."
    logger.info("OpenAI 분류 응답 tool_call=%s args=%s finish=%s tokens[%s] (%.0fms)",
                tool_calls[0].function.name, _preview(tool_calls[0].function.arguments),
                choice.finish_reason, _usage(response), elapsed)
    return tool_calls[0].function.name

def generate_response(user_message: str, data: str) -> str:
    model = "gpt-4.1-mini"
    logger.info("OpenAI 응답생성 요청 model=%s 질문=%r 참고데이터=%r", model, _preview(user_message), _preview(data))
    start = time.perf_counter()
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": f"사용자의 질문에 대해 아래 참고 데이터를 바탕으로 사용자의 질문에 답변해. "
                               f"만약 참고데이터에 적절한 내용이 없으면 응답불가합니다 라고 답변해. \n\n[참고 데이터]\n{data}",
                },
                {
                    "role": "user",
                    "content": user_message,
                },
            ],
            temperature=0.3,
            # max_completion_tokens=100
        )
    except Exception:
        logger.exception("OpenAI 응답생성 호출 실패 (%.0fms)", (time.perf_counter() - start) * 1000)
        raise
    elapsed = (time.perf_counter() - start) * 1000
    answer = response.choices[0].message.content.strip()
    logger.info("OpenAI 응답생성 응답 finish=%s tokens[%s] (%.0fms) 응답=%r",
                response.choices[0].finish_reason, _usage(response), elapsed, _preview(answer))
    return answer
