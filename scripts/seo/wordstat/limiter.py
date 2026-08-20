#!/usr/bin/env python3
"""Ограничитель частоты и повторы для Wordstat API.

Два независимых окна, потому что сервис ограничивает и то и другое:
  секундное — token bucket на 10 запросов в секунду;
  часовое   — скользящее окно на 100 запросов (готово к 500).

Часовое состояние переживает прогон: воркфлоу запускается несколько раз в час,
и без общего счётчика второй прогон выбрал бы квоту первого. Состояние лежит
в файле и учитывает вызовы за последние 60 минут.

Неизвестное состояние квоты (файл повреждён, часы сдвинулись) трактуется как
исчерпанное: безопасная пауза лучше, чем 429 и потерянный прогон.
"""

from __future__ import annotations

import datetime as dt
import json
import pathlib
import random
import time

STATE_PATH = pathlib.Path("reports/seo/wordstat/limiter-state.json")
MAX_ATTEMPTS = 4
BASE_BACKOFF_SEC = 2.0


class QuotaExhausted(RuntimeError):
    """Часовая квота исчерпана — прогон обязан остановиться, а не ждать час."""


class RateLimiter:
    def __init__(self, requests_per_second: int, requests_per_hour: int,
                 now: float | None = None, state_path: pathlib.Path | None = None):
        self.rps = requests_per_second
        self.rph = requests_per_hour
        self.path = state_path or STATE_PATH
        self._now = now
        self.tokens = float(requests_per_second)
        self.last_refill = self.now()
        self.hour_marks = self._load_marks()
        self.observed_quota: int | None = None

    def now(self) -> float:
        return self._now if self._now is not None else time.time()

    # ── Часовое окно ─────────────────────────────────────────────────────
    def _load_marks(self) -> list[float]:
        if not self.path.exists():
            return []
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            marks = [float(t) for t in data.get("marks", [])]
        except (ValueError, TypeError, OSError):
            # Состояние нечитаемо: считаем окно полным и ждём следующего часа.
            return [self.now()] * self.rph
        cutoff = self.now() - 3600
        return [t for t in marks if t > cutoff]

    def _save_marks(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps({
            "marks": [round(t, 3) for t in self.hour_marks],
            "requests_per_hour": self.rph,
            "updated_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        }), encoding="utf-8")

    def hour_used(self) -> int:
        cutoff = self.now() - 3600
        self.hour_marks = [t for t in self.hour_marks if t > cutoff]
        return len(self.hour_marks)

    def hour_remaining(self) -> int:
        return max(0, self.rph - self.hour_used())

    def seconds_until_slot(self) -> float:
        if self.hour_remaining() > 0:
            return 0.0
        return max(0.0, min(self.hour_marks) + 3600 - self.now())

    # ── Секундное окно ───────────────────────────────────────────────────
    def _refill(self) -> None:
        now = self.now()
        elapsed = now - self.last_refill
        self.tokens = min(float(self.rps), self.tokens + elapsed * self.rps)
        self.last_refill = now

    def acquire(self, sleep=time.sleep) -> None:
        """Занять слот. Бросает QuotaExhausted, если часовая квота выбрана."""
        if self.hour_remaining() <= 0:
            raise QuotaExhausted(
                f"часовая квота {self.rph} исчерпана, следующий слот через "
                f"{self.seconds_until_slot():.0f} с")
        self._refill()
        if self.tokens < 1:
            need = (1 - self.tokens) / self.rps
            sleep(need)
            self._refill()
        self.tokens -= 1
        self.hour_marks.append(self.now())
        self._save_marks()

    # ── Реакция на ответ сервиса ─────────────────────────────────────────
    def note_quota_error(self, message: str) -> None:
        """Извлечь фактическую квоту из текста ошибки и зафиксировать её."""
        import re
        m = re.search(r"allowed (\d+) requests", message or "")
        if m:
            self.observed_quota = int(m.group(1))
            if self.observed_quota < self.rph:
                self.rph = self.observed_quota
        # Считаем окно выбранным: сервис уже отказал.
        self.hour_marks = [self.now()] * self.rph
        self._save_marks()

    def backoff_delay(self, attempt: int) -> float:
        """Экспоненциальная задержка с разбросом, чтобы повторы не сходились."""
        return BASE_BACKOFF_SEC * (2 ** attempt) * (0.75 + random.random() * 0.5)


def with_retry(call, *, limiter: RateLimiter, sleep=time.sleep,
               max_attempts: int = MAX_ATTEMPTS):
    """Выполнить вызов с повторами. 429 повторов не получает — это квота.

    call() обязан вернуть объект с полями status_code и text либо бросить
    исключение сети. Повторяются только сетевые сбои и 5xx.
    """
    last = None
    for attempt in range(max_attempts):
        limiter.acquire(sleep=sleep)
        try:
            resp = call()
        except Exception as e:                       # сетевой сбой
            last = e
            if attempt == max_attempts - 1:
                raise
            sleep(limiter.backoff_delay(attempt))
            continue
        if resp.status_code == 429:
            limiter.note_quota_error(getattr(resp, "text", ""))
            raise QuotaExhausted(getattr(resp, "text", "429"))
        if 500 <= resp.status_code < 600:
            last = resp
            if attempt == max_attempts - 1:
                return resp
            sleep(limiter.backoff_delay(attempt))
            continue
        return resp
    return last
