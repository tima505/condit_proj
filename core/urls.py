from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    # Auth
    path('login/', auth_views.LoginView.as_view(template_name='login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    
    # Common router
    path('', views.role_redirect, name='role_redirect'),

    # Manager
    path('manager/', views.manager_dashboard, name='manager_dashboard'),
    path('manager/order/create/', views.create_order, name='create_order'),
    path('manager/shift/close/', views.close_shift, name='close_shift'),
    path('manager/cash/', views.cash_history, name='cash_history'),
    path('manager/products/create/', views.create_product, name='create_product'),
    path('manager/ingredients/create/', views.create_ingredient, name='create_ingredient'),
    path('manager/ingredients/<int:pk>/add-stock/', views.add_ingredient_stock, name='add_ingredient_stock'),
    path('manager/ingredients/<int:pk>/edit/', views.edit_ingredient, name='edit_ingredient'),
    path('manager/ingredients/<int:pk>/delete/', views.delete_ingredient, name='delete_ingredient'),
    path('manager/orders/', views.manager_orders, name='manager_orders'),
    path('manager/products/', views.manager_products, name='manager_products'),
    path('manager/products/<int:pk>/edit/', views.edit_product, name='edit_product'),
    path('manager/products/<int:pk>/delete/', views.delete_product, name='delete_product'),
    path('manager/ready-stock/', views.manager_ready_stock, name='manager_ready_stock'),
    path('manager/ready-stock/add/', views.manager_add_ready_stock, name='manager_add_ready_stock'),
    path('manager/ingredients/', views.manager_ingredients, name='manager_ingredients'),
    path('manager/ingredients/arrivals/', views.ingredient_arrival_history, name='ingredient_arrival_history'),
    path('manager/wholesalers/', views.manager_wholesalers, name='manager_wholesalers'),
    path('manager/wholesalers/<int:pk>/', views.wholesaler_detail, name='wholesaler_detail'),
    path('manager/workers/', views.manager_workers, name='manager_workers'),
    
    path('manager/order/<int:pk>/status/', views.update_order_status, name='update_order_status'),

    # Worker
    path('worker/', views.worker_dashboard, name='worker_dashboard'),
    path('worker/order/<int:pk>/report/', views.submit_worker_report, name='submit_worker_report'),
    
    # Wholesaler
    path('wholesaler/', views.wholesaler_dashboard, name='wholesaler_dashboard'),
    path('wholesaler/repay/', views.wholesaler_repay, name='wholesaler_repay'),
    
    # User Creation
    path('manager/create_manager/', views.create_manager, name='create_manager'),
    path('manager/create_worker/', views.create_worker, name='create_worker'),
    path('manager/user/<int:pk>/edit/', views.edit_worker, name='edit_worker'),
    path('manager/user/<int:pk>/delete/', views.delete_worker, name='delete_worker'),
    path('manager/create_wholesaler/', views.create_wholesaler, name='create_wholesaler'),
    path('manager/create_role/', views.create_role, name='create_role'),
]
