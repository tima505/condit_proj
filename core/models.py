from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from decimal import Decimal

class CustomRole(models.Model):
    name = models.CharField(max_length=100, verbose_name='Название роли')
    can_view_ready_stock = models.BooleanField(default=False, verbose_name='Готовый склад')
    can_view_ingredients = models.BooleanField(default=False, verbose_name='Склад сырья')
    can_view_arrivals = models.BooleanField(default=False, verbose_name='Приход')
    can_view_cash = models.BooleanField(default=False, verbose_name='Касса')
    can_view_orders = models.BooleanField(default=False, verbose_name='Заказы')
    can_view_reports = models.BooleanField(default=False, verbose_name='Отчет')
    can_view_staff = models.BooleanField(default=False, verbose_name='Сотрудники')
    can_view_workers = models.BooleanField(default=False, verbose_name='Работники')
    can_view_users = models.BooleanField(default=False, verbose_name='Пользователи')
    can_view_categories = models.BooleanField(default=False, verbose_name='Категории')
    can_view_products = models.BooleanField(default=False, verbose_name='Продукты')
    can_view_wholesalers = models.BooleanField(default=False, verbose_name='Оптовики')

    class Meta:
        verbose_name = 'Роль'
        verbose_name_plural = 'Роли'

    def __str__(self):
        return self.name

class User(AbstractUser):
    ROLE_CHOICES = (
        ('admin', 'Администратор'),
        ('manager', 'Менеджер'),
        ('worker', 'Рабочий'),
        ('wholesaler', 'Оптовик'),
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='worker', verbose_name='Роль')
    custom_role = models.ForeignKey(CustomRole, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='Индивидуальная роль')
    created_by = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, verbose_name='Создан пользователем')

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'

    def save(self, *args, **kwargs):
        if self.role in ['admin', 'manager']:
            self.is_staff = True
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"


class Ingredient(models.Model):
    UNIT_CHOICES = [
        ('kg', 'кг'),
        ('g', 'г'),
        ('pcs', 'шт'),
        ('l', 'л'),
    ]
    name = models.CharField(max_length=200, verbose_name='Название')
    unit = models.CharField(max_length=10, choices=UNIT_CHOICES, verbose_name='Единица измерения')
    quantity = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name='Количество на складе')
    min_stock = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name='Мин. остаток')

    class Meta:
        verbose_name = 'Ингредиент'
        verbose_name_plural = 'Ингредиенты'

    def __str__(self):
        return self.name

    @property
    def average_price(self):
        """Возвращает среднюю цену за единицу из всех приходов"""
        arrivals = self.arrivals.all()
        if not arrivals.exists():
            return Decimal('0.00')
        total_qty = sum(a.quantity for a in arrivals)
        if total_qty == 0:
            return Decimal('0.00')
        total_cost = sum(a.quantity * a.price for a in arrivals)
        return (total_cost / total_qty).quantize(Decimal('0.01'))

class IngredientArrival(models.Model):
    ingredient = models.ForeignKey(Ingredient, on_delete=models.CASCADE, related_name='arrivals', verbose_name='Ингредиент')
    quantity = models.DecimalField(max_digits=12, decimal_places=2, verbose_name='Количество (приход)')
    remaining_quantity = models.DecimalField(max_digits=12, decimal_places=2, verbose_name='Остаток в партии')
    price = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name='Цена за единицу (₸)')
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name='Дата прихода')

    class Meta:
        verbose_name = 'Приход ингредиента'
        verbose_name_plural = 'Приходы ингредиентов'
        ordering = ['timestamp']

    def __str__(self):
        return f"{self.ingredient.name} - {self.quantity} {self.ingredient.get_unit_display()} ({self.timestamp.strftime('%d.%m.%Y')})"

    @property
    def total_cost(self):
        return (self.quantity * self.price).quantize(Decimal('0.01'))


