from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import Sum
from decimal import Decimal

from .models import Order, Payment, Product, Shift, Wholesaler, Payroll, User, Ingredient, OrderWorkLog, IngredientArrival, CustomRole
from .forms import OrderCreateForm, PaymentForm, ProductForm, IngredientForm, IngredientAddStockForm, RecipeItemFormSet, WorkerReportForm

@login_required
def role_redirect(request):
    role = request.user.role
    if role in ['admin', 'manager']:
        return redirect('manager_dashboard')
    elif role == 'worker':
        return redirect('worker_dashboard')
    elif role == 'wholesaler':
        return redirect('wholesaler_dashboard')
    return redirect('logout')

@login_required
def manager_dashboard(request):
    if request.user.role not in ['admin', 'manager']:
        return redirect('role_redirect')
        
    today = timezone.now().date()
    
    # Active shift
    active_shift = Shift.objects.filter(closed_at__isnull=True).first()
    
    if active_shift:
        # Выручка за текущую смену
        revenue_today = active_shift.payments.aggregate(Sum('amount'))['amount__sum'] or Decimal('0.00')
        
        # Завершенные заказы за текущую смену
        completed_orders = Order.objects.filter(status='completed', completed_at__gte=active_shift.opened_at).count()
        
        # Остаток в кассе текущей смены (пока не закрыли - это вся выручка)
        cash_register = revenue_today
        
        # Чистая прибыль (прогнозируемая: Выручка - 50% на ЗП)
        net_profit = revenue_today - (revenue_today * Decimal('0.5'))
    else:
        revenue_today = Decimal('0.00')
        completed_orders = 0
        cash_register = Decimal('0.00')
        net_profit = Decimal('0.00')
    
    active_orders = Order.objects.exclude(status__in=['completed', 'cancelled']).order_by('-created_at')
    workers = User.objects.filter(role='worker')
    products = Product.objects.all()

    context = {
        'revenue_today': revenue_today,
        'completed_orders': completed_orders,
        'cash_register': cash_register,
        'net_profit': net_profit,
        'active_orders': active_orders,
        'active_shift': active_shift,
        'workers': workers,
        'products': products,
    }
    return render(request, 'manager_dashboard.html', context)

@login_required
def create_order(request):
    if request.user.role not in ['admin', 'manager']:
        return redirect('role_redirect')
        
    if request.method == 'POST':
        form = OrderCreateForm(request.POST)
        if form.is_valid():
            order = form.save(commit=False)
            order.created_by = request.user
            order.status = 'new'
            order.calculate_total()
            order.save()
            messages.success(request, f"Заказ #{order.id} успешно создан!")
            return redirect('manager_dashboard')
    else:
        form = OrderCreateForm()
    
    # prepare recipe info for dynamic JS frontend if needed
    products = Product.objects.all()
    
    return render(request, 'manager_create_order.html', {'form': form, 'products': products})

@login_required
def update_order_status(request, pk):
    if request.user.role not in ['admin', 'manager']:
        return redirect('role_redirect')
        
    order = get_object_or_404(Order, pk=pk)
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'assign_workers' and order.status == 'new':
            try:
                # Сначала пробуем списать сырье
                order.deduct_ingredients()
                
                # Назначаем ВСЕХ рабочих автоматически
                workers = User.objects.filter(role='worker')
                order.workers.set(workers)
                order.status = 'in_production'
                order.save()
                
                messages.success(request, f"Заказ #{order.id}: Сырьё списано, производство начато (назначены все рабочие).")
            except ValueError as e:
                messages.error(request, str(e))
            except Exception as e:
                messages.error(request, f"Не удалось начать производство: {str(e)}")
                
        elif action == 'ready' and order.status == 'in_production':
            order.status = 'ready'
            order.save()
            messages.success(request, f"Заказ #{order.id} готов!")
            
        elif action == 'complete' and order.status == 'ready':
            order.mark_completed()
            messages.success(request, f"Заказ #{order.id} завершён! Долг оптовика увеличен.")
            
        elif action == 'cancel' and order.status in ['new', 'in_production', 'ready']:
            if order.status in ['in_production', 'ready']:
                order.return_ingredients()
                messages.info(request, f"Заказ #{order.id} отменён. Сырьё возвращено на склад (ручная корректировка опциональна).")
            else:
                messages.info(request, f"Заказ #{order.id} отменён.")
            order.status = 'cancelled'
            order.save()
            
    return redirect('manager_dashboard')

