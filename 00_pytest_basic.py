# 폴더 전체 실행: cd ..
#                 python -m pytest 09_testing/ -v
# 실행: pytest 00_pytest_basic.py -v
#
# [Step 0] pytest 기초 — GWT 패턴으로 순수 함수 테스트하기
#
# Given : 테스트에 필요한 데이터를 준비한다
# When  : 테스트할 함수를 호출한다
# Then  : 결과가 예상과 같은지 assert로 확인한다

import pytest


# ── 테스트 대상 함수 ───────────────────────────────────────────────────────────

def add(a, b):
    return a + b

def divide(a, b):
    if b == 0:
        raise ValueError("0으로 나눌 수 없습니다.")
    return a / b



# ── 기본 테스트 ───────────────────────────────────────────────────────────────

def test_두_수를_더하면_합이_반환된다():
    # Given
    a, b = 2, 3

    # When
    result = add(a, b)

    # Then
    assert result == 5


def test_소수_덧셈은_approx로_비교한다():
    # Given: 0.1 + 0.2 는 파이썬 내부에서 0.30000000000000004 이므로
    #        == 비교가 실패할 수 있다 → pytest.approx() 사용
    # When
    result = add(0.1, 0.2)

    # Then
    assert result == pytest.approx(0.3)


def test_정상적으로_나누면_몫이_반환된다():
    # Given
    a, b = 10, 2

    # When
    result = divide(a, b)

    # Then
    assert result == 5.0


# ── 예외 테스트 ───────────────────────────────────────────────────────────────

def test_0으로_나누면_ValueError가_발생한다():
    # Given
    a, b = 10, 0

    # When & Then: 이 블록 안에서 ValueError가 발생해야 테스트 통과
    with pytest.raises(ValueError, match="0으로 나눌 수 없습니다."):
        divide(a, b)
