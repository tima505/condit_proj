from django import forms
from django.forms import inlineformset_factory
from .models import Order, Payment, Product, RecipeItem, Ingredient, CustomRole

class OrderCreateForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ['wholesaler', 'product', 'quantity']
        widgets = {
            'wholesaler': forms.Select(attrs={'class': 'block w-full rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-slate-900 shadow-sm focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent transition-all hover:bg-white'}),
            'product': forms.Select(attrs={'class': 'block w-full rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-slate-900 shadow-sm focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent transition-all hover:bg-white'}),
            'quantity': forms.NumberInput(attrs={'class': 'block w-full rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-slate-900 shadow-sm focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent transition-all hover:bg-white', 'min': '1'}),
        }

class PaymentForm(forms.ModelForm):
    class Meta:
        model = Payment
        fields = ['amount']
        widgets = {
            'amount': forms.NumberInput(attrs={'class': 'block w-full rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-slate-900 shadow-sm focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent transition-all hover:bg-white', 'min': '1', 'step': '0.01'}),
        }

class IngredientForm(forms.ModelForm):
    class Meta:
        model = Ingredient
        fields = ['name', 'unit', 'quantity', 'min_stock']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'block w-full rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-slate-900 shadow-sm focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent transition-all hover:bg-white'}),
            'unit': forms.Select(attrs={'class': 'block w-full rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-slate-900 shadow-sm focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent transition-all hover:bg-white'}),
            'quantity': forms.NumberInput(attrs={'class': 'block w-full rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-slate-900 shadow-sm focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent transition-all hover:bg-white', 'min': '0'}),
            'min_stock': forms.NumberInput(attrs={'class': 'block w-full rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-slate-900 shadow-sm focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent transition-all hover:bg-white', 'min': '0'}),
        }

class IngredientAddStockForm(forms.Form):
    amount = forms.DecimalField(
        label='Количество',
        max_digits=12,
        decimal_places=2,
        min_value=0.01,
        widget=forms.NumberInput(attrs={'class': 'block w-full rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-slate-900 shadow-sm focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent transition-all hover:bg-white', 'step': '0.01', 'id': 'id_amount'})
    )
    total_cost = forms.DecimalField(
        label='Общая сумма закупки (₸)',
        max_digits=12,
        decimal_places=2,
        min_value=0,
        required=False,
        widget=forms.NumberInput(attrs={'class': 'block w-full rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-slate-900 shadow-sm focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent transition-all hover:bg-white', 'step': '0.01', 'id': 'id_total_cost'})
    )
    price_per_unit = forms.DecimalField(
        label='Цена за единицу (₸)',
        max_digits=12,
        decimal_places=2,
        min_value=0,
        required=False,
        widget=forms.NumberInput(attrs={'class': 'block w-full rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-slate-900 shadow-sm focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent transition-all hover:bg-white', 'step': '0.01', 'id': 'id_price_per_unit'})
    )

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['name', 'price']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'block w-full rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-slate-900 shadow-sm focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent transition-all hover:bg-white'}),
            'price': forms.NumberInput(attrs={'class': 'block w-full rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-slate-900 shadow-sm focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent transition-all hover:bg-white', 'min': '0'}),
        }

RecipeItemFormSet = inlineformset_factory(
    Product, RecipeItem,
    fields=['ingredient', 'quantity_per_unit'],
    extra=1,
    can_delete=True,
    widgets={
        'ingredient': forms.Select(attrs={'class': 'block w-full rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-slate-900 shadow-sm focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent transition-all hover:bg-white'}),
        'quantity_per_unit': forms.NumberInput(attrs={'class': 'block w-full rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-slate-900 shadow-sm focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent transition-all hover:bg-white', 'step': '0.0001'}),
    }
)

from django.contrib.auth import get_user_model

User = get_user_model()

