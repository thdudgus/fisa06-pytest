# 실행: pytest test_05_depends_example.py -v -s
#       pytest test_05_depends_example.py -v -s --lf   # 실패한 테스트만 재실행
#       pytest test_05_depends_example.py -v -s --cache-clear

import pytest
from unittest.mock import MagicMock
from fastapi.testclient import TestClient
from depends_example import app, get_db, get_current_user_endpoint, User


# ── 헬퍼: 세션 없이 User ORM 인스턴스 생성 ─────────────────────────────────────

def make_user(id=1, name="테스트유저", email="test@example.com", role="user"):
    """
    Pydantic UserResponse (from_attributes=True) 가 직렬화할 수 있다.
    """
    user = User()
    user.id    = id
    user.name  = name
    user.email = email
    user.role  = role
    return user


# ── Fixture ──────────────────────────────────────────────────────────────────

@pytest.fixture
def mock_db():
    """매 테스트마다 새 MagicMock DB 세션을 주입하고, 테스트 후 override를 제거한다."""
    db = MagicMock()
    app.dependency_overrides[get_db] = lambda: db
    yield db
    app.dependency_overrides.clear()


client = TestClient(app)


# =========================================================================
# 1. POST /users/ — create_user
# =========================================================================

def test_새_유저를_생성하면_201과_유저정보가_반환된다(mock_db):
    # Given: 중복 이메일 없음 / refresh 시 id 주입
    mock_db.query.return_value.filter.return_value.first.return_value = None
    # db.query().filter(user.email == email).first()
    def set_id(u):
        u.id = 1
    mock_db.refresh.side_effect = set_id

    # When
    response = client.post("/users/", json={
        "name": "테스트유저",
        "email": "test@example.com",
        "role": "user",
    })

    # Then
    assert response.status_code == 201
    data = response.json()
    assert data["name"]  == "테스트유저"
    assert data["email"] == "test@example.com"
    mock_db.add.assert_called_once()
    mock_db.commit.assert_called_once()
    mock_db.refresh.assert_called_once()


def test_중복_이메일로_생성하면_400이_반환된다(mock_db):
    # Given: 동일 이메일 유저가 이미 존재
    mock_db.query.return_value.filter.return_value.first.return_value = make_user()

    # When
    response = client.post("/users/", json={
        "name": "다른사람",
        "email": "test@example.com",
        "role": "user",
    })

    # Then
    assert response.status_code == 400
    assert "이미 등록된 이메일" in response.json()["detail"]
    mock_db.add.assert_not_called()


# =========================================================================
# 2. GET /users/ — read_users
# =========================================================================

def test_유저_목록을_조회하면_200과_리스트가_반환된다(mock_db):
    # Given
    user_list = [make_user(id=1), make_user(id=2, name="두번째", email="b@b.com")]
    mock_db.query.return_value.offset.return_value.limit.return_value.all.return_value = user_list

    # When
    response = client.get("/users/")

    # Then
    assert response.status_code == 200
    assert len(response.json()) == 2


def test_유저가_없으면_빈_리스트가_반환된다(mock_db):
    # Given
    mock_db.query.return_value.offset.return_value.limit.return_value.all.return_value = []

    # When
    response = client.get("/users/")

    # Then
    assert response.status_code == 200
    assert response.json() == []


def test_skip과_limit_파라미터가_DB_쿼리에_전달된다(mock_db):
    # Given
    mock_db.query.return_value.offset.return_value.limit.return_value.all.return_value = []

    # When
    client.get("/users/?skip=5&limit=3")

    # Then: offset(5), limit(3) 순으로 호출됐는지 확인
    mock_db.query.return_value.offset.assert_called_once_with(5)
    mock_db.query.return_value.offset.return_value.limit.assert_called_once_with(3)


# =========================================================================
# 3. GET /users/{user_id} — read_user
# =========================================================================

def test_존재하는_유저를_단건_조회하면_200과_유저정보가_반환된다(mock_db):
    # Given
    mock_db.query.return_value.filter.return_value.first.return_value = make_user()

    # When
    response = client.get("/users/1")

    # Then
    assert response.status_code == 200
    assert response.json()["id"] == 1


def test_없는_유저를_단건_조회하면_404가_반환된다(mock_db):
    # Given
    mock_db.query.return_value.filter.return_value.first.return_value = None

    # When
    response = client.get("/users/999")

    # Then
    assert response.status_code == 404
    assert "없는 사용자" in response.json()["detail"]


# =========================================================================
# 4. PUT /users/{user_id} — update_user_all (전체 수정)
# =========================================================================

def test_전체_수정하면_200과_수정된_유저가_반환된다(mock_db):
    # Given
    existing = make_user(name="원래이름", email="old@old.com", role="user")
    mock_db.query.return_value.filter.return_value.first.return_value = existing

    # When
    response = client.put("/users/1", json={
        "name": "새이름",
        "email": "new@new.com",
        "role": "admin",
    })

    # Then
    assert response.status_code == 200
    assert existing.name  == "새이름"
    assert existing.email == "new@new.com"
    assert existing.role  == "admin"
    mock_db.commit.assert_called_once()
    mock_db.refresh.assert_called_once()