class Product(models.Model):
    name = models.CharField(max_length=200, verbose_name='Название')
    price = models.DecimalField(max_digits=12, decimal_places=0, verbose_name='Цена (₸)')
    stock_quantity = models.PositiveIntegerField(default=0, verbose_name='На готовом складе (шт)')

    class Meta:
        verbose_name = 'Товар'
        verbose_name_plural = 'Товары'

    def __str__(self):
        return self.name

    @property
    def cost_price(self):
        """Рассчитывает себестоимость товара на основе средних цен ингредиентов"""
        total_cost = Decimal('0.00')
        for item in self.recipe_items.all():
            total_cost += item.quantity_per_unit * item.ingredient.average_price
        return total_cost.quantize(Decimal('0.01'))

    @property
    def recommended_price(self):
        """Рекомендуемая цена (себестоимость * 2)"""
        return (self.cost_price * Decimal('2.0')).quantize(Decimal('0'))

    def produce(self, quantity):
        """Производство товара на готовый склад (списание сырья)"""
        qty = Decimal(quantity)
        # 1. Проверка
        for item in self.recipe_items.all():
            total_needed = item.quantity_per_unit * qty
            if item.ingredient.quantity < total_needed:
                raise ValueError(f"Недостаточно {item.ingredient.name}! Нужно {total_needed} {item.ingredient.get_unit_display()}, осталось {item.ingredient.quantity} {item.ingredient.get_unit_display()}.")
                
        # 2. Списание
        for item in self.recipe_items.all():
            total_needed = item.quantity_per_unit * qty
            item.ingredient.quantity -= total_needed
            item.ingredient.save()
            
            remaining_to_deduct = total_needed
            arrivals = item.ingredient.arrivals.filter(remaining_quantity__gt=0).order_by('timestamp')
            for arrival in arrivals:
                if remaining_to_deduct <= 0:
                    break
                if arrival.remaining_quantity >= remaining_to_deduct:
                    arrival.remaining_quantity -= remaining_to_deduct
                    remaining_to_deduct = 0
                else:
                    remaining_to_deduct -= arrival.remaining_quantity
                    arrival.remaining_quantity = 0
                arrival.save()
                
        # 3. Начисление готового товара
        self.stock_quantity += int(quantity)
        self.save()


class RecipeItem(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='recipe_items', verbose_name='Товар')
    ingredient = models.ForeignKey(Ingredient, on_delete=models.PROTECT, verbose_name='Ингредиент')
    quantity_per_unit = models.DecimalField(max_digits=12, decimal_places=4, verbose_name='Количество на ед. товара')

    class Meta:
        verbose_name = 'Ингредиент рецепта'
        verbose_name_plural = 'Ингредиенты рецепта'
        unique_together = ('product', 'ingredient')

    def __str__(self):
        return f"{self.ingredient.name} для {self.product.name}"


class Wholesaler(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='wholesaler_profile', verbose_name='Пользователь')
    name = models.CharField(max_length=200, verbose_name='Название/Имя')
    phone = models.CharField(max_length=20, blank=True, null=True, verbose_name='Телефон')
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name='Долг (₸)') # положительный = должен нам

    class Meta:
        verbose_name = 'Оптовик'
        verbose_name_plural = 'Оптовики'

    def __str__(self):
        return self.name


class Shift(models.Model):
    opened_at = models.DateTimeField(default=timezone.now, verbose_name='Время открытия')
    closed_at = models.DateTimeField(null=True, blank=True, verbose_name='Время закрытия')
    opened_by = models.ForeignKey(User, on_delete=models.PROTECT, verbose_name='Открыл менеджер')
    income = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name='Доход (₸)')
    expenses = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name='Расходы (₸)')
    payroll_total = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name='ФОТ (₸)')
    company_profit = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name='Прибыль компании (₸)')

    class Meta:
        verbose_name = 'Смена'
        verbose_name_plural = 'Смены'

    def __str__(self):
        return f"Смена {self.opened_at.strftime('%d.%m.%Y %H:%M')}"

    @property
    def is_active(self):
        return self.closed_at is None

    def close_shift(self):
        if not self.is_active:
            raise ValueError("Смена уже закрыта")
            
        self.closed_at = timezone.now()
        
        # Доход = сумма всех Payment (живых денег) за эту смену
        payments_sum = self.payments.aggregate(models.Sum('amount'))['amount__sum'] or Decimal('0.00')
        self.income = payments_sum
        
        # ФОТ = 50% от внесенных живых денег (payments_sum)
        self.payroll_total = self.income * Decimal('0.5')
        
        # Находим всех рабочих и делим ЗП поровну между ними
        workers = User.objects.filter(role='worker')
        workers_count = workers.count()
        
        if self.payroll_total > Decimal('0.00') and workers_count > 0:
            amount_per_worker = (self.payroll_total / Decimal(workers_count)).quantize(Decimal('0.01'))
            for w in workers:
                Payroll.objects.create(
                    worker=w,
                    amount=amount_per_worker,
                    shift=self
                )
                
        # Прибыль за смену = живые деньги - выплаченная ЗП - другие расходы
        self.company_profit = self.income - self.payroll_total - self.expenses
        
        self.save()