@login_required
def close_shift(request):
    if request.user.role not in ['admin', 'manager']:
        return redirect('role_redirect')
        
    active_shift = Shift.objects.filter(closed_at__isnull=True).first()
    
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'open' and not active_shift:
            Shift.objects.create(opened_by=request.user)
            messages.success(request, "Новая смена открыта!")
        elif action == 'close' and active_shift:
            try:
                # Manager might specify expenses
                expenses = request.POST.get('expenses', '0')
                active_shift.expenses = Decimal(expenses)
                active_shift.save()
                
                active_shift.close_shift()
                messages.success(request, "Смена закрыта! Зарплаты начислены, прибыль рассчитана.")
            except Exception as e:
                messages.error(request, f"Ошибка при закрытии смены: {str(e)}")
                
    return redirect('manager_dashboard')

@login_required
def worker_dashboard(request):
    if request.user.role != 'worker':
        return redirect('role_redirect')
        
    # Заказы, где этот рабочий либо назначен, либо все заказо в производстве (так как мы назначили всех)
    my_orders = Order.objects.filter(status__in=['in_production', 'ready', 'completed', 'cancelled']).order_by('-created_at')
    
    today = timezone.now().date()
    payrolls = Payroll.objects.filter(worker=request.user)
    today_earnings = payrolls.filter(date__date=today).aggregate(Sum('amount'))['amount__sum'] or Decimal('0.00')
    total_earnings = payrolls.aggregate(Sum('amount'))['amount__sum'] or Decimal('0.00')

    context = {
        'my_orders': my_orders,
        'today_earnings': today_earnings,
        'total_earnings': total_earnings,
        'payrolls': payrolls.order_by('-date'),
        'report_form': WorkerReportForm(),
    }
    return render(request, 'worker_dashboard.html', context)

@login_required
def submit_worker_report(request, pk):
    if request.user.role != 'worker':
        return redirect('role_redirect')
    
    order = get_object_or_404(Order, pk=pk)
    if order.status != 'in_production':
        messages.error(request, "Запись возможна только когда заказ 'В производстве'.")
        return redirect('worker_dashboard')
        
    if request.method == 'POST':
        form = WorkerReportForm(request.POST)
        if form.is_valid():
            quantity = form.cleaned_data['quantity']
            
            # --- Проверка: не пытаются ли сдать больше, чем нужно? ---
            total_produced_so_far = order.current_produced_quantity
            remaining_to_produce = order.quantity - total_produced_so_far
            
            if quantity > remaining_to_produce:
                messages.error(request, f"Ошибка: в заказе осталось сделать только {remaining_to_produce} шт. Вы не можете сдать {quantity} шт.")
                return redirect('worker_dashboard')
            # ---------------------------------------------------------
            
            OrderWorkLog.objects.create(
                order=order,
                worker=request.user,
                quantity=quantity
            )
            
            # --- Автоматическое пополнение готового склада ---
            product = order.product
            product.stock_quantity += quantity
            product.save()
            # -------------------------------------------------
            
            # Проверяем: сделано ли всё количество после текущего сохранения?
            total_produced = order.current_produced_quantity # это свойство автоматически считает сумму логов, включая текущий
            if total_produced >= order.quantity:
                # Автоматически завершаем заказ
                order.mark_completed()
                messages.success(request, f"Заказ #{order.id} полностью выполнен ({total_produced}/{order.quantity} шт)! Товар на складе, долг оптовика увеличен.")
            else:
                remaining = order.quantity - total_produced
                messages.success(request, f"Отчет принят: {quantity} шт. отправлено на склад. Осталось сделать: {remaining} шт.")
            
    return redirect('worker_dashboard')

