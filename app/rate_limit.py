"""
Простой rate limiter в памяти процесса — после нескольких неудачных попыток
подряд по одному ключу (например IP+email) временно блокирует дальнейшие
попытки. Не переживает перезапуск процесса и не общий между процессами
(бот/админка/сайт у нас — три отдельных процесса) — цель не "идеальная защита
от распределённого брутфорса", а просто не дать перебирать пароли в лоб
простым скриптом по логину/паролю.
"""
import time

MAX_ATTEMPTS = 5
COOLDOWN_SECONDS = 5 * 60  # 5 минут

_failed_attempts: dict[str, list[float]] = {}


def _recent(key: str) -> list[float]:
    now = time.time()
    attempts = [t for t in _failed_attempts.get(key, []) if now - t < COOLDOWN_SECONDS]
    _failed_attempts[key] = attempts
    return attempts


def register_failure(key: str) -> None:
    attempts = _recent(key)
    attempts.append(time.time())
    _failed_attempts[key] = attempts


def is_blocked(key: str) -> bool:
    return len(_recent(key)) >= MAX_ATTEMPTS


def reset(key: str) -> None:
    _failed_attempts.pop(key, None)
