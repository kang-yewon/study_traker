"""
SQLite 데이터베이스 관리 모듈
- study_record 테이블 생성/조회/저장
- 모든 시간은 분(minute) 단위로 저장
"""
import sqlite3
import os
from datetime import datetime, timedelta
# DB 파일 경로 (이 파일과 같은 폴더의 study.db)
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "study.db")
# 과목 컬럼 리스트 (앱 전체에서 이 순서/이름을 사용)
SUBJECTS = ["korean", "english", "math", "science", "social"]
# 과목 표시 이름 (한글)
SUBJECT_LABELS = {
    "korean": "국어",
    "english": "영어",
    "math": "수학",
    "science": "과학",
    "social": "사회",
}
# 과목 색상 (Home 도넛, Stats 스택바 공통)
SUBJECT_COLORS = {
    "korean": "#4A90E2",
    "english": "#2ECC71",
    "math": "#F39C12",
    "science": "#9B59B6",
    "social": "#F1C40F",
}
def _connect():
    """SQLite 연결 반환"""
    return sqlite3.connect(DB_PATH)
def init_db():
    """앱 시작 시 테이블이 없으면 생성"""
    conn = _connect()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS study_record (
                date TEXT PRIMARY KEY,
                korean INTEGER NOT NULL DEFAULT 0,
                english INTEGER NOT NULL DEFAULT 0,
                math INTEGER NOT NULL DEFAULT 0,
                science INTEGER NOT NULL DEFAULT 0,
                social INTEGER NOT NULL DEFAULT 0
            )
            """
        )
        conn.commit()
    finally:
        conn.close()
def today_str():
    """오늘 날짜 문자열 (YYYY-MM-DD)"""
    return datetime.now().strftime("%Y-%m-%d")
def get_record(date_str):
    """
    특정 날짜 기록 반환.
    없으면 모든 과목 0인 dict 반환.
    """
    conn = _connect()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT korean, english, math, science, social "
            "FROM study_record WHERE date = ?",
            (date_str,),
        )
        row = cur.fetchone()
    finally:
        conn.close()
    if row is None:
        return {s: 0 for s in SUBJECTS}
    return dict(zip(SUBJECTS, row))
def save_record(date_str, minutes_dict):
    """
    기록 저장 (없으면 INSERT, 있으면 UPDATE = 덮어쓰기)
    minutes_dict: {"korean": 90, "english": 30, ...}
    """
    # 누락 과목은 0으로 채움
    values = [int(minutes_dict.get(s, 0)) for s in SUBJECTS]
    conn = _connect()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO study_record (date, korean, english, math, science, social)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(date) DO UPDATE SET
                korean = excluded.korean,
                english = excluded.english,
                math = excluded.math,
                science = excluded.science,
                social = excluded.social
            """,
            (date_str, *values),
        )
        conn.commit()
    finally:
        conn.close()
def get_total_all_time():
    """전체 누적 (총합, 과목별 dict) 반환. 단위: 분"""
    conn = _connect()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT "
            "COALESCE(SUM(korean),0), COALESCE(SUM(english),0), "
            "COALESCE(SUM(math),0), COALESCE(SUM(science),0), "
            "COALESCE(SUM(social),0) "
            "FROM study_record"
        )
        row = cur.fetchone()
    finally:
        conn.close()
    per_subject = dict(zip(SUBJECTS, row))
    total = sum(per_subject.values())
    return total, per_subject
def get_records_in_range(start_date_str, end_date_str):
    """
    [start, end] 구간의 기록 리스트 반환.
    반환: [{"date": "YYYY-MM-DD", "korean": ..., ...}, ...] (날짜 오름차순)
    """
    conn = _connect()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT date, korean, english, math, science, social "
            "FROM study_record WHERE date BETWEEN ? AND ? ORDER BY date ASC",
            (start_date_str, end_date_str),
        )
        rows = cur.fetchall()
    finally:
        conn.close()
    result = []
    for r in rows:
        item = {"date": r[0]}
        item.update(dict(zip(SUBJECTS, r[1:])))
        result.append(item)
    return result
# database.py 내의 format_minutes 함수만 아래와 같이 수정하세요.
def format_minutes(minutes):
    """분(int) -> '3h 30m' 형식 문자열로 변경"""
    minutes = int(minutes)
    h = minutes // 60
    m = minutes % 60
    if h > 0 and m > 0:
        return f"{h}h {m}m"
    if h > 0:
        return f"{h}h"
    return f"{m}m"
def date_range(period):
    """
    통계 화면용 기간 계산.
    period: "day" | "week" | "month" | "year"
    반환: (start_date_str, end_date_str)
    """
    today = datetime.now().date()
    if period == "day":
        start = today
    elif period == "week":
        start = today - timedelta(days=6)   # 오늘 포함 7일
    elif period == "month":
        start = today - timedelta(days=29)  # 오늘 포함 30일
    elif period == "year":
        start = today - timedelta(days=364)  # 오늘 포함 365일
    else:
        start = today
    return start.strftime("%Y-%m-%d"), today.strftime("%Y-%m-%d")
# ... (기존 database.py 상단 코드 동일)

def get_monthly_summary():
    """
    최근 12개월 월별 '일평균' 공부시간 반환 (요구사항 5 반영)
    반환: [{"date": "YYYY-MM", "korean": 일평균분, ...}, ...]
    """
    conn = _connect()
    try:
        cur = conn.cursor()
        # SUM 대신 AVG를 사용하여 각 월별 일평균(반올림 정수형)을 구함
        cur.execute("""
            SELECT
                substr(date, 1, 7) AS month,
                ROUND(AVG(korean)),
                ROUND(AVG(english)),
                ROUND(AVG(math)),
                ROUND(AVG(science)),
                ROUND(AVG(social))
            FROM study_record
            GROUP BY month
            ORDER BY month DESC
            LIMIT 12
        """)
        rows = cur.fetchall()
    finally:
        conn.close()

    rows.reverse()
    result = []
    for r in rows:
        item = {"date": r[0]}
        item.update(dict(zip(SUBJECTS, [int(v or 0) for v in r[1:]])))
        result.append(item)
    return result

