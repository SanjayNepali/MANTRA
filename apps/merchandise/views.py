# apps/merchandise/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.generic import ListView, DetailView
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Q, F
from django.core.paginator import Paginator
from django.views.generic import TemplateView
from datetime import timedelta
from django.db.models import Count, Sum
from django.utils import timezone

from apps.merchandise.models import Merchandise, MerchandiseCategory, MerchandiseOrder, OrderItem
from apps.merchandise.forms import MerchandiseCreateForm, OrderForm
from algorithms.integration import get_user_recommendations


class MerchandiseListView(TemplateView):
    template_name = 'merchandise/list.html'

    def get_context_data(self, **kwargs):
        from django.utils import timezone
        from datetime import timedelta
        context = super().get_context_data(**kwargs)
        now = timezone.now()

        base_qs = Merchandise.objects.filter(
            status='available'
        ).select_related('celebrity')

        # ✅ FIX: use 'order_items' instead of 'orders'
        context['top_items'] = base_qs.annotate(
            sales_count=Count('order_items')
        ).order_by('-sales_count')[:10]

        # ✅ FIX: same here
        thirty_days_ago = now - timedelta(days=30)
        context['trending_items'] = base_qs.filter(
            created_at__gte=thirty_days_ago
        ).annotate(
            sales_count=Count('order_items')
        ).order_by('-sales_count')[:10]

        # AI-Powered Merchandise Recommendations
        if self.request.user.is_authenticated and self.request.user.user_type == 'fan':
            try:
                # Get AI recommendations for merchandise
                recommendations = get_user_recommendations(
                    self.request.user,
                    recommendation_type='merchandise',
                    limit=10,
                    use_cache=True
                )

                if recommendations and 'merchandise' in recommendations:
                    context['recommended_items'] = recommendations['merchandise'][:10]
                else:
                    # Fallback to followed celebrities' merchandise
                    followed_celebs = self.request.user.following.filter(
                        following__user_type='celebrity'
                    ).values_list('following_id', flat=True)
                    context['recommended_items'] = base_qs.filter(
                        celebrity_id__in=followed_celebs
                    ).order_by('-created_at')[:10]
            except Exception as e:
                print(f"Error getting merchandise recommendations: {e}")
                # Fallback
                followed_celebs = self.request.user.following.filter(
                    following__user_type='celebrity'
                ).values_list('following_id', flat=True)
                context['recommended_items'] = base_qs.filter(
                    celebrity_id__in=followed_celebs
                ).order_by('-created_at')[:10]
        else:
            context['recommended_items'] = context['top_items']

        queryset = base_qs
        category = self.request.GET.get('category')
        if category:
            queryset = queryset.filter(category__slug=category)
        context['current_category'] = category

        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(description__icontains=search) |
                Q(celebrity__username__icontains=search)
            )
        context['search_query'] = search

        sort = self.request.GET.get('sort', '-created_at')
        if sort == 'price_low':
            queryset = queryset.order_by('price')
        elif sort == 'price_high':
            queryset = queryset.order_by('-price')
        elif sort == 'popular':
            # ✅ FIX: same annotation correction
            queryset = queryset.annotate(
                sales_count=Count('order_items')
            ).order_by('-sales_count')
        else:
            queryset = queryset.order_by('-created_at')
        context['current_sort'] = sort

        paginator = Paginator(queryset, 12)
        page_number = self.request.GET.get('page')
        context['items'] = paginator.get_page(page_number)
        context['categories'] = MerchandiseCategory.objects.all()

        return context


class MerchandiseDetailView(DetailView):
    """View merchandise details"""
    model = Merchandise
    template_name = 'merchandise/detail.html'
    context_object_name = 'product'
    slug_field = 'slug'
    slug_url_kwarg = 'slug'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        product = self.object
        context['merchandise'] = product

        # Increment views
        if hasattr(product, 'views_count'):
            product.views_count = F('views_count') + 1
            product.save(update_fields=['views_count'])

        # Calculate final price
        if self.request.user.is_authenticated and hasattr(product, 'get_final_price'):
            context['final_price'] = product.get_final_price(self.request.user)
        else:
            context['final_price'] = getattr(product, 'price', 0)

        # Related products
        context['related_products'] = Merchandise.objects.filter(
            celebrity=product.celebrity,
            status='available'
        ).exclude(id=product.id)[:4]

        return context

