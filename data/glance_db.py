#!/usr/bin/env python3
"""
stock_data.db 데이터베이스의 구조와 데이터를 한눈에 볼 수 있는 스크립트

사용법:
    python glance_db.py              # 모든 정보 표시
    python glance_db.py --tables     # 테이블 목록만 표시
    python glance_db.py --schema     # 테이블 스키마만 표시
    python glance_db.py --data       # 데이터 샘플만 표시
    python glance_db.py --head 10    # 각 테이블의 처음 10개 행 표시 (기본: 5개)
"""

import os
import sqlite3
import sys
import argparse
from datetime import datetime

# 조회할 데이터베이스 파일 목록 (data 폴더 기준)
DB_FILES = [
    "stock_data.db",
    # 추가 데이터베이스 파일들을 여기에 추가
]

# 데이터 폴더 경로 (모듈 루트의 data 폴더)
DATA_DIR = os.path.dirname(__file__)

def get_table_schema(cursor, table_name):
    """테이블의 스키마 정보를 조회"""
    try:
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = cursor.fetchall()
        return columns
    except Exception as e:
        print(f"스키마 조회 실패: {e}")
        return []

def get_table_data(cursor, table_name, limit=5):
    """테이블의 데이터 샘플을 조회"""
    try:
        cursor.execute(f"SELECT * FROM {table_name} LIMIT {limit}")
        data = cursor.fetchall()
        return data
    except Exception as e:
        print(f"데이터 조회 실패: {e}")
        return []

def format_column_info(columns):
    """컬럼 정보를 포맷팅"""
    if not columns:
        return "컬럼 정보 없음"
    
    formatted = []
    for col in columns:
        # col = (cid, name, type, notnull, dflt_value, pk)
        cid, name, col_type, notnull, default, pk = col
        
        # 타입 정보 구성
        type_info = col_type
        
        # 제약조건 추가
        constraints = []
        if pk:
            constraints.append("PK")
        if notnull:
            constraints.append("NOT NULL")
        if default is not None:
            constraints.append(f"DEFAULT {default}")
        
        if constraints:
            type_info += f" ({', '.join(constraints)})"
        
        formatted.append(f"  • {name}: {type_info}")
    
    return "\n".join(formatted)

def format_data_rows(columns, data):
    """데이터 행을 포맷팅"""
    if not data or not columns:
        return "데이터 없음"
    
    # 컬럼명 추출
    col_names = [col[1] for col in columns]  # col[1]은 컬럼명
    
    # 각 컬럼의 최대 너비 계산
    col_widths = []
    for i, col_name in enumerate(col_names):
        max_width = len(col_name)
        for row in data:
            if i < len(row) and row[i] is not None:
                max_width = max(max_width, len(str(row[i])))
        col_widths.append(min(max_width, 20))  # 최대 20자로 제한
    
    # 헤더 출력
    header = " | ".join(col_name.ljust(width)[:width] for col_name, width in zip(col_names, col_widths))
    separator = "-" * len(header)
    
    # 데이터 행 출력
    formatted_rows = [header, separator]
    for row in data:
        formatted_row = []
        for i, (value, width) in enumerate(zip(row, col_widths)):
            if value is None:
                formatted_value = "NULL"
            else:
                formatted_value = str(value)[:width]
            formatted_row.append(formatted_value.ljust(width))
        formatted_rows.append(" | ".join(formatted_row))
    
    return "\n".join(formatted_rows)

