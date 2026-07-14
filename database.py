"""
SQLite 데이터베이스 관리 모듈 (정규화 버전)
- subjects (과목 메타데이터) 테이블
- study_records (날짜별 공부 기록) 테이블
- 모든 시간은 분(minute) 단위로 저장
"""
import sqlite3
import os
from datetime import datetime, timedelta

# DB 파일 경로 (이 파일과 같은 폴더의 study.db)
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "study.db")

def _connect():
    """SQLite 연결 반환"""
    return sqlite3.connect(DB_PATH)

def init_db():
    """앱 시작 시 테이블이 없으면 생성하고 기존 스키마 마이그레이션 진행"""
    conn = _connect()
    try:
        cur = conn.cursor()
        
        # 1. subjects 테이블 생성
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS subjects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                color TEXT NOT NULL
            )
            """
        )
        
        # 2. study_records 테이블 생성
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS study_records (
                date TEXT NOT NULL,
                subject_id INTEGER NOT NULL,
                duration_minutes INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY (date, subject_id),
                FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE CASCADE
            )
            """
        )
        
        # 3. 기본 과목 데이터 삽입 (기존 하드코딩 과목들)
        default_subjects = [
            ("korean", "국어", "#4A90E2"),
            ("english", "영어", "#2ECC71"),
            ("math", "수학", "#F39C12"),
            ("science", "과학", "#9B59B6"),
            ("social", "사회", "#F1C40F"),
        ]
        for code, name, color in default_subjects:
            cur.execute(
                "INSERT OR IGNORE INTO subjects (code, name, color) VALUES (?, ?, ?)",
                (code, name, color)
            )
        
        # 4. 기존 study_record 테이블 마이그레이션 확인
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='study_record'")
        old_table_exists = cur.fetchone()
        
        if old_table_exists:
            # 기존 테이블의 컬럼 확인
            cur.execute("PRAGMA table_info(study_record)")
            columns = [col[1] for col in cur.fetchall()]
            
            # 구 테이블 컬럼이 맞는지 확인 (korean 등이 포함되어 있는지)
            if "korean" in columns:
                # 모든 기존 기록 읽기
                cur.execute("SELECT * FROM study_record")
                rows = cur.fetchall()
                
                # 과목 코드별 ID 매핑 정보 조회
                cur.execute("SELECT code, id FROM subjects")
                subj_id_map = {row[0]: row[1] for row in cur.fetchall()}
                
                for r in rows:
                    date_val = r[0]
                    for code in ["korean", "english", "math", "science", "social"]:
                        if code in columns:
                            idx = columns.index(code)
                            minutes = r[idx]
                            if minutes > 0:
                                cur.execute(
                                    """
                                    INSERT OR REPLACE INTO study_records (date, subject_id, duration_minutes)
                                    VALUES (?, ?, ?)
                                    """,
                                    (date_val, subj_id_map[code], minutes)
                                )
                # 기존 테이블 삭제
                cur.execute("DROP TABLE study_record")
        
        conn.commit()
    finally:
        conn.close()

def today_str():
    """오늘 날짜 문자열 (YYYY-MM-DD)"""
    return datetime.now().strftime("%Y-%m-%d")

def load_subject_metadata():
    """
    DB에서 실시간 과목 목록 및 색상, 라벨 메타데이터 로드.
    반환: (subjects_list, subject_labels_dict, subject_colors_dict)
    """
    conn = _connect()
    try:
        cur = conn.cursor()
        cur.execute("SELECT code, name, color FROM subjects")
        rows = cur.fetchall()
    finally:
        conn.close()
        
    subjects = []
    labels = {}
    colors = {}
    for code, name, color in rows:
        subjects.append(code)
        labels[code] = name
        colors[code] = color
    return subjects, labels, colors

def get_record(date_str):
    """
    특정 날짜 기록 반환.
    없으면 모든 과목 0인 dict 반환.
    """
    conn = _connect()
    try:
        cur = conn.cursor()
        # 모든 과목 목록 조회
        cur.execute("SELECT id, code FROM subjects")
        subjs = cur.fetchall()
        
        # 특정 날짜의 기록 조회
        cur.execute(
            "SELECT subject_id, duration_minutes FROM study_records WHERE date = ?",
            (date_str,),
        )
        records = {r[0]: r[1] for r in cur.fetchall()}
    finally:
        conn.close()
        
    return {code: records.get(sid, 0) for sid, code in subjs}

