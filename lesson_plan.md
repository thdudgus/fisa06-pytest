# 09. pytest로 FastAPI 테스트하기

> 목표: 실무에서 쓰는 API 테스트 패턴을 직접 작성하고 CI에 붙일 수 있는 수준 도달

---

## 왜 테스트를 배우는가?

- AI 백엔드에서 모델 추론 API는 입력/출력이 복잡 → 수동 검증에 한계
- 리팩토링·모델 교체 시 회귀(regression)를 자동으로 감지
- GitHub Actions 등 CI와 연동하면 push할 때마다 자동 검증

---

### Step 0 — pytest 기초 (`00_pytest_basic.py`)

**핵심 개념**
- `pytest` 설치 및 실행 (`pytest -v`)
- 테스트 함수 작명 규칙 (`test_` 접두사)
- `assert` 문으로 기댓값 검증
- 예외 테스트: `pytest.raises`

**실습 내용**
```
순수 파이썬 함수(사칙연산, 문자열 처리)에 대한 테스트 작성
→ 테스트가 실패하면 어떤 메시지가 나오는지 직접 확인
```

**파일**: `00_pytest_basic.py`

---

### Step 1 — FastAPI TestClient (`01_test_fastapi_crud.py`)

**핵심 개념**
- `httpx` 기반 `TestClient` (실제 서버 없이 API 호출)
- `GET` / `POST` / `PUT` / `DELETE` 엔드포인트 테스트
- 상태 코드·응답 JSON 검증

**실습 내용**
```
00_fastapi_basic의 CRUD API를 TestClient로 테스트
→ 정상 케이스 + 404/422 에러 케이스까지 작성
```

**파일**: `01_test_fastapi_crud.py`

---

### Step 2 — fixture로 테스트 격리 (`02_test_with_fixtures.py`)

**핵심 개념**
- `@pytest.fixture` — 공통 셋업/정리 코드 분리
- `scope` 옵션: `function` / `module` / `session`
- 인메모리 DB(`SQLite`)로 테스트 격리 (01_orm 연계)

**실습 내용**
```
ORM 기반 API를 테스트할 때 매 테스트마다 DB를 초기화하는 fixture 작성
→ 테스트 순서에 관계없이 독립적으로 동작하는 구조 완성
```

**파일**: `02_test_with_fixtures.py`

---

### Step 3 — 모델 서빙 API 테스트 (`03_test_model_serving.py`)

**핵심 개념**
- ML 추론 API의 입력 유효성·출력 범위 검증
- `pytest.mark.parametrize` — 여러 입력을 한 번에 테스트
- `monkeypatch` / `unittest.mock` — 모델 로딩을 모킹해 속도 향상

**실습 내용**
```
03_model_serving의 Iris 분류 API를 대상으로:
  - 정상 입력 → 0/1/2 중 하나인지 검증
  - 경계값·잘못된 입력 → 422 응답 확인
  - parametrize로 여러 샘플을 한꺼번에 검증
```

**파일**: `03_test_model_serving.py`

---

## 파일 구성 (예정)

```
09_testing/
├── lesson_plan.md          ← 이 파일
├── requirements.txt        ← pytest, httpx, pytest-anyio
├── 00_pytest_basic.py      ← Step 0: pytest 기초
├── 01_test_fastapi_crud.py ← Step 1: TestClient CRUD 테스트
├── 02_test_with_fixtures.py← Step 2: fixture + DB 격리
└── 03_test_model_serving.py← Step 3: ML 서빙 API 테스트
```

---

## 관련 모듈 연계

| 이 수업에서 테스트할 대상 | 원본 모듈 |
|--------------------------|-----------|
| CRUD API | `00_fastapi_basic` |
| ORM + 인증 API | `01_orm` |
| ML 추론 API | `03_model_serving` |

```
 pytest 00_pytest_basic.py -v -s  # print() 찍어놓은 코드는 출력합니다.
 pytest 00_pytest_basic.py -v -s --lf  # 성공한 테스트코드는 제외하고 실패했던 테스트코드만 돌립니다.
# pytest 00_pytest_basic.py -v -s --cache-clear # 기존 실패 테스트에 대한 내역을 삭제합니다.
```