@login_required
def create_merchandise(request):
    """Create merchandise (celebrities only)"""
    if request.user.user_type != 'celebrity':
        messages.error(request, 'Only celebrities can create merchandise')
        return redirect('merchandise_list')
    
    if request.method == 'POST':
        form = MerchandiseCreateForm(request.POST, request.FILES)
        
        if form.is_valid():
            merchandise = form.save(commit=False)
            merchandise.celebrity = request.user
            merchandise.save()
            
            messages.success(request, 'Merchandise created successfully!')
            return redirect('merchandise_detail', slug=merchandise.slug)
    else:
        form = MerchandiseCreateForm()
    
    return render(request, 'merchandise/create.html', {'form': form})


@login_required
def add_to_cart(request, slug):
    """Add merchandise to cart"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    product = get_object_or_404(Merchandise, slug=slug, status='available')
    quantity = int(request.POST.get('quantity', 1))
    
    if hasattr(product, 'stock_quantity') and quantity > product.stock_quantity:
        return JsonResponse({'error': 'Not enough stock'}, status=400)
    
    # Get or create cart in session
    cart = request.session.get('cart', {})
    product_id = str(product.id)
    
    # Get final price
    if hasattr(product, 'get_final_price'):
        price = float(product.get_final_price(request.user))
    else:
        price = float(product.price) if hasattr(product, 'price') else 0
    
    # Get image URL
    image_url = ''
    if hasattr(product, 'primary_image') and product.primary_image:
        image_url = product.primary_image.url
    elif hasattr(product, 'image') and product.image:
        image_url = product.image.url
    
    if product_id in cart:
        cart[product_id]['quantity'] += quantity
    else:
        cart[product_id] = {
            'name': product.name,
            'price': price,
            'quantity': quantity,
            'image': image_url
        }
    
    request.session['cart'] = cart
    request.session.modified = True
    
    return JsonResponse({
        'status': 'success',
        'cart_items': len(cart),
        'message': f'{product.name} added to cart'
    })


@login_required
def view_cart(request):
    """View shopping cart"""
    cart = request.session.get('cart', {})
    
    # Calculate totals
    total = 0
    for item_id, item in cart.items():
        item['subtotal'] = item['price'] * item['quantity']
        total += item['subtotal']
    
    context = {
        'cart': cart,
        'total': total
    }
    
    return render(request, 'merchandise/cart.html', context)


@login_required
def remove_from_cart(request, product_id):
    """Remove item from cart"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    cart = request.session.get('cart', {})
    product_id_str = str(product_id)
    
    if product_id_str in cart:
        del cart[product_id_str]
        request.session['cart'] = cart
        request.session.modified = True
        
        return JsonResponse({
            'status': 'success',
            'message': 'Item removed from cart',
            'cart_items': len(cart)
        })
    else:
        return JsonResponse({'error': 'Item not in cart'}, status=404)


