import os
import re
from django.conf import settings
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator
from django.http import Http404

def get_table_info_from_readme():
    """README.mdからテーブル情報をパースしてリストとして返す"""
    readme_path = os.path.join(settings.BASE_DIR, 'README.md')
    tables_info = []
    in_table_section = False
    try:
        with open(readme_path, 'r', encoding='utf-8') as f:
            for line in f:
                if '### 本アプリケーション独自テーブル' in line:
                    in_table_section = True
                    continue

                if in_table_section and line.strip().startswith('|'):
                    if '---' in line or 'テーブル名' in line:
                        continue

                    parts = [p.strip() for p in line.strip().split('|') if p.strip()]
                    if len(parts) == 3:
                        table_name = re.sub(r'`', '', parts[0])
                        model_name = re.sub(r'`', '', parts[1])
                        description = parts[2]
                        tables_info.append({
                            'name': table_name,
                            'model': model_name,
                            'description': description,
                        })
                elif in_table_section and not line.strip().startswith('|'):
                    if tables_info:
                        break
    except FileNotFoundError:
        pass
    return tables_info

class TableListView(LoginRequiredMixin, TemplateView):
    """
    README.mdからテーブル一覧を読み込んで表示するビュー
    """
    template_name = 'system/tables/table_list.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        all_tables = get_table_info_from_readme()

        paginator = Paginator(all_tables, 1000)
        page_number = self.request.GET.get('page')
        page_obj = paginator.get_page(page_number)

        context['tables'] = page_obj
        context['page_title'] = 'テーブル一覧'
        context['active_menu'] = 'system_tables'
        return context

class TableDataView(LoginRequiredMixin, TemplateView):
    """
    指定されたテーブルのデータを表示するビュー
    """
    template_name = 'system/tables/table_data.html'

    def get_context_data(self, **kwargs):
        from django.db import connection
        from django.core.paginator import Paginator

        context = super().get_context_data(**kwargs)
        table_name = kwargs.get('table_name')

        allowed_tables_info = get_table_info_from_readme()
        allowed_table_names = [t['name'] for t in allowed_tables_info]
        if table_name not in allowed_table_names:
            raise Http404("Table not found or not allowed")

        sort_by = self.request.GET.get('sort_by')
        order = self.request.GET.get('order', 'asc')
        page_number = self.request.GET.get('page', 1)

        query = f'SELECT * FROM {table_name}'

        headers = []
        with connection.cursor() as cursor:
            cursor.execute(f"PRAGMA table_info({table_name})")
            headers = [row[1] for row in cursor.fetchall()]

        if sort_by and sort_by in headers:
            if order not in ['asc', 'desc']:
                order = 'asc'
            query += f' ORDER BY {sort_by} {order}'

        query += ' LIMIT 1000'

        with connection.cursor() as cursor:
            cursor.execute(query)
            all_rows = cursor.fetchall()

        paginator = Paginator(all_rows, 20)
        page_obj = paginator.get_page(page_number)

        context['page_title'] = f'テーブルデータ: {table_name}'
        context['table_name'] = table_name
        context['headers'] = headers
        context['rows'] = page_obj
        context['active_menu'] = 'system_tables'
        context['sort_by'] = sort_by
        context['order'] = 'desc' if order == 'asc' else 'asc' # For toggling
        return context
