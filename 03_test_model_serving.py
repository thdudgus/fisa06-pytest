# 실행: pytest 03_test_model_serving.py -v
# pytest 00_pytest_basic.py -v -s --lf  # 성공한 테스트코드는 제외하고 실패했던 테스트코드만 돌립니다.
# pytest 00_pytest_basic.py -v -s --cache-clear # 기존 실패 테스트에 대한 내역을 삭제합니다.
# [Step 3] ML 모델 서빙 API 테스트
#
# ▶ 두 가지 핵심 기법
#   1. MagicMock : 실제 모델 파일 없이 모델을 가짜로 교체
#   2. parametrize: 여러 입력 케이스를 테이블처럼 한 번에 테스트

import pytest
import numpy as np
from unittest.mock import MagicMock
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel, Field


# ── 테스트 대상 앱 ─────────────────────────────────────────────────────────────

class IrisInput(BaseModel):
    sepal_length: float = Field(..., gt=0)
    sepal_width:  float = Field(..., gt=0)
    petal_length: float = Field(..., gt=0)
    petal_width:  float = Field(..., gt=0)

app = FastAPI()
app.state.model = None  # 테스트에서 Mock으로 교체할 슬롯

TARGET_NAMES = ["setosa", "versicolor", "virginica"]

@app.post("/predict")
def predict(data: IrisInput):
    if app.state.model is None:
        return {"error": "모델이 없습니다."}
    features = np.array([[data.sepal_length, data.sepal_width,
                          data.petal_length, data.petal_width]])
    idx = int(app.state.model.predict_from_model(features)[0])
    return {"class_id": idx, "class_name": TARGET_NAMES[idx]}


# ── fixture ───────────────────────────────────────────────────────────────────
# given: 함수에 들어갈 입력값을 준비
@pytest.fixture
def client():
    """
    MagicMock을 모델로 주입한 TestClient를 반환한다.

    MagicMock: 어떤 메서드를 호출해도 에러 없이 동작하는 가짜 객체.
    mock.predict.return_value 를 바꾸면 원하는 값을 반환하게 제어할 수 있다.
    """
    mock = MagicMock() # 모델 대신 입력과 출력을 확인할 블랙박스
    mock.predict_from_model.return_value = np.array([0])  # 함수의 리턴값: 기본값: setosa
    app.state.model = mock
    yield TestClient(app)
    app.state.model = None # None을 되돌려 놓을 겁니다.


# ── 기본 테스트 ───────────────────────────────────────────────────────────────

def test_정상_입력으로_요청하면_200과_예측_결과가_반환된다(client):
    # Given: Mock 모델이 주입된 상태 (기본 반환값: class 0 = setosa)
    payload = {"sepal_length": 3.2, "sepal_width": 3.5,
               "petal_length": 1.4, "petal_width": 0.2}

    # When
    response = client.post("/predict", json=payload)

    # Then
    assert response.status_code == 200
    assert response.json()["class_id"] == 0
    assert response.json()["class_name"] == "setosa"


# ── parametrize: 여러 케이스를 한 번에 ────────────────────────────────────────
# 아래 리스트의 각 행이 독립적인 테스트 케이스가 된다.
# pytest -v 실행 시 케이스별로 이름이 따로 출력되어 어디서 실패했는지 바로 알 수 있다.

@pytest.mark.parametrize("mock_class_id, expected_name", [
    (0, "setosa"),
    (1, "versicolor"),
    (2, "virginica"),
])
def test_Mock_반환값에_따라_올바른_품종명이_응답된다(client, mock_class_id, expected_name):
    # Given: Mock이 mock_class_id를 반환하도록 설정
    app.state.model.predict_from_model.return_value = np.array([mock_class_id])

    # When
    # 이렇게 입력값을 넘겨줄 때
    response = client.post("/predict", json={
        "sepal_length": 5.1, "sepal_width": 3.5,
        "petal_length": 1.4, "petal_width": 0.2,
    })

    # Then
    assert response.json()["class_id"] == mock_class_id
    assert response.json()["class_name"] == expected_name


# ── 유효성 검사 실패 ──────────────────────────────────────────────────────────

def test_음수_입력값은_422가_반환된다(client):
    # Given: sepal_length 가 음수 (gt=0 위반)
    payload = {"sepal_length": -1.0, "sepal_width": 3.5,
               "petal_length": 1.4, "petal_width": 0.2}

    # When
    response = client.post("/predict", json=payload)

    # Then: Pydantic이 자동으로 422 반환
    assert response.status_code == 422


def test_필드가_누락되면_422가_반환된다(client):
    # Given: petal_width 없음
    payload = {"sepal_length": 5.1, "sepal_width": 3.5, "petal_length": 1.4}

    # When
    response = client.post("/predict", json=payload)

    # Then
    assert response.status_code == 422
