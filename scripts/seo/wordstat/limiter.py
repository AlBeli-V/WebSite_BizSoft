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
# После отказа по квоте не блокируемся на весь час вслепую: сервис мог освободить
# окно раньше. Ждём интервал, делаем один пробный запрос и по его исходу решаем.
PROBE_START_SEC = 600
PROBE_MAX_SEC = 3600


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
        state = self._load_state()
        self.hour_marks = state["marks"]
        self.blocked_until = state["blocked_until"]
        self.probe_interval = state["probe_interval"]
        self.observed_quota: int | None = state.get("observed_quota")

    def now(self) -> float:
        return self._now if self._now is not None else time.time()

    # ── Часовое окно ─────────────────────────────────────────────────────
    def _load_state(self) -> dict:
        empty = {"marks": [], "blocked_until": 0.0,
                 "probe_interval": PROBE_START_SEC, "observed_quota": None}
        if not self.path.exists():
            return empty
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            marks = [float(t) for t in data.get("marks", [])]
        except (ValueError, TypeError, OSError):
            # Состояние нечитаемо: считаем окно полным и ждём безопасный интервал.
            return {"marks": [self.now()] * self.rph,
                    "blocked_until": self.now() + PROBE_START_SEC,
                    "probe_interval": PROBE_START_SEC, "observed_quota": None}
        cutoff = self.now() - 3600
        return {"marks": [t for t in marks if t > cutoff],
                "blocked_until": float(data.get("blocked_until") or 0.0),
                "probe_interval": float(data.get("probe_interval") or PROBE_START_SEC),
                "observed_quota": data.get("observed_quota")}

    def _save_marks(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps({
            "marks": [round(t, 3) for t in self.hour_marks],
            "requests_per_hour": self.rph,
            "blocked_until": round(self.blocked_until, 3),
            "probe_interval": self.probe_interval,
            "observed_quota": self.observed_quota,
            "updated_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        }), encoding="utf-8")

    def hour_used(self) -> int:
        cutoff = self.now() - 3600
        self.hour_marks = [t for t in self.hour_marks if t > cutoff]
        return len(self.hour_marks)

    def hour_remaining(self) -> int:
        return max(0, self.rph - self.hour_used())

    def seconds_until_slot(self) -> float:
        if self.blocked_until > self.now():
            return round(self.blocked_until - self.now(), 1)
        if self.hour_remaining() > 0:
            return 0.0
        return max(0.0, min(self.hour_marks) + 3600 - self.now())

    def probe_due(self) -> bool:
        """Пора ли проверить, освободилась ли квота."""
        return bool(self.blocked_until) and self.now() >= self.blocked_until

    # ── Секундное окно ───────────────────────────────────────────────────
    def _refill(self) -> None:
        now = self.now()
        elapsed = now - self.last_refill
        self.tokens = min(float(self.rps), self.tokens + elapsed * self.rps)
        self.last_refill = now

    def acquire(self, sleep=time.sleep) -> None:
        """Занять слот.

        После отказа по квоте разрешается ровно один пробный запрос по истечении
        интервала ожидания: сервис мог освободить окно раньше, чем истечёт час,
        и блокировать себя вслепую на час — терять время без причины.
        """
        if self.blocked_until > self.now():
            raise QuotaExhausted(
                f"ожидание после отказа по квоте, проба через "
                f"{self.seconds_until_slot():.0f} с")
        if self.probe_due():
            # Пробный запрос: окно очищаем, чтобы вызов прошёл, но интервал
            # оставляем на случай повторного отказа.
            self.hour_marks = []
            self.blocked_until = 0.0
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

    def note_success(self) -> None:
        """Успешный ответ снимает блокировку и возвращает интервал к исходному."""
        if self.blocked_until or self.probe_interval != PROBE_START_SEC:
            self.blocked_until = 0.0
            self.probe_interval = PROBE_START_SEC
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
        # Сервис отказал: ждём интервал, затем один пробный запрос. При повторном
        # отказе интервал удваивается, но не превышает часа.
        self.hour_marks = [self.now()] * self.rph
        self.blocked_until = self.now() + self.probe_interval
        self.probe_interval = min(PROBE_MAX_SEC, self.probe_interval * 2)
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
        if resp.status_code == 200:
            limiter.note_success()
            return resp
        if 500 <= resp.status_code < 600:
            last = resp
            if attempt == max_attempts - 1:
                return resp
            sleep(limiter.backoff_delay(attempt))
            continue
        return resp
    return last
