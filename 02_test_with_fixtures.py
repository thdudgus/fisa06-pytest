# 실행: pytest 02_test_with_fixtures.py -v
#
# [Step 2] pytest fixture — 테스트 격리
#
# ▶ Step 1의 문제점
#   items 리스트가 모든 테스트에서 공유된다.
#   → 한 테스트가 데이터를 추가하면 다른 테스트에 영향을 준다.
#
# ▶ 해결책: fixture
#   @pytest.fixture 를 붙인 함수를 테스트 인자로 선언하면
#   pytest가 매 테스트 전에 자동으로 실행해서 Given 패턴의 "준비물"을 넘겨준다.
#   → 매 테스트마다 새 앱 인스턴스 = 독립된 데이터 = 테스트 격리

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from pydantic import BaseModel, Field


# ── 앱 팩토리: 호출할 때마다 새 앱 인스턴스를 반환 ────────────────────────────

class Item(BaseModel):
    id: int
    name: str
    price: float = Field(..., gt=0)

def create_app():
    """매번 새로운 앱과 빈 items 리스트를 만들어 반환한다."""
    _app = FastAPI()
    _items: list[Item] = []

    @_app.get("/items/")
    def read_items():
        return _items

    @_app.get("/items/{item_id}")
    def read_item(item_id: int):
        for item in _items:
            if item.id == item_id:
                return item
        raise HTTPException(status_code=404, detail="상품을 찾을 수 없습니다.")

    @_app.post("/items/", status_code=201)
    def create_item(item: Item):
        _items.append(item)
        return item

    @_app.delete("/items/{item_id}")
    def delete_item(item_id: int):
        for idx, item in enumerate(_items):
            if item.id == item_id:
                del _items[idx]
                return {"message": "삭제되었습니다."}
        raise HTTPException(status_code=404, detail="상품을 찾을 수 없습니다.")

    return _app


# ── fixture 정의 ──────────────────────────────────────────────────────────────

@pytest.fixture
def client():
    """
    매 테스트마다 새 앱(빈 데이터)으로 TestClient를 만들어 반환한다.
    → 테스트 간 데이터가 절대 겹치지 않는다.

    GWT에서 Given 역할:
    테스트 함수가 client 인자를 선언하면 pytest가 이 fixture를 자동 실행한다.
    """
    app = create_app()
    return TestClient(app)


# ── 테스트 ────────────────────────────────────────────────────────────────────

def test_빈_상태에서_목록을_조회하면_빈_리스트가_반환된다(client):
    # Given: fixture가 빈 데이터로 새 앱을 준비했다

    # When
    response = client.get("/items/")

    # Then
    assert response.status_code == 200
    assert response.json() == []


def test_상품을_생성하면_목록에서_조회된다(client):
    # Given: 빈 상태의 client (fixture 주입)
    client.post("/items/", json={"id": 1, "name": "연필", "price": 10.0})

    # When
    response = client.get("/items/")

    # Then
    assert len(response.json()) == 1
    assert response.json()[0]["name"] == "연필"


def test_각_테스트는_독립적이라_이전_테스트_데이터가_보이지_않는다(client):
    # Given: fixture가 또 다른 새 앱을 준비했다
    #        위의 테스트에서 연필을 추가했지만, 이 테스트의 client는 다른 앱이다

    # When
    response = client.get("/items/")

    # Then: 이전 테스트에서 추가한 연필이 없어야 한다
    assert response.json() == []


def test_없는_상품을_조회하면_404가_반환된다(client):
    # Given: 빈 상태

    # When
    response = client.get("/items/999")

    # Then
    assert response.status_code == 404


def test_상품을_삭제하면_이후_조회시_404가_반환된다(client):
    # Given: 상품을 먼저 생성
    client.post("/items/", json={"id": 1, "name": "연필", "price": 10.0})

    # When
    client.delete("/items/1")

    # Then
    assert client.get("/items/1").status_code == 404