@login_required
def wholesaler_dashboard(request):
    if request.user.role != 'wholesaler':
        return redirect('role_redirect')
        
    if not hasattr(request.user, 'wholesaler_profile'):
        return render(request, 'error.html', {'message': 'Профиль оптовика не найден.'})
        
    wholesaler = request.user.wholesaler_profile
    products = Product.objects.all()
    my_orders = Order.objects.filter(wholesaler=wholesaler).order_by('-created_at')
    
    if request.method == 'POST':
        product_id = request.POST.get('product_id')
        quantity = request.POST.get('quantity')
        if product_id and quantity:
            product = get_object_or_404(Product, pk=product_id)
            needed = int(quantity)
            
            # Теперь всегда создаем новый заказ, ничего со склада автоматически не списываем,
            # мы просто позволяем менеджеру позже (или рабочим) обработать его.
            # Если вам нужно, чтобы заказ сразу создавался как 'new' для рабочих:
            order = Order.objects.create(
                wholesaler=wholesaler,
                product=product,
                quantity=needed,
                status='new',
                created_by=request.user
            )
            order.calculate_total()
            order.save()
            messages.success(request, f"Заказ на {needed} шт. успешно оформлен и отправлен в работу!")
                
            return redirect('wholesaler_dashboard')
            
    context = {
        'wholesaler': wholesaler,
        'products': products,
        'my_orders': my_orders,
    }
    return render(request, 'wholesaler_dashboard.html', context)

@login_required
def wholesaler_repay(request):
    if request.user.role not in ['admin', 'manager', 'wholesaler']:
        # If manager does it on behalf of wholesaler, we can adapt.
        # But prompt says "Погашение долга: форма ввода суммы -> balance -= amount, создается Payment"
        return redirect('role_redirect')
        
    # Assuming manager repays via some view? The prompt says "Оптовик видит товары, может создавать заказы, видит свои долги и историю"
    # Actually manager or admin should process payment? Or wholesaler can just "pay" (simulator)?
    # Let's say manager creates payment, because it asks for active shift to be linked. 
    # Yes, Payment requires a shift! If wholesaler does it, is there an active shift? 
    # Let's make it a manager action, or wholesaler action? 
    # Let's say manager. "Касса: остаток, история смен"
    active_shift = Shift.objects.filter(closed_at__isnull=True).first()
    
    if request.method == 'POST':
        wholesaler_id = request.POST.get('wholesaler_id')
        amount = request.POST.get('amount')
        
        if not active_shift:
            messages.error(request, "Нет активной смены для приема оплат!")
            return redirect('manager_dashboard')
            
        if amount and Decimal(amount) > 0:
            if request.user.role == 'wholesaler':
                wholesaler = request.user.wholesaler_profile
            else:
                wholesaler = get_object_or_404(Wholesaler, pk=wholesaler_id)
                
            payment = Payment.objects.create(
                wholesaler=wholesaler,
                amount=Decimal(amount),
                shift=active_shift
            )
            messages.success(request, f"Долг уменьшен на {amount} ₸.")
            
            if request.user.role == 'wholesaler':
                return redirect('wholesaler_dashboard')
            return redirect('manager_dashboard')
            
    return redirect('role_redirect')

@login_required
def cash_history(request):
    if request.user.role not in ['admin', 'manager']:
        return redirect('role_redirect')
        
    shifts = Shift.objects.all().order_by('-opened_at')
    return render(request, 'cash_history.html', {'shifts': shifts})

from .forms import ManagerCreationForm, WorkerCreationForm, WholesalerCreationForm, RoleCreationForm, WorkerEditForm

@login_required
def create_manager(request):
    if request.user.role != 'admin':
        messages.error(request, "Только администратор может создавать менеджеров.")
        return redirect('role_redirect')
        
    if request.method == 'POST':
        form = ManagerCreationForm(request.POST)
        if form.is_valid():
            user = User.objects.create_user(
                username=form.cleaned_data['username'],
                password=form.cleaned_data['password'],
                first_name=form.cleaned_data['first_name'],
                last_name=form.cleaned_data['last_name'],
                role='manager',
                created_by=request.user
            )
            messages.success(request, f"Менеджер {user.username} успешно создан!")
            return redirect('manager_dashboard')
    else:
        form = ManagerCreationForm()
    
    return render(request, 'create_manager.html', {'form': form})

