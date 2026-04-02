import pytest

# add(a, b) 입력받아서 a+b를 리턴하는 함수 하나를 만들어주세요.
# given(주어진 값) - when(들어왔을 때) - then(결과값은 이래야 해) 패턴으로 작성 


def add(a, b):
    return a+b


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
    
