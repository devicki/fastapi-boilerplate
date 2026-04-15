#!/bin/bash

# FastAPI Boilerplate Server Startup Script
# 이 스크립트는 구성 파일과 함께 Gunicorn을 사용하여 FastAPI 애플리케이션을 시작합니다.

set -e  # Exit on any error

echo "========================================"
echo "FastAPI Boilerplate Server Startup Script"
echo "========================================"

# 이 스크립트가 있는 디렉터리를 가져옵니다.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo "Script directory: $SCRIPT_DIR"

# 프로젝트 루트 디렉터리로 변경
cd "$SCRIPT_DIR"
echo "Changed to project root: $(pwd)"

# Gunicorn을 사용할 수 있는지 확인하세요.
if ! command -v gunicorn &> /dev/null; then
    echo "Error: gunicorn is not installed or not in PATH"
    exit 1
fi

# 구성 파일이 있는지 확인
if [ ! -f "gunicorn.conf.py" ]; then
    echo "Error: gunicorn.conf.py configuration file not found"
    exit 1
fi

# 환경 변수 설정 - .env 파일에서 로드
if [ -f ".env" ]; then
    echo ".env에서 환경 변수 로드 중..."
    set -a
    source .env
    set +a
    echo "환경 변수 로드 완료"
else
    echo "Warning: .env 파일이 없습니다. 기본 환경변수를 사용합니다."
fi

# 서버 포트 확인 및 기존 서버 종료
# gunicorn.conf.py에서 bind 설정에서 포트 추출
if [ -f "gunicorn.conf.py" ]; then
    # bind = "0.0.0.0:8000" 형식에서 포트 번호 추출
    SERVER_PORT=$(grep '^bind.*=' gunicorn.conf.py | sed 's/.*://' | sed 's/".*//' | tr -d '\n\r')
    if [ -z "$SERVER_PORT" ] || ! [[ "$SERVER_PORT" =~ ^[0-9]+$ ]]; then
        echo "Warning: gunicorn.conf.py에서 포트를 찾을 수 없습니다. 기본값 8000을 사용합니다."
        SERVER_PORT="8000"
    fi
else
    echo "Warning: gunicorn.conf.py 파일을 찾을 수 없습니다. 기본값 8000을 사용합니다."
    SERVER_PORT="8000"
fi

echo "포트 $SERVER_PORT 사용 가능 여부 확인 중..."

# 포트가 사용 중인지 확인
if command -v ss &> /dev/null; then
    PORT_CHECK_CMD="ss -tlnp | grep :$SERVER_PORT"
elif command -v netstat &> /dev/null; then
    PORT_CHECK_CMD="netstat -tlnp | grep :$SERVER_PORT"
else
    echo "Warning: ss 또는 netstat 명령어를 찾을 수 없습니다. 포트 확인을 건너뜁니다."
    PORT_CHECK_CMD=""
fi

if [ -n "$PORT_CHECK_CMD" ] && eval "$PORT_CHECK_CMD" > /dev/null; then
    echo "포트 $SERVER_PORT이(가) 이미 사용 중입니다."
    echo "기존 서버를 종료하고 새로 시작합니다..."

    # 기존 서버 프로세스 찾기 및 종료
    echo "기존 gunicorn/uvicorn 프로세스 종료 중..."

    # 1. gunicorn 프로세스 종료 시도 (PID 파일 기반)
    if [ -f "/tmp/gunicorn.pid" ]; then
        if PID=$(cat "/tmp/gunicorn.pid" 2>/dev/null) && kill -0 "$PID" 2>/dev/null; then
            echo "gunicorn PID 파일 발견: $PID"
            kill -TERM "$PID" 2>/dev/null || true

            # 종료 대기 (최대 10초)
            COUNT=0
            while [ $COUNT -lt 10 ] && kill -0 "$PID" 2>/dev/null; do
                sleep 1
                COUNT=$((COUNT + 1))
            done

            if kill -0 "$PID" 2>/dev/null; then
                echo "강제 종료 시도..."
                kill -KILL "$PID" 2>/dev/null || true
                sleep 2
            fi
        fi
        rm -f "/tmp/gunicorn.pid"
    fi

    # 2. 포트 기반 프로세스 종료 (uvicorn 등 다른 서버 포함)
    if eval "$PORT_CHECK_CMD" > /dev/null; then
        echo "포트 $SERVER_PORT을 사용하는 프로세스 강제 종료..."
        # 포트를 사용하는 프로세스의 PID 찾기
        if command -v ss &> /dev/null; then
            PORT_PID=$(ss -tlnp | grep :$SERVER_PORT | grep -o 'pid=[0-9]*' | cut -d'=' -f2 | head -1)
        elif command -v netstat &> /dev/null; then
            PORT_PID=$(netstat -tlnp | grep :$SERVER_PORT | awk '{print $7}' | cut -d'/' -f1 | head -1)
        fi

        if [ -n "$PORT_PID" ] && [ "$PORT_PID" != "-" ]; then
            echo "포트 $SERVER_PORT을 사용하는 프로세스 발견: PID $PORT_PID"
            kill -TERM "$PORT_PID" 2>/dev/null || true
            sleep 3

            if kill -0 "$PORT_PID" 2>/dev/null; then
                echo "강제 종료 시도..."
                kill -KILL "$PORT_PID" 2>/dev/null || true
                sleep 2
            fi
        fi
    fi

    # 3. 남은 gunicorn/uvicorn 프로세스 정리
    if pgrep -f "gunicorn.*app.main:app" > /dev/null; then
        echo "남은 gunicorn 프로세스 정리..."
        pkill -TERM -f "gunicorn.*app.main:app" 2>/dev/null || true
        sleep 2
        pkill -KILL -f "gunicorn.*app.main:app" 2>/dev/null || true
    fi

    if pgrep -f "uvicorn.*app.main:app" > /dev/null; then
        echo "남은 uvicorn 프로세스 정리..."
        pkill -TERM -f "uvicorn.*app.main:app" 2>/dev/null || true
        sleep 2
        pkill -KILL -f "uvicorn.*app.main:app" 2>/dev/null || true
    fi

    echo "기존 서버 종료 완료"