def test_없는_유저를_전체_수정하면_404가_반환된다(mock_db):
    # Given
    mock_db.query.return_value.filter.return_value.first.return_value = None

    # When
    response = client.put("/users/999", json={
        "name": "이름",
        "email": "a@a.com",
        "role": "user",
    })

    # Then
    assert response.status_code == 404


# =========================================================================
# 5. PATCH /users/{user_id} — update_user_partial (부분 수정)
# =========================================================================

def test_이름만_수정하면_나머지_필드는_변경되지_않는다(mock_db):
    # Given
    existing = make_user(name="원래이름", email="keep@keep.com", role="user")
    mock_db.query.return_value.filter.return_value.first.return_value = existing

    # When: name 만 보냄
    response = client.patch("/users/1", json={"name": "새이름"})

    # Then
    assert response.status_code == 200
    assert existing.name  == "새이름"
    assert existing.email == "keep@keep.com"   # 변경되지 않아야 함
    assert existing.role  == "user"             # 변경되지 않아야 함


def test_email과_role만_수정하면_name은_변경되지_않는다(mock_db):
    # Given
    existing = make_user(name="유지될이름", email="old@old.com", role="user")
    mock_db.query.return_value.filter.return_value.first.return_value = existing

    # When
    response = client.patch("/users/1", json={"email": "new@new.com", "role": "admin"})

    # Then
    assert response.status_code == 200
    assert existing.name  == "유지될이름"  # 변경되지 않아야 함
    assert existing.email == "new@new.com"
    assert existing.role  == "admin"


def test_없는_유저를_부분_수정하면_404가_반환된다(mock_db):
    # Given
    mock_db.query.return_value.filter.return_value.first.return_value = None

    # When
    response = client.patch("/users/999", json={"name": "아무개"})

    # Then
    assert response.status_code == 404


# =========================================================================
# 6. DELETE /users/{user_id} — delete_user
# =========================================================================

def test_유저를_삭제하면_200과_삭제_메시지가_반환된다(mock_db):
    # Given
    existing = make_user(name="삭제될유저")
    mock_db.query.return_value.filter.return_value.first.return_value = existing

    # When
    response = client.delete("/users/1")

    # Then
    assert response.status_code == 200
    assert "삭제될유저" in response.json()["message"]
    mock_db.delete.assert_called_once_with(existing)
    mock_db.commit.assert_called_once()


def test_없는_유저를_삭제하면_404가_반환된다(mock_db):
    # Given
    mock_db.query.return_value.filter.return_value.first.return_value = None

    # When
    response = client.delete("/users/999")

    # Then
    assert response.status_code == 404
    assert "찾는 사용자가 없습니다" in response.json()["detail"]
    mock_db.delete.assert_not_called()


# =========================================================================
# 7. GET /validate/ — get_current_user_endpoint (인증)
# =========================================================================

def test_유효한_토큰이면_200과_유저정보가_반환된다(mock_db):
    # Given: token 과 일치하는 이름을 가진 유저가 DB에 존재
    mock_db.query.return_value.filter.return_value.first.return_value = make_user(name="홍길동")

    # When
    response = client.get("/validate/?token=홍길동")

    # Then
    assert response.status_code == 200
    assert response.json()["name"] == "홍길동"


def test_유효하지_않은_토큰이면_401이_반환된다(mock_db):
    # Given: DB에 해당 이름 없음
    mock_db.query.return_value.filter.return_value.first.return_value = None

    # When
    response = client.get("/validate/?token=없는사람")

    # Then
    assert response.status_code == 401
    assert "인증 정보가 유효하지 않습니다" in response.json()["detail"]


# =========================================================================
# 8. GET /admin — read_admin_data (인가)
# =========================================================================

def test_admin_role_유저는_관리자_데이터에_접근할_수_있다():
    # Given: get_current_user_endpoint 를 직접 override → admin 유저 반환
    admin = make_user(name="관리자", role="admin")
    app.dependency_overrides[get_current_user_endpoint] = lambda token, db=None: admin

    try:
        # When
        response = client.get("/admin?token=관리자")

        # Then
        assert response.status_code == 200
        assert "관리자" in response.json()["message"]
    finally:
        app.dependency_overrides.clear()


def test_user_role_유저는_관리자_데이터에_접근하면_403이_반환된다():
    # Given: get_current_user_endpoint → 일반 user 반환
    normal_user = make_user(name="일반유저", role="user")
    app.dependency_overrides[get_current_user_endpoint] = lambda token, db=None: normal_user

    try:
        # When
        response = client.get("/admin?token=일반유저")

        # Then
        assert response.status_code == 403
        assert "관리자 권한이 없습니다" in response.json()["detail"]
    finally:
        app.dependency_overrides.clear()


def test_유효하지_않은_토큰으로_관리자_접근시_401이_반환된다(mock_db):
    # Given: validate 단계에서 DB에 해당 이름 없음 (get_current_user_endpoint 는 override 안 함)
    mock_db.query.return_value.filter.return_value.first.return_value = None

    # When
    response = client.get("/admin?token=모르는사람")

    # Then: validate → 401로 차단
    assert response.status_code == 401
