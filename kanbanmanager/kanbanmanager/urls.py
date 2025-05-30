# kanbanmanager/urls.py
from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('admin/', admin.site.urls),

    # аутентификация
    path('login/',  auth_views.LoginView.as_view(template_name='registration/login.html'),  name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'),                       name='logout'),
    path('accounts/signup/', include('main.urls')),  # чтобы /accounts/signup/ вело на ваш signup


    # ваша основная аппликация
    path('', include('main.urls', namespace='main')),
]
