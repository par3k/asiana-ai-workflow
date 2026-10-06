import logging
import os
import sys
from logging.handlers import RotatingFileHandler

# 프로젝트 루트/logs (LOG_DIR 환경변수로 변경 가능)
LOG_DIR = os.getenv("LOG_DIR", os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs"))
LOG_FILE = "app.log"
MAX_BYTES = 10 * 1024 * 1024  # 파일 1개당 10MB
BACKUP_COUNT = 5              # app.log.1 ~ app.log.5 까지 보관, 그 이상은 삭제

_FORMAT = "%(asctime)s %(levelname)s [%(name)s] %(message)s"


class _StdoutToLog:
    """print() 출력을 콘솔은 그대로 두고 로그 파일에도 한 줄씩 기록한다."""

    def __init__(self, original, logger: logging.Logger):
        self._original = original
        self._logger = logger
        self._buffer = ""

    def write(self, text):
        self._original.write(text)
        self._buffer += text
        while "\n" in self._buffer:
            line, self._buffer = self._buffer.split("\n", 1)
            if line.strip():
                self._logger.info(line)
        return len(text)

    def flush(self):
        self._original.flush()

    def __getattr__(self, name):
        return getattr(self._original, name)


def setup_logging() -> None:
    root = logging.getLogger()
    if getattr(root, "_file_logging_ready", False):  # 중복 설정 방지
        return

    os.makedirs(LOG_DIR, exist_ok=True)
    file_handler = RotatingFileHandler(
        os.path.join(LOG_DIR, LOG_FILE),
        maxBytes=MAX_BYTES,
        backupCount=BACKUP_COUNT,
        encoding="utf-8",
    )
    file_handler.setFormatter(logging.Formatter(_FORMAT))

    # uvicorn / uvicorn.access 는 propagate=False 라 root 설정이 닿지 않으므로 각각 추가
    # (uvicorn.error 는 uvicorn 으로 전파되므로 따로 추가하면 중복 기록됨)
    for name in ("", "uvicorn", "uvicorn.access"):
        logger = logging.getLogger(name)
        logger.addHandler(file_handler)
        if name == "":
            logger.setLevel(logging.INFO)

    # print() 캡처: 콘솔 중복 출력을 막기 위해 파일 전용 로거 사용
    stdout_logger = logging.getLogger("stdout")
    stdout_logger.propagate = False
    stdout_logger.setLevel(logging.INFO)
    stdout_logger.addHandler(file_handler)
    sys.stdout = _StdoutToLog(sys.stdout, stdout_logger)

    root._file_logging_ready = True
