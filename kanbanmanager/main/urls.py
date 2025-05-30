# main/urls.py
from django.urls import path
from . import views

app_name = 'main'

urlpatterns = [
    # список компаний (если это ваша главная CRUD-страница)
    path('', views.index, name='index'),

    # Kanban-доска
    path('board/', views.board, name='board'),

    path('add/',    views.add_company,    name='add_company'),
    path('edit/<int:pk>/',   views.edit_company,   name='edit_company'),
    path('delete/<int:pk>/', views.delete_company, name='delete_company'),

    path('move/',    views.move_company,     name='move_company'),
    path('reorder/', views.reorder_companies,name='reorder_companies'),
    path('company/<int:pk>/', views.company_detail, name='company_detail'),

    path('company/<int:company_id>/history/add/', views.add_status_history, name='add_status_history'),
    path('profile/', views.profile, name='profile'),

    path('signup/', views.signup, name='signup'),

]


# main/urls.py

urlpatterns += [
    path(
      'history/<int:history_id>/edit/',
      views.edit_status_history,
      name='edit_status_history'
    ),
    path(
      'history/<int:history_id>/delete/',
      views.delete_status_history,
      name='delete_status_history'
    ),
]
