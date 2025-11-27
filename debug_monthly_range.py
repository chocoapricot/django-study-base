import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.kintai.models import StaffTimecard, StaffTimesheet
from apps.contract.models import StaffContract
from apps.staff.models import Staff
from apps.master.models_contract import OvertimePattern, ContractPattern, EmploymentType
from datetime import date, time

# テストデータ作成
emp_type = EmploymentType.objects.create(name="正社員_test")
contract_pattern = ContractPattern.objects.create(name="test_pattern", domain='1')

pattern_monthly_range = OvertimePattern.objects.create(
    name='月単位時間範囲_test',
    calculate_midnight_premium=False,
    calculation_type='monthly_range',
    monthly_range_min=140,
    monthly_range_max=160,
)

staff = Staff.objects.create(
    name_last='テスト', name_first='太郎',
)

staff_contract = StaffContract.objects.create(
    staff=staff,
    contract_name='Test Contract',
    start_date=date(2023, 1, 1),
    contract_pattern=contract_pattern,
    overtime_pattern=pattern_monthly_range,
)

timesheet = StaffTimesheet.objects.create(
    staff_contract=staff_contract,
    staff=staff,
    target_month=date(2023, 1, 1),
)

# タイムカード作成（10日間、1日9時間勤務）
for day in range(1, 11):
    timecard = StaffTimecard(
        staff_contract=staff_contract,
        timesheet=timesheet,
        work_date=date(2023, 1, day),
        work_type='10',
        start_time=time(9, 0),
        end_time=time(19, 0),
        break_minutes=60,
    )
    timecard.save()
    print(f"Day {day}: work_minutes = {timecard.work_minutes}")

# 結果確認
timesheet.refresh_from_db()
print(f"\n総労働時間: {timesheet.total_work_minutes}分 ({timesheet.total_work_minutes / 60}時間)")
print(f"割増時間: {timesheet.total_premium_minutes}分")
print(f"控除時間: {timesheet.total_deduction_minutes}分")
print(f"期待値: 9000分 (150時間)")

# クリーンアップ
timesheet.delete()
staff_contract.delete()
staff.delete()
pattern_monthly_range.delete()
contract_pattern.delete()
emp_type.delete()
