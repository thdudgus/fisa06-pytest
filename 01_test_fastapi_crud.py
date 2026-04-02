# 실행: pytest 01_test_fastapi_crud.py -v
#       pytest 01_test_fastapi_crud.py -v -k "200"     : 함수명에 들어가는 특정 단어로 특정 테스트함수만 동작
# [Step 1] FastAPI TestClient — CRUD API 테스트
#
# TestClient: 실제 서버를 켜지 않고 API를 테스트할 수 있는 클라이언트
# (uvicorn 없이 테스트 코드 안에서 바로 HTTP 요청을 보낼 수 있다)

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from pydantic import BaseModel, Field

# ── 테스트 대상 앱 ─────────────────────────────────────────────────────────────

class Item(BaseModel):
    id: int
    name: str
    price: float = Field(..., gt=0)  # gt=0: 0보다 커야 한다

app = FastAPI()
items: list[Item] = [
    Item(id=1, name="연필", price=10.0),
    Item(id=2, name="공책", price=20.0),
]

@app.get("/items/{item_id}")
def read_item(item_id: int):
    for item in items:
        if item.id == item_id:
            return item
    raise HTTPException(status_code=404, detail="상품을 찾을 수 없습니다.")

@app.post("/items/", status_code=201)
def create_item(item: Item):
    items.append(item)
    return item

@app.delete("/items/{item_id}")
def delete_item(item_id: int):
    for idx, item in enumerate(items):
        if item.id == item_id:
            del items[idx]
            return {"message": "삭제되었습니다."}
    raise HTTPException(status_code=404, detail="상품을 찾을 수 없습니다.")


# ── TestClient 생성 ────────────────────────────────────────────────────────────

client = TestClient(app)


# ── 테스트 ────────────────────────────────────────────────────────────────────

def test_존재하는_상품을_조회하면_200과_상품정보가_반환된다():
    # Given: id=1 연필이 있는 상태

    # When
    response = client.get("/items/1")

    # Then
    assert response.status_code == 200
    assert response.json()["name"] == "연필"


def test_없는_상품을_조회하면_404가_반환된다():
    # Given: id=999 는 없다

    # When
    response = client.get("/items/999")

    # Then
    assert response.status_code == 404


def test_새_상품을_생성하면_201과_생성된_상품이_반환된다():
    # Given
    new_item = {"id": 99, "name": "지우개", "price": 5.0}

    # When
    response = client.post("/items/", json=new_item)

    # Then
    assert response.status_code == 201
    assert response.json()["name"] == "지우개"

    # 뒷정리: 다른 테스트에 영향을 주지 않도록 삭제
    client.delete("/items/99")


def test_가격이_음수이면_422가_반환된다():
    # Given: price가 음수 → Pydantic의 gt=0 제약 위반
    invalid_item = {"id": 100, "name": "잘못된상품", "price": -1.0}

    # When
    response = client.post("/items/", json=invalid_item)

    # Then: 422 = FastAPI가 요청 데이터 자체가 잘못됐을 때 자동으로 반환
    assert response.status_code == 422


def test_상품을_삭제하면_이후_조회시_404가_반환된다():
    # Given: 삭제할 상품을 먼저 생성
    client.post("/items/", json={"id": 50, "name": "임시상품", "price": 1.0})

    # When
    client.delete("/items/50")

    # Then: 삭제 후 조회하면 없어야 한다
    assert client.get("/items/50").status_code == 404
