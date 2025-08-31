from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.views.generic import (
    ListView, DetailView, CreateView, UpdateView, DeleteView
)
from .models import InformationFromCompany
from .forms import InformationForm
from apps.company.models import Company

class InformationListView(LoginRequiredMixin, ListView):
    model = InformationFromCompany
    template_name = 'information/information_list.html'
    context_object_name = 'information_list'
    paginate_by = 10

class InformationDetailView(LoginRequiredMixin, DetailView):
    model = InformationFromCompany
    template_name = 'information/information_detail.html'
    context_object_name = 'information'

class InformationCreateView(LoginRequiredMixin, CreateView):
    model = InformationFromCompany
    form_class = InformationForm
    template_name = 'information/information_form.html'
    success_url = reverse_lazy('information:information_list')

    def form_valid(self, form):
        company = Company.objects.first()
        if company:
            form.instance.corporate_number = company.corporate_number
        return super().form_valid(form)

class InformationUpdateView(LoginRequiredMixin, UpdateView):
    model = InformationFromCompany
    form_class = InformationForm
    template_name = 'information/information_form.html'
    success_url = reverse_lazy('information:information_list')

class InformationDeleteView(LoginRequiredMixin, DeleteView):
    model = InformationFromCompany
    template_name = 'information/information_confirm_delete.html'
    success_url = reverse_lazy('information:information_list')
    context_object_name = 'information'
