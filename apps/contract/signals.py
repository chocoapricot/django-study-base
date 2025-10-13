# apps/contract/signals.py

from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import ContractAssignment
from .teishokubi_calculator import TeishokubiCalculator
from apps.common.constants import Constants


def run_teishokubi_calculation(instance):
    """
    抵触日計算を実行するためのヘルパー関数
    """
    client_contract = instance.client_contract
    staff_contract = instance.staff_contract

    # 派遣契約かつ派遣社員(有期)の場合のみ計算を実行
    if client_contract.client_contract_type_code == Constants.CLIENT_CONTRACT_TYPE.DISPATCH and staff_contract.employment_type == '30':
        staff_email = staff_contract.staff.email
        client_corporate_number = client_contract.client.corporate_number

        # haken_info と haken_unit が存在するか確認
        if hasattr(client_contract, 'haken_info') and client_contract.haken_info and client_contract.haken_info.haken_unit:
            organization_name = client_contract.haken_info.haken_unit.name

            calculator = TeishokubiCalculator(
                staff_email=staff_email,
                client_corporate_number=client_corporate_number,
                organization_name=organization_name
            )
            calculator.calculate_and_update()


@receiver(post_save, sender=ContractAssignment)
def contract_assignment_post_save(sender, instance, **kwargs):
    """
    ContractAssignment が保存された後に抵触日を再計算する
    """
    run_teishokubi_calculation(instance)


@receiver(post_delete, sender=ContractAssignment)
def contract_assignment_post_delete(sender, instance, **kwargs):
    """
    ContractAssignment が削除された後に抵触日を再計算する
    """
    run_teishokubi_calculation(instance)