def save_record(date_str, minutes_dict):
    """
    기록 저장 (없으면 INSERT, 있으면 UPDATE = 덮어쓰기)
    minutes_dict: {"korean": 90, "english": 30, ...}
    """
    conn = _connect()
    try:
        cur = conn.cursor()
        # 과목 코드별 ID 매핑 조회
        cur.execute("SELECT code, id FROM subjects")
        subj_id_map = {row[0]: row[1] for row in cur.fetchall()}
        
        for code, minutes in minutes_dict.items():
            if code in subj_id_map:
                sid = subj_id_map[code]
                cur.execute(
                    """
                    INSERT INTO study_records (date, subject_id, duration_minutes)
                    VALUES (?, ?, ?)
                    ON CONFLICT(date, subject_id) DO UPDATE SET
                        duration_minutes = excluded.duration_minutes
                    """,
                    (date_str, sid, int(minutes))
                )
        conn.commit()
    finally:
        conn.close()

def get_total_all_time():
    """전체 누적 (총합, 과목별 dict) 반환. 단위: 분"""
    conn = _connect()
    try:
        cur = conn.cursor()
        # 모든 과목 조회
        cur.execute("SELECT id, code FROM subjects")
        subjs = cur.fetchall()
        
        # 과목별 합계 조회
        cur.execute(
            "SELECT subject_id, SUM(duration_minutes) FROM study_records GROUP BY subject_id"
        )
        sums = {r[0]: r[1] for r in cur.fetchall()}
    finally:
        conn.close()
        
    per_subject = {code: sums.get(sid, 0) for sid, code in subjs}
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
        # 모든 과목 조회
        cur.execute("SELECT id, code FROM subjects")
        subjs = cur.fetchall()
        
        # 날짜 범위 기록 조회 (날짜 오름차순)
        cur.execute(
            """
            SELECT date, subject_id, duration_minutes 
            FROM study_records 
            WHERE date BETWEEN ? AND ? 
            ORDER BY date ASC
            """,
            (start_date_str, end_date_str),
        )
        rows = cur.fetchall()
    finally:
        conn.close()
        
    # 날짜별로 그룹화
    records_by_date = {}
    for date_val, sid, minutes in rows:
        if date_val not in records_by_date:
            records_by_date[date_val] = {code: 0 for _, code in subjs}
        # 해당 과목 찾기
        for s_id, code in subjs:
            if s_id == sid:
                records_by_date[date_val][code] = minutes
                break
                
    # 리스트 변환 및 정렬된 결과 반환
    result = []
    for date_val in sorted(records_by_date.keys()):
        item = {"date": date_val}
        item.update(records_by_date[date_val])
        result.append(item)
    return result

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

def get_monthly_summary():
    """
    최근 12개월 월별 '일평균' 공부시간 반환 (요구사항 5 반영)
    반환: [{"date": "YYYY-MM", "korean": 일평균분, ...}, ...]
    """
    conn = _connect()
    try:
        cur = conn.cursor()
        # 모든 과목 조회
        cur.execute("SELECT id, code FROM subjects")
        subjs = cur.fetchall()
        
        # 월별, 과목별 평균값 계산
        cur.execute(
            """
            SELECT substr(date, 1, 7) AS month, subject_id, ROUND(AVG(duration_minutes))
            FROM study_records
            GROUP BY month, subject_id
            ORDER BY month DESC
            LIMIT 60
            """
        )
        rows = cur.fetchall()
    finally:
        conn.close()
        
    # 월별 그룹화
    monthly = {}
    for month, sid, avg_min in rows:
        if month not in monthly:
            monthly[month] = {code: 0 for _, code in subjs}
        for s_id, code in subjs:
            if s_id == sid:
                monthly[month][code] = int(avg_min or 0)
                break
                
    # 정렬 및 12개월 LIMIT
    sorted_months = sorted(monthly.keys(), reverse=True)[:12]
    result = []
    for month in reversed(sorted_months):
        item = {"date": month}
        item.update(monthly[month])
        result.append(item)
    return result

def clear_all_records():
    """모든 공부 기록 삭제"""
    conn = _connect()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM study_records")
        conn.commit()
    finally:
        conn.close()