class Order(models.Model):
    STATUS_CHOICES = (
        ('new', 'Новый'),
        ('in_production', 'В производстве'),
        ('ready', 'Готов'),
        ('completed', 'Завершён'),
        ('cancelled', 'Отменён'),
    )
    wholesaler = models.ForeignKey(Wholesaler, on_delete=models.CASCADE, related_name='orders', verbose_name='Оптовик')
    product = models.ForeignKey(Product, on_delete=models.PROTECT, verbose_name='Товар')
    quantity = models.PositiveIntegerField(verbose_name='Количество')
    total_price = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name='Сумма (₸)')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='new', verbose_name='Статус')
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name='created_orders', verbose_name='Создал менеджер')
    workers = models.ManyToManyField(User, related_name='assigned_orders', blank=True, verbose_name='Назначенные рабочие')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Создан')
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name='Завершен')

    class Meta:
        verbose_name = 'Заказ'
        verbose_name_plural = 'Заказы'

    def __str__(self):
        return f"Заказ #{self.id} - {self.product.name} ({self.quantity} шт)"

    def calculate_total(self):
        self.total_price = self.product.price * Decimal(self.quantity)

    def deduct_ingredients(self):
        # 1. Проверяем, достаточно ли всех ингредиентов на складе
        for item in self.product.recipe_items.all():
            total_needed = item.quantity_per_unit * Decimal(self.quantity)
            if item.ingredient.quantity < total_needed:
                raise ValueError(f"Недостаточно {item.ingredient.name}! Нужно {total_needed} {item.ingredient.get_unit_display()}, осталось только {item.ingredient.quantity} {item.ingredient.get_unit_display()}. Добавьте на склад или уменьшите заказ.")
                
        # 2. Если всего хватает, отнимаем со склада используя FIFO
        for item in self.product.recipe_items.all():
            total_needed = item.quantity_per_unit * Decimal(self.quantity)
            
            # Сначала уменьшаем общий остаток в модели Ingredient
            item.ingredient.quantity -= total_needed
            item.ingredient.save()
            
            # Затем распределяем списание по партиям (arrivals)
            remaining_to_deduct = total_needed
            arrivals = item.ingredient.arrivals.filter(remaining_quantity__gt=0).order_by('timestamp')
            
            for arrival in arrivals:
                if remaining_to_deduct <= 0:
                    break
                
                if arrival.remaining_quantity >= remaining_to_deduct:
                    arrival.remaining_quantity -= remaining_to_deduct
                    remaining_to_deduct = 0
                else:
                    remaining_to_deduct -= arrival.remaining_quantity
                    arrival.remaining_quantity = 0
                arrival.save()

    def return_ingredients(self):
        for item in self.product.recipe_items.all():
            total_needed = item.quantity_per_unit * Decimal(self.quantity)
            item.ingredient.quantity += total_needed
            item.ingredient.save()
            
            # Возвращаем в специальную партию "Возврат" или просто добавляем к последней
            # Для чистоты FIFO лучше создать новую запись прихода с пометкой "Возврат"
            IngredientArrival.objects.create(
                ingredient=item.ingredient,
                quantity=total_needed,
                remaining_quantity=total_needed,
                price=0, # Цена возврата может быть 0 или средней, для простоты 0
            )

    def mark_completed(self):
        self.status = 'completed'
        self.completed_at = timezone.now()
        self.wholesaler.balance += self.total_price
        self.wholesaler.save()
        self.save()

    @property
    def current_produced_quantity(self):
        return sum(log.quantity for log in self.work_logs.all())


class OrderWorkLog(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='work_logs', verbose_name='Заказ')
    worker = models.ForeignKey(User, on_delete=models.CASCADE, related_name='work_logs', verbose_name='Рабочий')
    quantity = models.PositiveIntegerField(verbose_name='Сделано штук')
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name='Время')

    class Meta:
        verbose_name = 'Отчет о работе'
        verbose_name_plural = 'Отчеты о работе'

    def __str__(self):
        return f"{self.worker.username} сделал {self.quantity} для #{self.order.id}"


class Payment(models.Model):
    wholesaler = models.ForeignKey(Wholesaler, on_delete=models.CASCADE, related_name='payments', verbose_name='Оптовик')
    amount = models.DecimalField(max_digits=12, decimal_places=2, verbose_name='Сумма (₸)')
    date = models.DateTimeField(auto_now_add=True, verbose_name='Дата внесения')
    shift = models.ForeignKey(Shift, on_delete=models.PROTECT, related_name='payments', verbose_name='Смена')

    class Meta:
        verbose_name = 'Оплата (погашение)'
        verbose_name_plural = 'Оплаты'

    def __str__(self):
        return f"{self.amount} от {self.wholesaler.name}"

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)
        if is_new:
            self.wholesaler.balance -= self.amount
            self.wholesaler.save()


class Payroll(models.Model):
    worker = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payrolls', verbose_name='Рабочий')
    amount = models.DecimalField(max_digits=12, decimal_places=2, verbose_name='Сумма (₸)')
    date = models.DateTimeField(auto_now_add=True, verbose_name='Дата начисления')
    shift = models.ForeignKey(Shift, on_delete=models.PROTECT, related_name='payrolls', verbose_name='Смена')

    class Meta:
        verbose_name = 'Зарплата'
        verbose_name_plural = 'Зарплаты'

    def __str__(self):
        return f"ЗП {self.worker.username}: {self.amount}"