@login_required
def create_worker(request):
    if request.user.role not in ['admin', 'manager']:
        return redirect('role_redirect')
        
    if request.method == 'POST':
        form = WorkerCreationForm(request.POST)
        if form.is_valid():
            role_value = form.cleaned_data['role']
            custom_role = None
            if role_value.startswith('custom_'):
                db_role = 'manager'
                custom_role = CustomRole.objects.get(id=int(role_value.split('_')[1]))
            else:
                db_role = role_value

            user = User.objects.create_user(
                username=form.cleaned_data['username'],
                password=form.cleaned_data['password'],
                first_name=form.cleaned_data['first_name'],
                last_name=form.cleaned_data['last_name'],
                role=db_role,
                custom_role=custom_role,
                created_by=request.user
            )
            role_display = dict(form.fields['role'].choices).get(form.cleaned_data['role'])
            messages.success(request, f"Пользователь {user.username} ({role_display}) успешно создан!")
            return redirect('manager_dashboard')
    else:
        form = WorkerCreationForm()
    
    return render(request, 'create_worker.html', {'form': form})

@login_required
def create_role(request):
    if request.user.role not in ['admin', 'manager']:
        return redirect('role_redirect')

    if request.method == 'POST':
        form = RoleCreationForm(request.POST)
        if form.is_valid():
            role = form.save()
            messages.success(request, f"Новая роль '{role.name}' успешно создана!")
            # Вернуться обратно может либо в список сотрудников, либо куда-то еще
            return redirect('manager_workers') 
    else:
        form = RoleCreationForm()

    return render(request, 'create_role.html', {'form': form})

@login_required
def edit_worker(request, pk):
    if request.user.role not in ['admin', 'manager']:
        return redirect('role_redirect')

    worker = get_object_or_404(User, pk=pk)

    if request.method == 'POST':
        form = WorkerEditForm(request.POST, instance=worker)
        if form.is_valid():
            user = form.save(commit=False)

            role_value = form.cleaned_data['role']
            if role_value.startswith('custom_'):
                user.role = 'manager'
                user.custom_role = CustomRole.objects.get(id=int(role_value.split('_')[1]))
            else:
                user.role = role_value
                user.custom_role = None

            if form.cleaned_data.get('password'):
                user.set_password(form.cleaned_data['password'])

            user.save()
            messages.success(request, f"Пользователь {user.username} успешно обновлён!")
            return redirect('manager_workers')
    else:
        form = WorkerEditForm(instance=worker)

    return render(request, 'edit_worker.html', {'form': form, 'worker': worker})

@login_required
def delete_worker(request, pk):
    if request.user.role not in ['admin', 'manager']:
        return redirect('role_redirect')

    worker = get_object_or_404(User, pk=pk)

    if worker == request.user:
        messages.error(request, "Вы не можете удалить самого себя!")
        return redirect('manager_workers')

    if request.method == 'POST':
        username = worker.username
        worker.delete()
        messages.success(request, f"Пользователь {username} удалён!")
        return redirect('manager_workers')

    return render(request, 'delete_worker.html', {'worker': worker})

@login_required
def create_wholesaler(request):
    if request.user.role not in ['admin', 'manager']:
        return redirect('role_redirect')
        
    if request.method == 'POST':
        form = WholesalerCreationForm(request.POST)
        if form.is_valid():
            user = User.objects.create_user(
                username=form.cleaned_data['username'],
                password=form.cleaned_data['password'],
                first_name=form.cleaned_data['first_name'],
                last_name=form.cleaned_data['last_name'],
                role='wholesaler',
                created_by=request.user
            )
            Wholesaler.objects.create(
                user=user,
                name=form.cleaned_data['company_name'],
                phone=form.cleaned_data['phone']
            )
            messages.success(request, f"Оптовик {user.username} успешно создан!")
            return redirect('manager_dashboard')
    else:
        form = WholesalerCreationForm()
    
    return render(request, 'create_wholesaler.html', {'form': form})

@login_required
def manager_orders(request):
    if request.user.role not in ['admin', 'manager']:
        return redirect('role_redirect')
    orders = Order.objects.all().order_by('-created_at')
    return render(request, 'manager_orders.html', {'orders': orders})

@login_required
def manager_products(request):
    if request.user.role not in ['admin', 'manager']:
        return redirect('role_redirect')
    products = Product.objects.all()
    return render(request, 'manager_products.html', {'products': products})

@login_required
def manager_ingredients(request):
    if request.user.role not in ['admin', 'manager']:
        return redirect('role_redirect')
    ingredients = Ingredient.objects.all()
    # Получаем последние 5 приходов для быстрой справки
    latest_arrivals = IngredientArrival.objects.all().order_by('-timestamp')[:5]
    return render(request, 'manager_ingredients.html', {
        'ingredients': ingredients,
        'latest_arrivals': latest_arrivals
    })

