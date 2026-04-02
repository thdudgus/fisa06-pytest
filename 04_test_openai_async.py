# 실행: pytest 04_test_openai_async.py -v -s

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '08_chat_ui_with_OpenAI'))

import time
import asyncio
from unittest.mock import MagicMock
import pytest
import httpx
import main_with_session_cookie

DELAY = 0.3   # OpenAI API 응답시간을 흉내 낸 지연 (초)
N =200       # 동시 요청 수


# ── 모든 테스트 전에 실행: 실제 OpenAI 대신 가짜 함수로 교체 ──────────────────
@pytest.fixture(autouse=True)
def mock_openai_clients(monkeypatch):
    def sync_create(*_, **__):         # time.sleep → 스레드를 점유하며 대기
        # print(*_)
        time.sleep(DELAY)
        return MagicMock(output_text="응답")

    async def async_create(*_, **__):  # asyncio.sleep → 이벤트루프를 양보하며 대기
        await asyncio.sleep(DELAY)
        return MagicMock(output_text="응답")

    monkeypatch.setattr(main_with_session_cookie.client.responses, "create", sync_create)
    monkeypatch.setattr(main_with_session_cookie.async_client.responses, "create", async_create)


# ── N개 요청을 동시에 보내는 헬퍼 ────────────────────────────────────────────
async def _send_concurrent(endpoint: str, n: int) -> list:
    transport = httpx.ASGITransport(app=main_with_session_cookie.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        return await asyncio.gather(
            *[ac.post(endpoint, json={"user_message": "안녕"}) for _ in range(n)]
        )


# ── 테스트 1: def + OpenAI → FastAPI 스레드풀 처리 ───────────────────────────
def test_sync_def():
    start = time.perf_counter()
    results = asyncio.run(_send_concurrent("/bench/sync_def", N))
    elapsed = time.perf_counter() - start

    print(f"\n  [sync_def]   {N}개 요청 → {elapsed:.2f}초")

    assert all(r.status_code == 200 for r in results)
    assert elapsed < DELAY * 5   # 스레드풀(40개)이 나눠서 처리 → 빠름


# ── 테스트 2: async def + OpenAI → 이벤트루프 블로킹 ────────────────────────
def test_async_bad():
    start = time.perf_counter()
    results = asyncio.run(_send_concurrent("/bench/async_bad", N))
    elapsed = time.perf_counter() - start

    print(f"\n  [async_bad]  {N}개 요청 → {elapsed:.2f}초")

    assert all(r.status_code == 200 for r in results)
    assert elapsed >= DELAY * (N // 2)   # 순차 처리 → 느림


# ── 테스트 3: async def + AsyncOpenAI → 진짜 비동기 ─────────────────────────
def test_async_good():
    start = time.perf_counter()
    results = asyncio.run(_send_concurrent("/bench/async_good", N))
    elapsed = time.perf_counter() - start

    print(f"\n  [async_good] {N}개 요청 → {elapsed:.2f}초")

    assert all(r.status_code == 200 for r in results)
    assert elapsed < DELAY * 3   # 동시 처리 → 빠름


# ── 테스트 4: 세 방식 한눈에 비교 ────────────────────────────────────────────
def test_비교():
    timings = {}
    for endpoint in ["/bench/sync_def", "/bench/async_bad", "/bench/async_good"]:
        start = time.perf_counter()
        asyncio.run(_send_concurrent(endpoint, N))
        timings[endpoint] = time.perf_counter() - start

    print(f"\n  {'방식':<20} {'소요시간':>8}")
    print("  " + "-" * 30)
    for endpoint, elapsed in timings.items():
        print(f"  {endpoint:<20} {elapsed:>7.2f}초")

    assert timings["/bench/async_bad"] > timings["/bench/async_good"] * 3




