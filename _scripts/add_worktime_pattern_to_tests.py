"""
スタッフ契約のテストに worktime_pattern を追加するスクリプト
"""
import re
import os
from pathlib import Path

# テストディレクトリ
test_dir = Path('apps/contract/tests')

# 修正対象のファイルパターン
test_files = list(test_dir.glob('test_*.py'))

for test_file in test_files:
    print(f"Processing: {test_file}")
    
    with open(test_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_content = content
    
    # パターン1: StaffContractForm(data=form_data) の前の form_data に worktime_pattern を追加
    # 既に worktime_pattern が含まれている場合はスキップ
    pattern1 = r"(form_data\s*=\s*\{[^}]*?'pay_unit':\s*[^,]+,)(\s*\})"
    
    def add_worktime_if_needed(match):
        form_data_content = match.group(0)
        if 'worktime_pattern' in form_data_content:
            return form_data_content
        # pay_unit の後に worktime_pattern を追加
        return match.group(1) + "\n            'worktime_pattern': self.worktime_pattern.pk," + match.group(2)
    
    content = re.sub(pattern1, add_worktime_if_needed, content)
    
    # パターン2: StaffContract.objects.create() に worktime_pattern を追加
    # 既に worktime_pattern が含まれている場合はスキップ
    pattern2 = r"(StaffContract\.objects\.create\([^)]*?pay_unit=[^,]+,)(\s*\))"
    
    def add_worktime_to_create(match):
        create_content = match.group(0)
        if 'worktime_pattern' in create_content:
            return create_content
        # pay_unit の後に worktime_pattern を追加
        return match.group(1) + "\n            worktime_pattern=self.worktime_pattern," + match.group(2)
    
    content = re.sub(pattern2, add_worktime_to_create, content)
    
    # 変更があった場合のみファイルを更新
    if content != original_content:
        with open(test_file, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"  Updated: {test_file}")
    else:
        print(f"  No changes: {test_file}")

print("Done!")
