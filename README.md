# FastAPI Boilerplate

JWT 인증, Redis 캐싱, PostgreSQL을 포함한 재사용 가능한 FastAPI 보일러플레이트입니다.

## 기술 스택

| 구분 | 기술 |
|------|------|
| Framework | FastAPI 0.115 + Uvicorn |
| Server | Gunicorn (UvicornWorker) |
| Database | PostgreSQL + SQLAlchemy 2.0 ORM |
| Auth | JWT (HS256), Cookie 기반 토큰 |
| Cache | Redis 7.1 (토큰 블랙리스트, 세션) |
| Password | Argon2id (argon2-cffi) |
| Validation | Pydantic 2.9 |
| Logging | concurrent-log-handler (멀티프로세스 안전) |

## 아키텍처

4계층 클린 아키텍처:

```
Request → Endpoint → Service → Repository → Model (DB)
```

- **Endpoint** (`app/api/v1/endpoints/`): HTTP 요청 처리, 입력 검증, 권한 체크
- **Service** (`app/services/`): 비즈니스 로직, 트랜잭션 관리
- **Repository** (`app/repositories/`): 데이터 액세스 레이어 (CRUD)
- **Model** (`app/databases/`): SQLAlchemy ORM 모델

## 디렉토리 구조

```
app/
  api/v1/
    endpoints/          # API 엔드포인트
      auth.py           # 인증 (로그인/회원가입/로그아웃/토큰갱신)
      users.py          # 사용자 CRUD (Sample)
    routers/
      entry.py          # v1 라우터 등록
    schemas/            # Pydantic 스키마
      auth.py
      user.py
      common_validators.py
      common/request_filter.py
  constants/
    filter_items.py     # 필터 관련 상수
  core/
    logging.py          # 멀티프로세스 로깅 설정
  databases/
    models.py           # SQLAlchemy ORM 모델
    redis.py            # Redis 클라이언트 (싱글톤, 메모리 폴백)
    session.py          # DB 세션 관리, 커넥션 풀링
  repositories/         # 데이터 액세스 레이어
    auth/
    users/
  services/             # 비즈니스 로직 레이어
    auth/
    users/
  utils/                # 공통 유틸리티
    cache_manager.py    # Redis 캐시 관리자
    date_utils.py       # 날짜/시간 유틸
    error_class.py      # 커스텀 에러 코드/예외
    error_handler.py    # 글로벌 에러 핸들러
    file_utils.py       # 파일 업로드/다운로드
    jwt_utils.py        # JWT 토큰 관리
    pagination.py       # 페이지네이션
    password_policy.py  # 비밀번호 정책 검증
    password_utils.py   # Argon2 비밀번호 해싱
    path_utils.py       # 경로 유틸
    response_utils.py   # 표준 API 응답 포맷
    types.py            # 공통 타입 정의
    filter_utils/       # 필터링 (정렬/검색/날짜/선택)
  main.py               # FastAPI 앱 초기화
```

## 시작하기

### 사전 요구사항

- Python 3.13+
- PostgreSQL
- Redis (선택, 없으면 메모리 폴백)

### 설치 및 실행

```bash
# 1. 의존성 설치
pip install -r requirements.txt

# 2. 환경변수 설정
cp .env .env.local  # .env.local에서 DB 접속 정보 등 수정

# 3. 개발 서버 실행
uvicorn app.main:app --reload --port 8088

# 또는 Gunicorn으로 실행
gunicorn -c gunicorn.conf.py app.main:app
```

### 개발 도구 설치

```bash
pip install -r requirements-dev.txt
pre-commit install
```

## 환경 변수 (.env)

| 변수 | 설명 | 기본값 |
|------|------|--------|
| `DB_HOST` | PostgreSQL 호스트 | `localhost` |
| `DB_PORT` | PostgreSQL 포트 | `5432` |
| `DB_USER` | DB 사용자 | `postgres` |
| `DB_PASSWORD` | DB 비밀번호 | `password` |
| `DB_SERVICE_NAME` | DB 이름 | `app_db` |
| `REDIS_HOST` | Redis 호스트 | `localhost` |
| `JWT_SECRET_KEY` | JWT 시크릿 키 | (필수 변경) |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | 액세스 토큰 만료(분) | `60` |
| `LOCAL_ENABLE_AUTO_LOGIN` | 개발 자동 로그인 | `true` |
| `APP_TIMEZONE` | 앱 타임존 | `UTC` |

## API 엔드포인트

### 인증 (`/api/v1/auth`)

| Method | Path | 설명 |
|--------|------|------|
| POST | `/signup` | 회원가입 |
| POST | `/login` | 로그인 (JWT 쿠키 발급) |
| POST | `/refresh` | 토큰 갱신 |
| POST | `/logout` | 로그아웃 (토큰 블랙리스트) |
| GET | `/me` | 현재 사용자 정보 |
| PUT | `/password` | 비밀번호 변경 |

### 사용자 Sample (`/api/v1/users`)

| Method | Path | 설명 |
|--------|------|------|
| GET | `/list` | 전체 조회 (페이지네이션, 필터링) |
| GET | `/by-id` | 단건 조회 |
| POST | `/create` | 생성 |
| PUT | `/update` | 수정 |
| DELETE | `/delete` | 삭제 |

## 새 모듈 추가 방법

`users` 샘플을 참고하여 새 도메인 모듈을 추가합니다:

1. **Model**: `app/databases/models.py`에 SQLAlchemy 모델 추가
2. **Schema**: `app/api/v1/schemas/` 에 Pydantic 스키마 생성
3. **Repository**: `app/repositories/<module>/` 에 데이터 액세스 클래스 생성
4. **Service**: `app/services/<module>/` 에 비즈니스 로직 클래스 생성
5. **Endpoint**: `app/api/v1/endpoints/` 에 라우터 생성
6. **Router 등록**: `app/api/v1/routers/entry.py`에 라우터 추가

### 핵심 패턴

```python
# Service: 트랜잭션 관리
with service.transaction():
    result = service.create_item(data)

# Repository: flush만 사용 (commit은 Service 레벨)
self.db.add(model)
self.db.flush()

# Endpoint: 의존성 주입
@router.get("/list")
def get_items(
    current_user = Depends(check_permission("items")),
    db: Session = Depends(get_db),
):
    ...
```

## 주요 기능

- **JWT 인증**: 쿠키 기반 Access/Refresh 토큰, 블랙리스트 로그아웃
- **역할 기반 권한**: admin/user 역할로 CRUD 권한 분리
- **Redis 캐싱**: 싱글톤 패턴, Redis 미연결 시 메모리 폴백
- **필터링 시스템**: 날짜 범위, 정렬, 검색, 선택 필터 지원
- **표준 응답 포맷**: 통일된 JSON 응답 구조 + 페이지네이션
- **에러 핸들링**: 커스텀 에러 코드, 글로벌 핸들러, 트레이스백 로깅
- **비밀번호 정책**: Argon2id 해싱, 복잡도 검증 (길이, 문자종류, 연속문자)
- **멀티프로세스 로깅**: Gunicorn 워커 간 안전한 로그 파일 관리
- **SQL 디버깅**: 파라미터 바인딩된 실행 SQL 로깅 (개발 모드)
