# apps/contract/teishokubi_calculator.py

from datetime import date
from dateutil.relativedelta import relativedelta
from apps.contract.models import ContractAssignment, StaffContractTeishokubi, StaffContractTeishokubiDetail


class TeishokubiCalculator:
    """
    抵触日を計算するためのクラス
    """

    def __init__(self, staff_email, client_corporate_number, organization_name):
        self.staff_email = staff_email
        self.client_corporate_number = client_corporate_number
        self.organization_name = organization_name

    def calculate_and_update(self):
        """
        派遣開始日と抵触日を計算し、StaffContractTeishokubi モデルを更新または作成する
        """
        haken_start_date, assignment_periods = self._calculate_haken_start_date()

        if haken_start_date:
            conflict_date = self._calculate_conflict_date(haken_start_date)
            teishokubi = self._update_or_create_teishokubi(haken_start_date, conflict_date)

            # 既存の詳細レコードを一旦削除
            teishokubi.details.all().delete()
            # 新しい詳細レコードを作成
            for period in assignment_periods:
                StaffContractTeishokubiDetail.objects.create(
                    teishokubi=teishokubi,
                    assignment_start_date=period['start_date'],
                    assignment_end_date=period['end_date'],
                    is_calculated=period['is_calculated']
                )
        else:
            # 該当する割当がない場合は、既存の抵触日レコードを削除
            self._delete_teishokubi()

    def calculate_conflict_date_without_update(self, new_assignment_instance=None):
        """
        抵触日を計算して返す（DB更新は行わない）
        """
        haken_start_date, _ = self._calculate_haken_start_date(new_assignment_instance=new_assignment_instance)
        if haken_start_date:
            return self._calculate_conflict_date(haken_start_date)
        return None

    def _calculate_haken_start_date(self, new_assignment_instance=None):
        """
        派遣開始日を計算し、計算に使用した期間の情報を返す
        """
        assignments = self._get_relevant_assignments()
        assignment_periods = self._get_assignment_periods(assignments)

        if new_assignment_instance:
            start_date = max(new_assignment_instance.client_contract.start_date, new_assignment_instance.staff_contract.start_date)
            end_date = min(
                new_assignment_instance.client_contract.end_date if new_assignment_instance.client_contract.end_date else date.max,
                new_assignment_instance.staff_contract.end_date if new_assignment_instance.staff_contract.end_date else date.max
            )
            assignment_periods.append({
                'start_date': start_date,
                'end_date': end_date,
            })

        if not assignment_periods:
            return None, []

        # is_calculated フラグを初期化
        for period in assignment_periods:
            period['is_calculated'] = False

        sorted_periods = sorted(assignment_periods, key=lambda p: p['start_date'])

        haken_start_date = sorted_periods[0]['start_date']
        start_index = 0
        for i in range(1, len(sorted_periods)):
            prev_period = sorted_periods[i-1]
            current_period = sorted_periods[i]

            # 前の割当終了日から3ヶ月と1日以上あいているかチェック
            if current_period['start_date'] >= prev_period['end_date'] + relativedelta(months=3, days=1):
                haken_start_date = current_period['start_date']
                start_index = i

        # 算出対象の期間にフラグを立てる
        for i in range(start_index, len(sorted_periods)):
            sorted_periods[i]['is_calculated'] = True

        return haken_start_date, sorted_periods

    def _get_relevant_assignments(self):
        """
        関連する契約割当を取得する
        """
        return ContractAssignment.objects.filter(
            staff_contract__staff__email=self.staff_email,
            client_contract__client__corporate_number=self.client_corporate_number,
            client_contract__haken_info__haken_unit__name=self.organization_name,
            client_contract__client_contract_type_code='20',  # 派遣
            staff_contract__employment_type__is_fixed_term=True  # 有期雇用
        ).select_related('client_contract', 'staff_contract')

    def _get_assignment_periods(self, assignments):
        """
        割当期間のリストを取得する
        """
        periods = []
        for assignment in assignments:
            start_date = max(assignment.client_contract.start_date, assignment.staff_contract.start_date)
            end_date = min(
                assignment.client_contract.end_date if assignment.client_contract.end_date else date.max,
                assignment.staff_contract.end_date if assignment.staff_contract.end_date else date.max
            )
            periods.append({'start_date': start_date, 'end_date': end_date})
        return periods

    def _calculate_conflict_date(self, haken_start_date):
        """
        抵触日を計算する (3年後)
        """
        return haken_start_date + relativedelta(years=3)

    def _update_or_create_teishokubi(self, haken_start_date, conflict_date):
        """
        StaffContractTeishokubi モデルを更新または作成する
        """
        obj, created = StaffContractTeishokubi.objects.update_or_create(
            staff_email=self.staff_email,
            client_corporate_number=self.client_corporate_number,
            organization_name=self.organization_name,
            defaults={
                'dispatch_start_date': haken_start_date,
                'conflict_date': conflict_date,
            }
        )
        return obj

    def _delete_teishokubi(self):
        """
        StaffContractTeishokubi モデルを削除する
        """
        StaffContractTeishokubi.objects.filter(
            staff_email=self.staff_email,
            client_corporate_number=self.client_corporate_number,
            organization_name=self.organization_name
        ).delete()
