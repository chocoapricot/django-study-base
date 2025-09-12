from import_export import resources, fields
from .models import ClientContract, StaffContract

class ClientContractResource(resources.ModelResource):
    client_name = fields.Field(attribute='client__name', column_name='クライアント名')
    contract_status_display = fields.Field(column_name='契約ステータス')

    class Meta:
        model = ClientContract
        fields = ('id', 'contract_name', 'client_name', 'start_date', 'end_date', 'contract_status_display', 'created_at', 'updated_at')
        export_order = ('id', 'contract_name', 'client_name', 'start_date', 'end_date', 'contract_status_display', 'created_at', 'updated_at')

    def dehydrate_contract_status_display(self, contract):
        return contract.get_contract_status_display()

class StaffContractResource(resources.ModelResource):
    staff_name = fields.Field(column_name='スタッフ名')
    contract_status_display = fields.Field(column_name='契約ステータス')

    class Meta:
        model = StaffContract
        fields = ('id', 'contract_name', 'staff_name', 'start_date', 'end_date', 'contract_status_display', 'created_at', 'updated_at')
        export_order = ('id', 'contract_name', 'staff_name', 'start_date', 'end_date', 'contract_status_display', 'created_at', 'updated_at')

    def dehydrate_staff_name(self, contract):
        return contract.staff.name

    def dehydrate_contract_status_display(self, contract):
        return contract.get_contract_status_display()
