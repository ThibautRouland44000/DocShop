from pprint import pprint

import stripe
from django.forms import modelformset_factory
from django.http import HttpResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

from accounts.models import Shopper, ShippingAdress
from store.forms import OrderForm
from store.models import Product, Cart, Order
from shop import settings

stripe.api_key = settings.STRIPE_API_KEY


def index(request):
    products = Product.objects.all()
    return render(request, 'store/index.html', context={"products": products})

def product_detail(request, slug):
    product = get_object_or_404(Product, slug=slug)
    return render(request, 'store/detail.html', context={"product": product})

def add_to_cart(request, slug):
    user = request.user
    product = get_object_or_404(Product, slug=slug)
    cart, _ = Cart.objects.get_or_create(user=user)
    order, created = Order.objects.get_or_create(user=user, ordered=False, product=product)

    if created:
        cart.orders.add(order)
        cart.save()
    else:
        order.quantity +=1
        order.save()

    return redirect(reverse("product", kwargs={"slug": slug}))

def cart(request):
    cart = get_object_or_404(Cart, user=request.user)
    OrderFormSet = modelformset_factory(Order, form=OrderForm, extra=0)
    formset = OrderFormSet(queryset=Order.objects.filter(user=request.user, ordered=False))
    return render(request, 'store/cart.html', context={"orders": cart.orders.all(),"forms":formset})

def update_quantities(request):
    OrderFormSet = modelformset_factory(Order, form=OrderForm, extra=0)
    formset = OrderFormSet(request.POST, queryset=Order.objects.filter(user=request.user, ordered=False))
    if formset.is_valid():
        formset.save()

    return redirect('cart')

def create_checkout_session(request):
    cart = request.user.cart

    line_items = [{"price": order.product.stripe_id, "quantity": order.quantity} for order in cart.orders.all()]

    session = stripe.checkout.Session.create(
        locale="fr",
        payment_method_types=['card'],
        line_items=line_items,
        mode='payment',
        customer_email=request.user.email,
        shipping_address_collection={"allowed_countries": ["FR", "US", "CA"]},
        success_url=request.build_absolute_uri(reverse('checkout-success')),
        cancel_url='http://127.0.0.1:8000',
    )

    return redirect(session.url, code=303)

def checkout_success(request):
    return render(request, 'store/success.html')

def delete_cart(request):
    cart = request.user.cart
    if cart:
        cart.delete()
    return redirect('index')

@csrf_exempt
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META['HTTP_STRIPE_SIGNATURE']
    endpoint_secret = "whsec_de13345002dc7bc7b5b2eee23a56e5094d4bf744e6752c19280ec8d665649f35"
    event = None

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, endpoint_secret
        )
    except ValueError as e:
        # Invalid payload
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError as e:
        # Invalid signature
        return HttpResponse(status=400)
    if event['type'] == 'checkout.session.completed':
        data = event['data']['object']
        try:
            user = get_object_or_404(Shopper, email=data["customer_details"]["email"])
            user_email = data['customer_details']['email']
        except KeyError:
            return HttpResponse("Invalid user email", status=404)

        completed_order(data=data, user=user)
        save_shipping_adress(data=data, user=user)
        return HttpResponse(status=200)

    # Passed signature verification
    return HttpResponse(status=200)

def completed_order(data, user):
    user.stripe_id = data["customer"]
    user.cart.delete()
    user.save()
    return HttpResponse(status=200)

def save_shipping_adress(data, user):
    try:
        address = data["shipping"]["adress"]
        name = data["shipping"]["name"]
        city = address["city"]
        country = address["country"]
        line1 = address["line1"]
        line2 = address["line2"]
        zip_code = address["postal_code"]
    except KeyError:
        return HttpResponse(status=400)

    ShippingAdress.objects.get_or_create(user=user,
                                         name=name,
                                         city=city,
                                         country=country.lower(),
                                         adress_1=line1,
                                         adress_2=line2 or "",
                                         zip_code=zip_code)

    return HttpResponse(status=200)