@login_required
def ingredient_arrival_history(request):
    if request.user.role not in ['admin', 'manager']:
        return redirect('role_redirect')
    arrivals = IngredientArrival.objects.all().order_by('-timestamp')
    return render(request, 'manager_ingredient_arrival_history.html', {'arrivals': arrivals})

@login_required
def manager_wholesalers(request):
    if request.user.role not in ['admin', 'manager']:
        return redirect('role_redirect')
    wholesalers = Wholesaler.objects.all()
    return render(request, 'manager_wholesalers.html', {'wholesalers': wholesalers})

@login_required
def wholesaler_detail(request, pk):
    if request.user.role not in ['admin', 'manager']:
        return redirect('role_redirect')

    wholesaler = get_object_or_404(Wholesaler, pk=pk)
    payments = wholesaler.payments.all().order_by('-date')
    orders = wholesaler.orders.all().order_by('-created_at')

    # Build a combined history timeline
    history = []
    for order in orders:
        history.append({
            'date': order.created_at,
            'type': 'order',
            'description': f"Заказ #{order.id} — {order.product.name} ({order.quantity} шт)",
            'amount': order.total_price,
            'status': order.get_status_display(),
            'is_debt': True,
        })
    for payment in payments:
        history.append({
            'date': payment.date,
            'type': 'payment',
            'description': f"Оплата долга",
            'amount': payment.amount,
            'status': 'Оплачено',
            'is_debt': False,
        })

    history.sort(key=lambda x: x['date'], reverse=True)

    return render(request, 'wholesaler_detail.html', {
        'wholesaler': wholesaler,
        'payments': payments,
        'orders': orders,
        'history': history,
    })

@login_required
def manager_workers(request):
    if request.user.role not in ['admin', 'manager']:
        return redirect('role_redirect')

    if request.user.role == 'admin' or getattr(request.user, 'custom_role', None) is None:
        workers = User.objects.exclude(role='wholesaler').order_by('-date_joined')
    else:
        cr = request.user.custom_role
        allowed_roles = []
        if cr.can_view_workers:
            allowed_roles.append('worker')
        if cr.can_view_staff:
            allowed_roles.append('manager')
        if cr.can_view_users:
            allowed_roles.extend(['admin', 'manager', 'worker', 'wholesaler'])
            
        if not allowed_roles: 
            workers = User.objects.none()
        else:
            workers = User.objects.filter(role__in=allowed_roles).exclude(role='wholesaler').order_by('-date_joined')
            
    return render(request, 'manager_workers.html', {'workers': workers})

@login_required
def create_product(request):
    if request.user.role not in ['admin', 'manager']:
        return redirect('role_redirect')
    
    if request.method == 'POST':
        form = ProductForm(request.POST)
        formset = RecipeItemFormSet(request.POST)
        if form.is_valid() and formset.is_valid():
            product = form.save()
            formset.instance = product
            formset.save()
            messages.success(request, f"Товар {product.name} и его рецепт успешно созданы!")
            return redirect('manager_products')
    else:
        form = ProductForm()
        formset = RecipeItemFormSet()
    
    ingredients = Ingredient.objects.all()
    return render(request, 'manager_create_product.html', {
        'form': form, 
        'formset': formset,
        'ingredients': ingredients
    })

@login_required
def edit_product(request, pk):
    if request.user.role not in ['admin', 'manager']:
        return redirect('role_redirect')
    
    product = get_object_or_404(Product, pk=pk)
    
    if request.method == 'POST':
        form = ProductForm(request.POST, instance=product)
        formset = RecipeItemFormSet(request.POST, instance=product)
        if form.is_valid() and formset.is_valid():
            form.save()
            formset.save()
            messages.success(request, f"Товар '{product.name}' успешно обновлен!")
            return redirect('manager_products')
    else:
        form = ProductForm(instance=product)
        formset = RecipeItemFormSet(instance=product)
    
    ingredients = Ingredient.objects.all()
    return render(request, 'manager_create_product.html', {
        'form': form, 
        'formset': formset,
        'ingredients': ingredients,
        'is_edit': True,
        'product': product
    })

@login_required
def manager_ready_stock(request):
    if request.user.role not in ['admin', 'manager']:
        return redirect('role_redirect')
    products = Product.objects.all().order_by('name')
    return render(request, 'manager_ready_stock.html', {'products': products})

