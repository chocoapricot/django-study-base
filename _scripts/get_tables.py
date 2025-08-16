#!/usr/bin/env python
"""
データベーステーブル一覧を取得するスクリプト
"""
import os
import sys
import sqlite3

# Djangoプロジェクトのルートディレクトリに移動
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
os.chdir(project_root)

def get_table_list():
    """データベースのテーブル一覧を取得"""
    db_path = 'db.sqlite3'
    
    if not os.path.exists(db_path):
        print(f"データベースファイル '{db_path}' が見つかりません。")
        return
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
        tables = cursor.fetchall()
        
        print("=== データベーステーブル一覧 ===")
        print(f"データベース: {db_path}")
        print(f"テーブル数: {len(tables)}")
        print("-" * 40)
        
        for table in tables:
            print(table[0])
        
        conn.close()
        
    except sqlite3.Error as e:
        print(f"データベースエラー: {e}")
    except Exception as e:
        print(f"エラー: {e}")

if __name__ == "__main__":
    get_table_list()