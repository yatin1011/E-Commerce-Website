from django.conf import settings
from django.contrib import messages
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, DetailView, View
from django.utils import timezone
from .forms import CheckoutForm, CouponForm, RefundForm
from .models import Item, OrderItem, Order, BillingAddress, Coupon, Refund, Payment
import string
import random
import stripe

stripe.api_key = settings.STRIPE_SECRET_KEY



def create_reference_id():
	return ''.join(random.choices(string.ascii_lowercase + string.digits, k=20))

def products(request):
	context = { 
		'items': Item.objects.all()
	}
	return render(request, "products.html", context)

class CheckoutView(View):
	def get(self, *args, **kwargs):
		try:
			order = Order.objects.get(user=self.request.user, ordered=False)
			form = CheckoutForm()
			context = {
				'form': form,
				'couponform': CouponForm(),
				'order': order
			}
			return render(self.request, "checkout.html", context)
		except ObjectDoesNotExist:
			messages.error(self.request, "You do not have an active order.")
			return redirect('core:checkout')
		# Form
		

	def post(self, *args, **kwargs):
		form = CheckoutForm(self.request.POST or None)
		try:
			order = Order.objects.get(user=self.request.user, ordered=False)
			if form.is_valid():
				street_address = form.cleaned_data.get('street_address')
				apartment_address = form.cleaned_data.get('apartment_address')
				country = form.cleaned_data.get('country')
				zip = form.cleaned_data.get('zip')
				# TODO: Add functionality for these fields
				# same_shipping_address = form.cleaned_data.get('same_shipping_address')
				# save_info = form.cleaned_data.get('save_info')
				payment_option = form.cleaned_data.get('payment_option')
				billing_address = BillingAddress(
					user = self.request.user,
					street_address = street_address,
					apartment_address = apartment_address,
					country = country,
					zip = zip
				)
				billing_address.save()
				order.billing_address = billing_address
				order.save()
				# TODO: Add a redirect to the selected payment option
				return redirect("core:payment")
			messages.warning(self.request, "Failed Checkout")
			return redirect('core:checkout')
			return render(self.request, "order-summary.html", context)
		except ObjectDoesNotExist:
			messages.error(self.request, "You do not have an active order.")
			return redirect('core:order-summary')
		

# Map the urls for payment page and create a slug (payment_option) to choose b/w stripe and paypal

# Now submitting form calls the same view (action=".")
# Define the post function to handle post request
# Search for stripe api -> charges -> create a charge
# Basically google how to implement stripe payment option

# Make sure that one cannot g to payment view without billing address
# Assign a reference id when an order is placed and payment is done

class PaymentView(View):
	def get(self, *args, **kwargs):
		order = Order.objects.get(user=self.request.user, ordered=False)
		context = {
			'order': order,
			'STRIPE_PUBLIC_KEY': settings.STRIPE_PUBLIC_KEY
		}
		return render(self.request, 'payment.html', context)

	def post(self, *args, **kwargs):
		order = Order.objects.get(user=self.request.user, ordered=False)
		amount = int(order.get_total() * 100)
		token = self.request.POST.get('stripeToken')

		try:
			# Use Stripe's library to make requests...
			charge = stripe.Charge.create(
				amount=str(amount),
				currency="usd",
				source=token
				# description="My First Test Charge (created for API docs)",
			)

			print(charge)

			payment = Payment()
			payment.stripe_charge_id = charge['id']
			payment.user = self.request.user
			payment.amount = order.get_total()
			payment.save()

			order.ordered = True
			order.payment = payment
			order.save()

			messages.success(self.request, "Your order has been placed.")
			return redirect('/')

		except stripe.error.CardError as e:
			# Since it's a decline, stripe.error.CardError will be caught
			messages.error(self.request, f"{e.user_message}")
			return redirect('/')
		except stripe.error.RateLimitError as e:
			# Too many requests made to the API too quickly
			messages.error(self.request, "Too many requests made to the API too quickly.")
			return redirect('/')
		except stripe.error.InvalidRequestError as e:
			# Invalid parameters were supplied to Stripe's API
			messages.error(self.request, "Invalid parameters.")
			return redirect('/')
		except stripe.error.AuthenticationError as e:
			# Authentication with Stripe's API failed
			# (maybe you changed API keys recently)
			messages.error(self.request, "Not Authenticated.")
			return redirect('/')
		except stripe.error.APIConnectionError as e:
			# Network communication with Stripe failed
			messages.error(self.request, "Network error.")
			return redirect('/')
		except stripe.error.StripeError as e:
			# Display a very generic error to the user, and maybe send
			# yourself an email
			messages.error(self.request, "Something went wrong, you were not charged, please try again.")
			return redirect('/')
		except Exception as e:
			# Something else happened, completely unrelated to Stripe
			messages.error(self.request, "A serious error has occured. We have been notified.")
			return redirect('/')

		


class HomeView(ListView):
	model = Item
	paginate_by = 8
	template_name = "home.html"

