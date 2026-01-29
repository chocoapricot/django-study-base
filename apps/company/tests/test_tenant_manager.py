from django.test import TestCase, RequestFactory
from django.contrib.sessions.middleware import SessionMiddleware
from apps.company.models import Company, CompanyDepartment, CompanyUser
from apps.common.middleware import TenantMiddleware

class TenantManagerTest(TestCase):
    """TenantManagerのフィルタリング機能のテスト"""

    def setUp(self):
        self.factory = RequestFactory()

        # 会社A
        self.company_a = Company.objects.create(name="会社A", tenant_id=100)
        self.dept_a = CompanyDepartment.objects.create(
            name="部署A", department_code="A001", tenant_id=100
        )
        self.user_a = CompanyUser.objects.create(
            name_last="田中", name_first="太郎", tenant_id=100
        )

        # 会社B
        self.company_b = Company.objects.create(name="会社B", tenant_id=200)
        self.dept_b = CompanyDepartment.objects.create(
            name="部署B", department_code="B001", tenant_id=200
        )
        self.user_b = CompanyUser.objects.create(
            name_last="佐藤", name_first="花子", tenant_id=200
        )

    def _get_request_with_session(self, tenant_id=None):
        request = self.factory.get('/')
        # SessionMiddlewareをシミュレート
        middleware = SessionMiddleware(lambda r: None)
        middleware.process_request(request)
        if tenant_id:
            request.session['current_tenant_id'] = tenant_id
        request.session.save()
        return request

    def test_filter_by_session_tenant_id(self):
        """セッションのテナントIDで正しくフィルタリングされるか"""
        request = self._get_request_with_session(tenant_id=100)

        def view_func(req):
            # 会社Aのデータのみ取得できるはず
            self.assertEqual(CompanyDepartment.objects.count(), 1)
            self.assertEqual(CompanyDepartment.objects.first().name, "部署A")
            self.assertEqual(CompanyUser.objects.count(), 1)
            self.assertEqual(CompanyUser.objects.first().name_last, "田中")
            return None

        tenant_middleware = TenantMiddleware(view_func)
        tenant_middleware(request)

    def test_filter_by_another_session_tenant_id(self):
        """別のセッションのテナントIDで正しくフィルタリングされるか"""
        request = self._get_request_with_session(tenant_id=200)

        def view_func(req):
            # 会社Bのデータのみ取得できるはず
            self.assertEqual(CompanyDepartment.objects.count(), 1)
            self.assertEqual(CompanyDepartment.objects.first().name, "部署B")
            self.assertEqual(CompanyUser.objects.count(), 1)
            self.assertEqual(CompanyUser.objects.first().name_last, "佐藤")
            return None

        tenant_middleware = TenantMiddleware(view_func)
        tenant_middleware(request)

    def test_no_tenant_id_in_session_returns_none(self):
        """セッションにテナントIDがない場合は空のクエリセットを返すか"""
        request = self._get_request_with_session(tenant_id=None)

        def view_func(req):
            self.assertEqual(CompanyDepartment.objects.count(), 0)
            self.assertEqual(CompanyUser.objects.count(), 0)
            return None

        tenant_middleware = TenantMiddleware(view_func)
        tenant_middleware(request)

    def test_unfiltered_outside_request(self):
        """リクエスト外（ミドルウェアを通っていない状態）ではフィルタリングされないか"""
        # setUpで作成したデータが全て取得できるはず
        self.assertEqual(CompanyDepartment.objects.count(), 2)
        self.assertEqual(CompanyUser.objects.count(), 2)