@login_required
def manager_add_ready_stock(request):
    if request.user.role not in ['admin', 'manager']:
        return redirect('role_redirect')
    if request.method == 'POST':
        product_id = request.POST.get('product_id')
        quantity = request.POST.get('quantity')
        if product_id and quantity:
            product = get_object_or_404(Product, pk=product_id)
            try:
                product.produce(quantity)
                messages.success(request, f"Успешно произведено {quantity} шт. товара '{product.name}' на готовый склад! Сырье списано.")
            except ValueError as e:
                messages.error(request, str(e))
            except Exception as e:
                messages.error(request, f"Ошибка при производстве: {str(e)}")
        return redirect('manager_ready_stock')
    return redirect('manager_ready_stock')

@login_required
def create_ingredient(request):
    if request.user.role not in ['admin', 'manager']:
        return redirect('role_redirect')
    if request.method == 'POST':
        form = IngredientForm(request.POST)
        if form.is_valid():
            i = form.save()
            messages.success(request, f"Сырье {i.name} успешно добавлено!")
            return redirect('manager_ingredients')
    else:
        form = IngredientForm()
    return render(request, 'manager_create_ingredient.html', {'form': form})

@login_required
def add_ingredient_stock(request, pk):
    if request.user.role not in ['admin', 'manager']:
        return redirect('role_redirect')
        
    ingredient = get_object_or_404(Ingredient, pk=pk)
    
    if request.method == 'POST':
        form = IngredientAddStockForm(request.POST)
        if form.is_valid():
            amount = form.cleaned_data['amount']
            total_cost = form.cleaned_data.get('total_cost')
            price_per_unit = form.cleaned_data.get('price_per_unit')
            
            # Если ввели общую сумму, вычисляем цену за единицу
            if total_cost and amount:
                price = (total_cost / amount).quantize(Decimal('0.01'))
            elif price_per_unit:
                price = price_per_unit
            else:
                price = Decimal('0.00')
            
            # 1. Обновляем общий баланс ингредиента
            ingredient.quantity += Decimal(str(amount))
            ingredient.save()
            
            # 2. Создаем партию прихода для FIFO
            IngredientArrival.objects.create(
                ingredient=ingredient,
                quantity=amount,
                remaining_quantity=amount,
                price=price
            )
            
            messages.success(request, f"Успешно добавлено {amount} {ingredient.get_unit_display()} к запасам '{ingredient.name}'.")
            return redirect('manager_ingredients')
    else:
        form = IngredientAddStockForm()
        
    return render(request, 'manager_add_ingredient_stock.html', {'form': form, 'ingredient': ingredient})

@login_required
def edit_ingredient(request, pk):
    if request.user.role not in ['admin', 'manager']:
        return redirect('role_redirect')

    ingredient = get_object_or_404(Ingredient, pk=pk)

    if request.method == 'POST':
        form = IngredientForm(request.POST, instance=ingredient)
        if form.is_valid():
            form.save()
            messages.success(request, f"Сырье '{ingredient.name}' успешно обновлено!")
            return redirect('manager_ingredients')
    else:
        form = IngredientForm(instance=ingredient)

    return render(request, 'edit_ingredient.html', {'form': form, 'ingredient': ingredient})

@login_required
def delete_ingredient(request, pk):
    if request.user.role not in ['admin', 'manager']:
        return redirect('role_redirect')

    ingredient = get_object_or_404(Ingredient, pk=pk)

    if ingredient.quantity > 0:
        messages.error(request, f"Нельзя удалить '{ingredient.name}' — на складе ещё {ingredient.quantity} {ingredient.get_unit_display()}. Сначала спишите остатки до 0.")
        return redirect('manager_ingredients')

    if request.method == 'POST':
        name = ingredient.name
        ingredient.delete()
        messages.success(request, f"Сырье '{name}' удалено!")
        return redirect('manager_ingredients')

    return render(request, 'delete_ingredient.html', {'ingredient': ingredient})

@login_required
def delete_product(request, pk):
    if request.user.role not in ['admin', 'manager']:
        return redirect('role_redirect')
    product = get_object_or_404(Product, pk=pk)
    name = product.name
    product.delete()
    messages.success(request, f"Товар '{name}' успешно удален.")
    return redirect('manager_products')
