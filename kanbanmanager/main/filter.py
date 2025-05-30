# main/filters.py
import django_filters # type: ignore
from .models import Company

class CompanyFilter(django_filters.FilterSet):
    q      = django_filters.CharFilter(field_name='name',
                                       lookup_expr='icontains',
                                       label='Поиск')
    status = django_filters.ModelChoiceFilter(queryset=Company._meta.get_field('status').related_model.objects.all())
    region = django_filters.ChoiceFilter(choices=Company._meta.get_field('region').choices)

    class Meta:
        model = Company
        fields = ['q', 'status', 'region']
