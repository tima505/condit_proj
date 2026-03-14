from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Ingredient, Product, RecipeItem, Wholesaler, Shift, Order, Payment, Payroll

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ('Дополнительная информация', {'fields': ('role', 'created_by')}),
    )
    list_display = ('username', 'email', 'first_name', 'last_name', 'role', 'is_staff')

@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    list_display = ('name', 'quantity', 'unit', 'min_stock')
    search_fields = ('name',)

class RecipeItemInline(admin.TabularInline):
    model = RecipeItem
    extra = 1

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'price')
    search_fields = ('name',)
    inlines = [RecipeItemInline]

@admin.register(Wholesaler)
class WholesalerAdmin(admin.ModelAdmin):
    list_display = ('name', 'phone', 'balance', 'user')
    search_fields = ('name', 'phone')

@admin.register(Shift)
class ShiftAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'opened_at', 'closed_at', 'opened_by', 'income', 'company_profit')
    list_filter = ('opened_at', 'closed_at')

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'wholesaler', 'product', 'quantity', 'total_price', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('wholesaler__name', 'product__name')

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('wholesaler', 'amount', 'date', 'shift')
    list_filter = ('date',)

@admin.register(Payroll)
class PayrollAdmin(admin.ModelAdmin):
    list_display = ('worker', 'amount', 'date', 'shift')
    list_filter = ('date',)