class BaseUserCreationForm(forms.Form):
    username = forms.CharField(label='Логин', widget=forms.TextInput(attrs={'class': 'block w-full rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-slate-900 shadow-sm focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent transition-all hover:bg-white'}))
    password = forms.CharField(label='Пароль', widget=forms.PasswordInput(attrs={'class': 'block w-full rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-slate-900 shadow-sm focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent transition-all hover:bg-white'}))
    first_name = forms.CharField(label='Имя', required=False, widget=forms.TextInput(attrs={'class': 'block w-full rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-slate-900 shadow-sm focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent transition-all hover:bg-white'}))
    last_name = forms.CharField(label='Фамилия', required=False, widget=forms.TextInput(attrs={'class': 'block w-full rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-slate-900 shadow-sm focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent transition-all hover:bg-white'}))

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError("Пользователь с таким логином уже существует!")
        return username

class ManagerCreationForm(BaseUserCreationForm):
    pass

class WorkerCreationForm(BaseUserCreationForm):
    ROLE_CHOICES = [
        ('worker', 'Рабочий'),
        ('manager', 'Главный Менеджер (Все права)'),
    ]
    role = forms.ChoiceField(
        label='Роль',
        choices=ROLE_CHOICES,
        widget=forms.Select(attrs={'class': 'block w-full rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-slate-900 shadow-sm focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent transition-all hover:bg-white'})
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Dynamically load custom roles
        choices = list(self.ROLE_CHOICES)
        for custom_role in CustomRole.objects.all():
            choices.append((f"custom_{custom_role.id}", f"{custom_role.name}"))
        self.fields['role'].choices = choices

class WorkerEditForm(forms.ModelForm):
    ROLE_CHOICES = [
        ('worker', 'Рабочий'),
        ('manager', 'Главный Менеджер (Все права)'),
    ]
    role = forms.ChoiceField(
        label='Роль',
        choices=ROLE_CHOICES,
        widget=forms.Select(attrs={'class': 'block w-full rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-slate-900 shadow-sm focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent transition-all hover:bg-white'})
    )
    password = forms.CharField(label='Новый пароль (оставьте пустым, если не меняете)', required=False, widget=forms.PasswordInput(attrs={'class': 'block w-full rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-slate-900 shadow-sm focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent transition-all hover:bg-white'}))

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'block w-full rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-slate-900 shadow-sm focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent transition-all hover:bg-white'}),
            'first_name': forms.TextInput(attrs={'class': 'block w-full rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-slate-900 shadow-sm focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent transition-all hover:bg-white'}),
            'last_name': forms.TextInput(attrs={'class': 'block w-full rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-slate-900 shadow-sm focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent transition-all hover:bg-white'})
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        choices = list(self.ROLE_CHOICES)
        for custom_role in CustomRole.objects.all():
            choices.append((f"custom_{custom_role.id}", f"{custom_role.name}"))
        self.fields['role'].choices = choices
        
        if self.instance and self.instance.pk:
            if self.instance.custom_role:
                self.fields['role'].initial = f"custom_{self.instance.custom_role.id}"
            else:
                self.fields['role'].initial = self.instance.role

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if User.objects.filter(username=username).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("Пользователь с таким логином уже существует!")
        return username

class RoleCreationForm(forms.ModelForm):
    class Meta:
        model = CustomRole
        fields = '__all__'
        widgets = {
            'name': forms.TextInput(attrs={'class': 'block w-full rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-slate-900 shadow-sm focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent transition-all hover:bg-white', 'placeholder': 'Название роли'}),
        }
class WholesalerCreationForm(BaseUserCreationForm):
    company_name = forms.CharField(label='Название/Имя', widget=forms.TextInput(attrs={'class': 'block w-full rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-slate-900 shadow-sm focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent transition-all hover:bg-white'}))
    phone = forms.CharField(label='Телефон', required=False, widget=forms.TextInput(attrs={'class': 'block w-full rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-slate-900 shadow-sm focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent transition-all hover:bg-white'}))

class WorkerReportForm(forms.Form):
    quantity = forms.IntegerField(
        label='Сколько штук сделано?',
        min_value=1,
        widget=forms.NumberInput(attrs={'class': 'block w-full rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-slate-900 shadow-sm focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent transition-all hover:bg-white'})
    )
