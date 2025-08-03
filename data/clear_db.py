#!/usr/bin/env python3
"""
stock_data.db 데이터베이스의 모든 테이블 데이터를 삭제하는 스크립트

사용법:
    python clear_db.py

주의사항:
    - 이 스크립트는 데이터베이스의 모든 데이터를 삭제합니다.
    - 실행 전에 백업을 권장합니다.
    - 테이블 구조는 유지되고 데이터만 삭제됩니다.
"""

import os
import sqlite3
import sys
from datetime import datetime

# 삭제할 데이터베이스 파일 목록 (data 폴더 기준)
DB_FILES = [
    "stock_data.db",
    # 추가 데이터베이스 파일들을 여기에 추가
]

# 데이터 폴더 경로
DATA_DIR = os.path.dirname(__file__)

def clear_all_tables():
    """모든 데이터베이스의 테이블 데이터를 삭제"""
    
    total_success = True
    all_deleted_tables = []
    
    for db_file in DB_FILES:
        db_path = os.path.join(DATA_DIR, db_file)
        
        print(f"\n{'='*50}")
        print(f"데이터베이스 처리 중: {db_file}")
        print(f"{'='*50}")
        
        if not os.path.exists(db_path):
            print(f"데이터베이스 파일이 존재하지 않습니다: {db_path}")
            continue
        
        try:
            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()
                
                # 모든 테이블 목록 조회
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
                tables = cursor.fetchall()
                
                if not tables:
                    print("삭제할 테이블이 없습니다.")
                    continue
                
                print(f"발견된 테이블: {[table[0] for table in tables]}")
                
                # 각 테이블의 데이터 삭제
                deleted_tables = []
                for table in tables:
                    table_name = table[0]
                    
                    # sqlite 시스템 테이블은 건너뛰기
                    if table_name.startswith('sqlite_'):
                        continue
                    
                    try:
                        # 테이블 데이터 삭제
                        cursor.execute(f"DELETE FROM {table_name}")
                        deleted_count = cursor.rowcount
                        deleted_tables.append((table_name, deleted_count))
                        print(f"✓ {table_name}: {deleted_count}개 행 삭제")
                        
                    except Exception as e:
                        print(f"✗ {table_name} 삭제 실패: {e}")
                        total_success = False
                
                # 변경사항 커밋
                conn.commit()
                
                print(f"\n=== {db_file} 삭제 완료 ===")
                print(f"{len(deleted_tables)}개 테이블에서 데이터가 삭제되었습니다.")
                
                # 삭제 결과 요약
                db_total_deleted = sum(count for _, count in deleted_tables)
                print(f"삭제된 행 수: {db_total_deleted}")
                
                all_deleted_tables.extend([(db_file, table_name, count) for table_name, count in deleted_tables])
                
        except Exception as e:
            print(f"데이터베이스 작업 중 오류 발생: {e}")
            total_success = False
    
    # 전체 요약
    if all_deleted_tables:
        print(f"\n{'='*60}")
        print("전체 삭제 요약")
        print(f"{'='*60}")
        
        # 데이터베이스별 요약
        db_summary = {}
        for db_file, table_name, count in all_deleted_tables:
            if db_file not in db_summary:
                db_summary[db_file] = {'tables': 0, 'rows': 0}
            db_summary[db_file]['tables'] += 1
            db_summary[db_file]['rows'] += count
        
        for db_file, summary in db_summary.items():
            print(f"• {db_file}: {summary['tables']}개 테이블, {summary['rows']:,}개 행 삭제")
        
        total_rows = sum(summary['rows'] for summary in db_summary.values())
        total_tables = sum(summary['tables'] for summary in db_summary.values())
        print(f"\n총계: {len(db_summary)}개 데이터베이스, {total_tables}개 테이블, {total_rows:,}개 행 삭제")
        print(f"삭제 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    return total_success

def get_table_info():
    """모든 데이터베이스의 테이블 정보를 조회"""
    
    for db_file in DB_FILES:
        db_path = os.path.join(DATA_DIR, db_file)
        
        print(f"\n=== {db_file} 테이블 정보 ===")
        
        if not os.path.exists(db_path):
            print(f"데이터베이스 파일이 존재하지 않습니다: {db_path}")
            continue
        
        try:
            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()
                
                # 모든 테이블 목록 조회
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
                tables = cursor.fetchall()
                
                if not tables:
                    print("테이블이 없습니다.")
                    continue
                
                total_rows = 0
                for table in tables:
                    table_name = table[0]
                    
                    # sqlite 시스템 테이블은 건너뛰기
                    if table_name.startswith('sqlite_'):
                        continue
                    
                    try:
                        # 테이블 행 수 조회
                        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                        row_count = cursor.fetchone()[0]
                        print(f"• {table_name}: {row_count:,}개 행")
                        total_rows += row_count
                        
                    except Exception as e:
                        print(f"• {table_name}: 조회 실패 ({e})")
                
                if total_rows > 0:
                    print(f"📊 {db_file} 총계: {total_rows:,}개 행")
                
        except Exception as e:
            print(f"데이터베이스 조회 중 오류 발생: {e}")

def main():
    """메인 함수"""
    
    print("=" * 60)
    print("Stock Data DB Clear Script")
    print("=" * 60)
    print(f"데이터 폴더: {DATA_DIR}")
    print(f"처리할 데이터베이스 파일: {DB_FILES}")
    print()
    
    # 현재 테이블 정보 표시
    print("현재 데이터베이스 상태:")
    get_table_info()
    print()
    
    # 사용자 확인
    if len(sys.argv) > 1 and sys.argv[1] == '--force':
        # --force 옵션이 있으면 확인 없이 실행
        confirm = 'y'
    else:
        confirm = input("모든 데이터베이스의 테이블 데이터를 삭제하시겠습니까? (y/N): ").lower().strip()
    
    if confirm in ['y', 'yes']:
        print("\n데이터 삭제를 시작합니다...")
        success = clear_all_tables()
        
        if success:
            print("\n삭제 후 데이터베이스 상태:")
            get_table_info()
        else:
            print("일부 데이터베이스 삭제에 실패했습니다.")
            sys.exit(1)
            
    else:
        print("작업이 취소되었습니다.")

if __name__ == "__main__":
    main()
