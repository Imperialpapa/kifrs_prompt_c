"""
System Logger - 디버깅용 로그 파일 관리
"""
import os
from datetime import datetime
from pathlib import Path

# 로그 디렉토리 설정
LOG_DIR = Path(__file__).parent.parent / "logs"
LOG_FILE = LOG_DIR / "system.log"

def _ensure_log_dir():
    """로그 디렉토리 생성"""
    LOG_DIR.mkdir(exist_ok=True)

def log(message: str, level: str = "INFO", module: str = None):
    """
    로그 메시지를 파일과 콘솔에 기록

    Args:
        message: 로그 메시지
        level: 로그 레벨 (INFO, DEBUG, WARN, ERROR)
        module: 모듈명 (예: RuleRepository, RuleService)
    """
    _ensure_log_dir()

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    module_str = f"[{module}] " if module else ""
    log_line = f"[{timestamp}] [{level}] {module_str}{message}"

    # 콘솔 출력
    print(log_line)

    # 파일에 추가
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(log_line + "\n")

def debug(message: str, module: str = None):
    log(message, "DEBUG", module)

def info(message: str, module: str = None):
    log(message, "INFO", module)

def warn(message: str, module: str = None):
    log(message, "WARN", module)

def error(message: str, module: str = None):
    log(message, "ERROR", module)

def clear_log():
    """로그 파일 초기화"""
    _ensure_log_dir()
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        f.write(f"=== Log started at {datetime.now().isoformat()} ===\n")
