#!/bin/bash
echo "[$(date)] Start docker-compose"

cd /home/capstone-design/Downloads/2025capstone || exit 1

docker-compose up -d torproxy curl-crawler

echo "[$(date)] docker-compose 완료"