else
    echo "포트 $SERVER_PORT이(가) 사용 가능합니다."
fi

# 시작 정보 표시
echo "Python version: $(python --version)"
echo "Gunicorn version: $(gunicorn --version)"
echo "Configuration file: gunicorn.conf.py"
echo "Application module: app.main:app"
echo ""

# Start Gunicorn server
echo "Starting Gunicorn server..."
echo "=========================================="

# 개발 편의: 코드 변경 시 자동 reload (운영에서는 비활성 권장)
# - ENABLE_RELOAD=true 인 경우 gunicorn --reload 사용
# - --reload 사용 시 다중 워커는 예측 불가하므로 workers=1로 강제
GUNICORN_CMD=(gunicorn -c gunicorn.conf.py app.main:app)
if [ "${ENABLE_RELOAD:-false}" = "true" ]; then
    echo "Reload enabled (ENABLE_RELOAD=true). Gunicorn will auto-reload on code changes."
    GUNICORN_CMD+=(--reload --workers 1)
fi

# gunicorn을 백그라운드에서 실행
"${GUNICORN_CMD[@]}" &
GUNICORN_PID=$!

# 서버가 실행 중인지 확인하는 함수
wait_for_server() {
    local max_attempts=30  # 최대 30초 대기
    local attempt=1

    echo "서버 시작 대기 중..."
    while [ $attempt -le $max_attempts ]; do
        if kill -0 $GUNICORN_PID 2>/dev/null; then
            echo "서버가 성공적으로 시작되었습니다 (PID: $GUNICORN_PID)"
            return 0
        fi
        sleep 1
        attempt=$((attempt + 1))
    done

    echo "서버 시작 실패"
    return 1
}

# 서버 시작 대기
if wait_for_server; then
    echo "=========================================="
    echo "서버가 실행 중입니다. 중지하려면 Ctrl+C를 누르세요."
    echo "=========================================="

    # SIGINT (Ctrl+C) 핸들러
    cleanup() {
        echo ""
        echo "서버 종료 중..."

        # Gunicorn 서버 종료
        if kill -0 $GUNICORN_PID 2>/dev/null; then
            kill -TERM $GUNICORN_PID 2>/dev/null || true

            # 종료 대기
            local count=0
            while [ $count -lt 10 ] && kill -0 $GUNICORN_PID 2>/dev/null; do
                sleep 1
                count=$((count + 1))
            done

            if kill -0 $GUNICORN_PID 2>/dev/null; then
                echo "강제 종료 시도..."
                kill -KILL $GUNICORN_PID 2>/dev/null || true
            fi
        fi

        echo "서버가 종료되었습니다."
        exit 0
    }

    # SIGINT 트랩 설정
    trap cleanup SIGINT SIGTERM

    # 서버가 종료될 때까지 대기
    wait $GUNICORN_PID 2>/dev/null || true

    # 정상 종료 시에도 cleanup 실행
    cleanup
else
    echo "서버 시작에 실패했습니다."

    exit 1
fi