@login_required
def update_cart_quantity(request, product_id):
    """Update cart item quantity"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    cart = request.session.get('cart', {})
    product_id_str = str(product_id)
    quantity = int(request.POST.get('quantity', 1))
    
    if quantity < 1:
        return JsonResponse({'error': 'Invalid quantity'}, status=400)
    
    if product_id_str in cart:
        # Check stock
        try:
            product = Merchandise.objects.get(id=product_id)
            if hasattr(product, 'stock_quantity') and quantity > product.stock_quantity:
                return JsonResponse({'error': 'Not enough stock'}, status=400)
        except Merchandise.DoesNotExist:
            return JsonResponse({'error': 'Product not found'}, status=404)
        
        cart[product_id_str]['quantity'] = quantity
        cart[product_id_str]['subtotal'] = cart[product_id_str]['price'] * quantity
        
        request.session['cart'] = cart
        request.session.modified = True
        
        # Calculate new total
        total = sum(item['price'] * item['quantity'] for item in cart.values())
        
        return JsonResponse({
            'status': 'success',
            'subtotal': cart[product_id_str]['subtotal'],
            'total': total
        })
    else:
        return JsonResponse({'error': 'Item not in cart'}, status=404)


@login_required
def checkout(request):
    """Checkout process"""
    cart = request.session.get('cart', {})
    
    if not cart:
        messages.error(request, 'Your cart is empty')
        return redirect('merchandise_list')
    
    if request.method == 'POST':
        form = OrderForm(request.POST)
        
        if form.is_valid():
            # Calculate total
            total = 0
            for item_id, item in cart.items():
                total += item['price'] * item['quantity']
            
            # Create order
            order = form.save(commit=False)
            order.user = request.user
            order.total_amount = total
            order.save()
            
            # Create order items
            for item_id, item in cart.items():
                merchandise = Merchandise.objects.get(id=item_id)
                OrderItem.objects.create(
                    order=order,
                    merchandise=merchandise,
                    quantity=item['quantity'],
                    price=item['price']
                )
                
                # Update stock atomically
                if hasattr(merchandise, 'stock_quantity'):
                    merchandise.stock_quantity = F('stock_quantity') - item['quantity']
                if hasattr(merchandise, 'total_sold'):
                    merchandise.total_sold = F('total_sold') + item['quantity']
                merchandise.save()
            
            # Clear cart
            request.session['cart'] = {}
            request.session.modified = True
            
            # Award points
            if hasattr(request.user, 'add_points'):
                request.user.add_points(15, 'Merchandise purchase')
            
            messages.success(request, 'Order placed successfully!')
            return redirect('order_detail', order_id=order.id)
    else:
        form = OrderForm()
    
    # Calculate total for display
    total = sum(item['price'] * item['quantity'] for item in cart.values())
    
    context = {
        'form': form,
        'cart': cart,
        'total': total
    }
    
    return render(request, 'merchandise/checkout.html', context)


@login_required
def order_detail(request, order_id):
    """View order details"""
    order = get_object_or_404(
        MerchandiseOrder,
        id=order_id,
        user=request.user
    )
    
    return render(request, 'merchandise/order_detail.html', {'order': order})


@login_required
def my_orders(request):
    """View user's orders"""
    orders = MerchandiseOrder.objects.filter(
        user=request.user
    ).select_related('user').prefetch_related('items__merchandise').order_by('-created_at')
    
    # Filter by status if requested
    status = request.GET.get('status')
    if status:
        orders = orders.filter(order_status=status)
    
    paginator = Paginator(orders, 10)
    page = request.GET.get('page')
    orders = paginator.get_page(page)
    
    context = {
        'orders': orders,
        'status_filter': status
    }
    
    return render(request, 'merchandise/my_orders.html', context)


@login_required
def cancel_order(request, order_id):
    """Cancel an order"""
    order = get_object_or_404(
        MerchandiseOrder,
        id=order_id,
        user=request.user
    )
    
    # Can only cancel pending or processing orders
    if order.order_status not in ['pending', 'processing']:
        messages.error(request, 'This order cannot be cancelled')
        return redirect('order_detail', order_id=order.id)
    
    if request.method == 'POST':
        # Restore stock
        for item in order.items.all():
            merchandise = item.merchandise
            if hasattr(merchandise, 'stock_quantity'):
                merchandise.stock_quantity = F('stock_quantity') + item.quantity
            if hasattr(merchandise, 'total_sold'):
                merchandise.total_sold = F('total_sold') - item.quantity
            merchandise.save()
        
        # Update order status
        order.order_status = 'cancelled'
        order.save()
        
        messages.success(request, 'Order cancelled successfully')
        return redirect('order_detail', order_id=order.id)
    
    return render(request, 'merchandise/cancel_order.html', {'order': order})


@login_required
def track_order(request, order_id):
    """Track order status"""
    order = get_object_or_404(
        MerchandiseOrder,
        id=order_id,
        user=request.user
    )
    
    # Order status timeline
    status_timeline = [
        {'status': 'pending', 'label': 'Order Placed', 'completed': True},
        {'status': 'processing', 'label': 'Processing', 'completed': order.order_status in ['processing', 'shipped', 'delivered']},
        {'status': 'shipped', 'label': 'Shipped', 'completed': order.order_status in ['shipped', 'delivered']},
        {'status': 'delivered', 'label': 'Delivered', 'completed': order.order_status == 'delivered'},
    ]
    
    context = {
        'order': order,
        'status_timeline': status_timeline
    }
    
    return render(request, 'merchandise/track_order.html', context)