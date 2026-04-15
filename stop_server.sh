#!/bin/bash

# FastAPI Boilerplate Server Stop Script
# 이 스크립트는 실행 중인 Gunicorn 서버를 안전하게 종료합니다.

set -e  # Exit on any error

echo "========================================"
echo "FastAPI Boilerplate Server Stop Script"
echo "========================================"

# 설정
PID_FILE="/tmp/gunicorn.pid"
TIMEOUT=30  # graceful shutdown 타임아웃 (초)
FORCE_TIMEOUT=10  # 강제 종료 대기 시간 (초)

# PID 파일 존재 확인
if [ ! -f "$PID_FILE" ]; then
    echo "Error: PID 파일을 찾을 수 없습니다: $PID_FILE"
    echo "서버가 실행 중이지 않거나 다른 방식으로 시작되었을 수 있습니다."
    echo ""
    echo "실행 중인 gunicorn 프로세스 확인:"
    if pgrep -f "gunicorn" > /dev/null; then
        echo "실행 중인 gunicorn 프로세스:"
        ps aux | grep gunicorn | grep -v grep
        echo ""
        echo "수동으로 종료하려면 다음 명령어를 사용하세요:"
        echo "  pkill -TERM gunicorn  # graceful shutdown"
        echo "  pkill -KILL gunicorn  # 강제 종료 (비추천)"
    else
        echo "실행 중인 gunicorn 프로세스가 없습니다."
    fi
    exit 1
fi

# PID 파일에서 PID 읽기
if ! PID=$(cat "$PID_FILE" 2>/dev/null); then
    echo "Error: PID 파일을 읽을 수 없습니다: $PID_FILE"
    exit 1
fi

echo "PID 파일에서 읽은 PID: $PID"

# PID 유효성 확인
if ! kill -0 "$PID" 2>/dev/null; then
    echo "Warning: PID $PID 프로세스가 존재하지 않습니다."
    echo "PID 파일을 정리합니다: $PID_FILE"
    rm -f "$PID_FILE"
    exit 0
fi

# 프로세스 이름 확인 (gunicorn인지 검증)
if ! ps -p "$PID" -o comm= | grep -q "gunicorn"; then
    echo "Error: PID $PID는 gunicorn 프로세스가 아닙니다."
    echo "현재 프로세스: $(ps -p "$PID" -o comm=)"
    exit 1
fi

echo "Gunicorn 마스터 프로세스 확인됨: PID $PID"
echo ""

# Graceful shutdown 시도 (SIGTERM)
echo "Graceful shutdown 시도 중... (최대 ${TIMEOUT}초 대기)"
kill -TERM "$PID"

# 종료 대기
COUNT=0
while [ $COUNT -lt $TIMEOUT ]; do
    if ! kill -0 "$PID" 2>/dev/null; then
        echo "서버가 정상적으로 종료되었습니다."
        rm -f "$PID_FILE"
        echo "PID 파일 정리 완료: $PID_FILE"
        exit 0
    fi

    echo -n "."
    sleep 1
    COUNT=$((COUNT + 1))
done

echo ""
echo "Graceful shutdown이 ${TIMEOUT}초 내에 완료되지 않았습니다."

# 강제 종료 시도 (SIGKILL)
echo "강제 종료 시도 중... (SIGKILL)"
kill -KILL "$PID" || true

# 강제 종료 대기
echo "강제 종료 대기 중... (최대 ${FORCE_TIMEOUT}초)"
COUNT=0
while [ $COUNT -lt $FORCE_TIMEOUT ]; do
    if ! kill -0 "$PID" 2>/dev/null; then
        echo "서버가 강제 종료되었습니다."
        rm -f "$PID_FILE"
        echo "PID 파일 정리 완료: $PID_FILE"
        exit 0
    fi

    echo -n "."
    sleep 1
    COUNT=$((COUNT + 1))
done

echo ""
echo "서버 종료 실패: 프로세스가 여전히 실행 중입니다."
echo "PID: $PID"
echo ""
echo "수동 조치 방법:"
echo "1. 프로세스 강제 종료: kill -9 $PID"
echo "2. 모든 gunicorn 프로세스 종료: pkill -9 gunicorn"
echo "3. 시스템 재부팅 고려"
exit 1
