### user에 대한 CRUD / 인증 / 인가를 확인하는 테스트코드를 짜 보세요.
# pytest 00_pytest_basic.py -v -s --lf  # 성공한 테스트코드는 제외하고 실패했던 테스트코드만 돌립니다.
# pytest 00_pytest_basic.py -v -s --cache-clear # 기존 실패 테스트에 대한 내역을 삭제합니다.

# pip install pymysql sqlalchemy
from fastapi import FastAPI, HTTPException, status, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import create_engine, Column, Integer, String

# =========================================================================
# 1. 데이터베이스 베이스 및 모델 설정 (SQLAlchemy)
# =========================================================================
DATABASE_URL = "sqlite:///./test.db"  

# SQLAlchemy 엔진 생성
engine = create_engine(DATABASE_URL, echo=True, connect_args={"check_same_thread": False})

# 세션 생성기(SessionLocal)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 모든 데이터베이스 모델(테이블)이 상속받을 기본 클래스
Base = declarative_base()

# 데이터베이스 테이블 모양을 정의하는 클래스 (ORM Model)
class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    email = Column(String, unique=True, index=True)
    role = Column(String, default="user")

# 정의된 모델을 바탕으로 실제 DB 파일(test.db) 테이블을 생성합니다.
Base.metadata.create_all(bind=engine)

# =========================================================================
# 2. FastAPI 앱 및 Pydantic 데이터 검증 스키마 설정
# =========================================================================
app = FastAPI(title="ORM 실습", description="FastAPI와 SQLAlchemy를 이용한 ORM 실습")

class UserCreate(BaseModel):
    name: str = Field(..., description="사용자 이름")
    email: str = Field(..., description="사용자 이메일")
    role: str = Field("user", description="가입 역할 (기본: user)")

class UserUpdate(BaseModel):
    name: str | None = Field(None, description="수정할 이름")
    email: str | None = Field(None, description="수정할 이메일")
    role: str | None = Field(None, description="수정할 역할")

class UserResponse(BaseModel):
    id: int
    name: str
    email: str
    role: str

    model_config = {"from_attributes": True}


def get_db():
    db = SessionLocal()
    
    try:
        yield db  # try 안의 구문이 종료될 때까지 db에 대한 제어권을 코드에게 넘겨줌
    finally:
        db.close() 
        

# =========================================================================
# 4. CRUD 엔드포인트
# =========================================================================
@app.post("/users/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(user: UserCreate, db = Depends(get_db) ): # Depends 안에 선행(먼저 실행된 결과)를 객체로 받아서 create_user 안에서 사용
    """새로운 사용자를 생성합니다."""

    # 1) 이메일 중복 체크 
    existing_user = db.query(User).filter(User.email == user.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="이미 등록된 이메일입니다.")

    # 2) DB 모델 객체 생성 및 저장
    new_user = User(name=user.name, email=user.email, role=user.role)
    db.add(new_user)
    db.commit() # 실제 DB에 반영
    db.refresh(new_user) # 반영된 객체 정보를 새로고침(id 등 발급정보 갱신)
    
    return new_user


@app.get("/users/", response_model=list[UserResponse])
def read_users(skip: int = 0, limit: int = 10, db = Depends(get_db)):
    """전체 유저 목록을 페이징하여 조회합니다."""
    users = db.query(User).offset(skip).limit(limit).all()
    return users

@app.get("/users/{user_id}", response_model=UserResponse)
def read_user(user_id: int, db = Depends(get_db)):
    """특정 유저 단건 조회"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="없는 사용자입니다.")
    return user

@app.put("/users/{user_id}", response_model=UserResponse)
def update_user_all(user_id: int, user_req: UserCreate, db = Depends(get_db)):
    """유저 정보 강제 전체 수정 (put)"""
    existing_user = db.query(User).filter(User.id == user_id).first()
    if not existing_user:
        raise HTTPException(status_code=404, detail="없는 사용자입니다.")
        
    existing_user.name = user_req.name 
    existing_user.email = user_req.email 
    existing_user.role = user_req.role 
    
    db.commit()
    db.refresh(existing_user)
    return existing_user

@app.patch("/users/{user_id}", response_model=UserResponse)
def update_user_partial(user_id: int, user_req: UserUpdate, db = Depends(get_db)):
    """유저 정보 강제 전체 수정 (put)"""
    """유저 정보 일부만 수정 (patch)"""
    existing_user = db.query(User).filter(User.id == user_id).first()
    if not existing_user:
        raise HTTPException(status_code=404, detail="없는 사용자입니다.")
        
    # 클라이언트가 실제로 전송한 데이터(None이 아닌 수정할 값)만 딕셔너리로 추출합니다.
    update_data = user_req.model_dump(exclude_unset=True)
    
    # 추출한 데이터를 기존 유저 모델에 덮어씌웁니다.
    for key, value in update_data.items():
        setattr(existing_user, key, value)
        
    db.commit()
    db.refresh(existing_user)
    return existing_user

@app.delete("/users/{user_id}")
def delete_user(user_id: int, db = Depends(get_db)):
    """유저 삭제"""
    existing_user = db.query(User).filter(User.id == user_id).first()
    if not existing_user:
        raise HTTPException(status_code=404, detail="찾는 사용자가 없습니다.")
        
    db.delete(existing_user)
    db.commit()
    return {"message": f"{existing_user.name} 정보가 정상적으로 삭제되었습니다."}

# =========================================================================
# 5. 권한 실습 엔드포인트
# =========================================================================
@app.get('/validate/', response_model=UserResponse)
def get_current_user_endpoint(token: str, db = Depends(get_db)):
    user = db.query(User).filter(User.name == token).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="인증 정보가 유효하지 않습니다. (이름이 DB에 없습니다.)",
        )
    return user


                            ### 계층화: 작업 순서에 따라 비즈니스 로직만을 함수로 분리
@app.get("/admin")          # 1. get_db 로 db에 접속 
                            # -> 2. get_current_user_endpoint 로 token(username)이 db에 있는지 확인
                            # -> -> 3. read_admin_data 로 관리자 데이터에 접근 권한 부여
def read_admin_data(user = Depends(get_current_user_endpoint)):
    """관리자만 접근 가능한 비밀 엔드포인트"""
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="관리자 권한이 없습니다.",
        )
    return {"message": f"환영합니다 {user.name} 관리자님. 관리자용 데이터에 접근하셨습니다."}