class OrderSummaryView(LoginRequiredMixin, View):
	def get(self, *args, **kwargs):
		try:
			order = Order.objects.get(user=self.request.user, ordered=False)
			context = {
				'object': order
			}
			return render(self.request, "order-summary.html", context)
		except ObjectDoesNotExist:
			messages.error(self.request, "You do not have an active order.")
			return redirect('/')

class ItemDetailView(DetailView):
	model = Item
	template_name = "product.html"

@login_required
def add_to_cart(request, slug):
	item = get_object_or_404(Item, slug=slug)
	order_item, created = OrderItem.objects.get_or_create(
		item=item,
		user=request.user,
		ordered=False
	)
	order_qs = Order.objects.filter(user=request.user, ordered=False)

	if order_qs.exists():
		order = order_qs[0]
		# Check if the order item is in the order
		if order.items.filter(item__slug=item.slug).exists():
			order_item.quantity += 1
			order_item.save()
			messages.info(request, "This item quantity was updated.")
			return redirect("core:order-summary")
		else:
			order.items.add(order_item)
			messages.info(request, "This item was added to the cart.")
			return redirect("core:product", slug=slug)
	else:
		ordered_date = timezone.now()
		order = Order.objects.create(user=request.user, ordered_date=ordered_date)
		order.items.add(order_item)
		messages.info(request, "This item was added to the cart.")
		return redirect("core:product", slug=slug)

@login_required
def remove_from_cart(request, slug):
	item = get_object_or_404(Item, slug=slug)
	order_qs = Order.objects.filter(
		user=request.user,
		ordered=False
	)

	if order_qs.exists():
		order = order_qs[0]
		# Check if the order item is in the order
		if order.items.filter(item__slug=item.slug).exists():
			order_item = OrderItem.objects.filter(
				item=item,
				user=request.user,
				ordered=False
			)[0]
			order.items.remove(order_item)
			messages.info(request, "This item was removed from your cart.")
			return redirect("core:order-summary") 
		else:
			messages.info(request, "This item was not in your cart.")
			return redirect("core:product", slug=slug)
	else:
		messages.info(request, "You do not have an active order.")
		return redirect("core:product", slug=slug)
	

@login_required
def remove_single_item_from_cart(request, slug):
	item = get_object_or_404(Item, slug=slug)
	order_qs = Order.objects.filter(
		user=request.user,
		ordered=False
	)

	if order_qs.exists():
		order = order_qs[0]
		# Check if the order item is in the order
		if order.items.filter(item__slug=item.slug).exists():
			order_item = OrderItem.objects.filter(
				item=item,
				user=request.user,
				ordered=False
			)[0]
			if order_item.quantity > 1:
				order_item.quantity -= 1
				order_item.save()
				messages.info(request, "This item quantity was updated.")
			else:
				order.items.remove(order_item)
				messages.info(request, "This item was removed from your cart.")
			return redirect("core:order-summary")
		else:
			messages.info(request, "This item was not in your cart.")
			return redirect("core:product", slug=slug)
	else:
		messages.info(request, "You do not have an active order.")
		return redirect("core:product", slug=slug)


'''
2.
Create CheckoutView to call stripe api and create checkout session
'''


def get_coupon(request, code):
	try:
		coupon = Coupon.objects.get(code=code)
		return coupon
	except ObjectDoesNotExist:
		messages.error(request, "This coupon does not exist.")
		return redirect('core:checkout')

class AddCouponView(View):
	def post(self, *args, **kwargs):
		form = CouponForm(self.request.POST or None)
		if form.is_valid():
			try:
				code = form.cleaned_data.get('code')
				order = Order.objects.get(user=self.request.user, ordered=False)
				order.coupon = get_coupon(self.request, code)
				order.save()
				messages.success(self.request, "Coupon code has been added.")
				return redirect('core:checkout')
			except ObjectDoesNotExist:
				messages.info(self.request, "You do not have an active order.")
				return redirect('core:checkout')


# Them store the refund using refund model    refund = Refund()   and then the operations
# Now build the html form for refund in a new template
# We need a get function/request to render that html page with context = form 


class RequestRefundView(View):
	def get(self, request, *args, **kwargs):
		form = RefundForm()
		context = {
			'form': form
		}
		return render(request, "request-refund.html", context)

	def post(self, *args, **kwargs):
		form = RefundForm(self.request.POST)
		if form.is_valid():
			reference_id = form.cleaned_data.get('reference_id')
			email = form.cleaned_data.get('email')
			reason = form.cleaned_data.get('reason')
			try:
				order = Order.objects.get(reference_id=reference_id)
				order.refund_requested = True
				order.save()

				refund = Refund()
				refund.order = order
				refund.reason = reason
				refund.email = email
				refund.save()

				messages.info(self.request, "Your request was recieved.")
				return redirect('core:request-refund')

			except ObjectDoesNotExist:
				messages.info(self.request, "You do not have such order.")
				return redirect('core:request-refund')


'''
Create a orders view to show all of users orders
Add a refund option if it is within time limit
'''

# TODO: Check if after adding an item to cart after already completing the order adds 1 item
# and creates a new order item or adds many items as previous order
# Add condition for order-snippet coupon code form to only appear in checkout form