def analyze_database(db_file, show_tables=True, show_schema=True, show_data=True, data_limit=5):
    """데이터베이스를 분석하고 정보를 출력"""
    
    db_path = os.path.join(DATA_DIR, db_file)
    
    print(f"\n{'='*80}")
    print(f"데이터베이스: {db_file}")
    print(f"경로: {db_path}")
    print(f"{'='*80}")
    
    if not os.path.exists(db_path):
        print(f"❌ 데이터베이스 파일이 존재하지 않습니다.")
        return
    
    try:
        # 파일 크기 정보
        file_size = os.path.getsize(db_path)
        if file_size > 1024 * 1024:
            size_str = f"{file_size / (1024 * 1024):.2f} MB"
        elif file_size > 1024:
            size_str = f"{file_size / 1024:.2f} KB"
        else:
            size_str = f"{file_size} bytes"
        
        print(f"📁 파일 크기: {size_str}")
        
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            
            # 모든 테이블 목록 조회
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
            tables = cursor.fetchall()
            
            if not tables:
                print("📋 테이블이 없습니다.")
                return
            
            table_names = [table[0] for table in tables]
            print(f"📋 테이블 수: {len(table_names)}")
            
            if show_tables:
                print(f"📝 테이블 목록: {', '.join(table_names)}")
            
            # 각 테이블 상세 정보
            for table_name in table_names:
                print(f"\n{'-'*60}")
                print(f"🗂️  테이블: {table_name}")
                print(f"{'-'*60}")
                
                # 행 수 조회
                try:
                    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                    row_count = cursor.fetchone()[0]
                    print(f"📊 행 수: {row_count:,}개")
                except Exception as e:
                    print(f"📊 행 수: 조회 실패 ({e})")
                    continue
                
                # 스키마 정보
                if show_schema:
                    print(f"\n🏗️  스키마:")
                    columns = get_table_schema(cursor, table_name)
                    if columns:
                        print(format_column_info(columns))
                        print(f"   총 {len(columns)}개 컬럼")
                    else:
                        print("   스키마 정보 없음")
                
                # 데이터 샘플
                if show_data and row_count > 0:
                    print(f"\n📄 데이터 샘플 (상위 {min(data_limit, row_count)}개 행):")
                    
                    if not columns:  # 스키마를 아직 조회하지 않았다면
                        columns = get_table_schema(cursor, table_name)
                    
                    data = get_table_data(cursor, table_name, data_limit)
                    if data:
                        formatted_data = format_data_rows(columns, data)
                        print(formatted_data)
                    else:
                        print("   데이터 조회 실패")
                
                # 최근 업데이트 시간 (created_at, updated_at 컬럼이 있는 경우)
                try:
                    cursor.execute(f"PRAGMA table_info({table_name})")
                    table_columns = [col[1] for col in cursor.fetchall()]
                    
                    if 'updated_at' in table_columns:
                        cursor.execute(f"SELECT MAX(updated_at) FROM {table_name}")
                        last_updated = cursor.fetchone()[0]
                        if last_updated:
                            print(f"🕒 최근 업데이트: {last_updated}")
                    elif 'created_at' in table_columns:
                        cursor.execute(f"SELECT MAX(created_at) FROM {table_name}")
                        last_created = cursor.fetchone()[0]
                        if last_created:
                            print(f"🕒 최근 생성: {last_created}")
                
                except Exception:
                    pass  # 시간 정보가 없거나 조회 실패 시 무시
    
    except Exception as e:
        print(f"❌ 데이터베이스 분석 중 오류 발생: {e}")

def get_database_summary():
    """모든 데이터베이스의 요약 정보를 출력"""
    
    print("=" * 80)
    print("📊 데이터베이스 요약")
    print("=" * 80)
    
    total_dbs = 0
    total_tables = 0
    total_rows = 0
    
    for db_file in DB_FILES:
        db_path = os.path.join(DATA_DIR, db_file)
        
        if not os.path.exists(db_path):
            print(f"• {db_file}: 파일 없음")
            continue
        
        try:
            total_dbs += 1
            file_size = os.path.getsize(db_path)
            
            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()
                
                # 테이블 수 조회
                cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
                db_tables = cursor.fetchone()[0]
                total_tables += db_tables
                
                # 총 행 수 조회
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
                tables = cursor.fetchall()
                
                db_rows = 0
                for table in tables:
                    try:
                        cursor.execute(f"SELECT COUNT(*) FROM {table[0]}")
                        db_rows += cursor.fetchone()[0]
                    except:
                        pass
                
                total_rows += db_rows
                
                # 파일 크기 포맷팅
                if file_size > 1024 * 1024:
                    size_str = f"{file_size / (1024 * 1024):.1f}MB"
                elif file_size > 1024:
                    size_str = f"{file_size / 1024:.1f}KB"
                else:
                    size_str = f"{file_size}B"
                
                print(f"• {db_file}: {db_tables}개 테이블, {db_rows:,}개 행, {size_str}")
        
        except Exception as e:
            print(f"• {db_file}: 분석 실패 ({e})")
    
    print(f"\n📈 총계: {total_dbs}개 데이터베이스, {total_tables}개 테이블, {total_rows:,}개 행")

def main():
    """메인 함수"""
    
    parser = argparse.ArgumentParser(description="데이터베이스 구조와 데이터 조회")
    parser.add_argument('--tables', action='store_true', help='테이블 목록만 표시')
    parser.add_argument('--schema', action='store_true', help='테이블 스키마만 표시')
    parser.add_argument('--data', action='store_true', help='데이터 샘플만 표시')
    parser.add_argument('--head', type=int, default=5, help='각 테이블의 상위 N개 행 표시 (기본: 5)')
    parser.add_argument('--summary', action='store_true', help='요약 정보만 표시')
    
    args = parser.parse_args()
    
    # 옵션이 아무것도 지정되지 않으면 모든 정보 표시
    if not any([args.tables, args.schema, args.data, args.summary]):
        show_tables = True
        show_schema = True 
        show_data = True
    else:
        show_tables = args.tables
        show_schema = args.schema
        show_data = args.data
    
    print("=" * 80)
    print("📋 Database Glance Script")
    print("=" * 80)
    print(f"🕒 실행 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📁 데이터 폴더: {DATA_DIR}")
    print(f"🗃️  대상 파일: {DB_FILES}")
    
    # 요약 정보만 표시
    if args.summary:
        get_database_summary()
        return
    
    # 각 데이터베이스 상세 분석
    for db_file in DB_FILES:
        analyze_database(
            db_file, 
            show_tables=show_tables, 
            show_schema=show_schema, 
            show_data=show_data, 
            data_limit=args.head
        )
    
    # 마지막에 요약 정보 표시
    get_database_summary()

if __name__ == "__main__":
    main()
