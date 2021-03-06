from django.conf import settings
from django.db import models
from django.shortcuts import reverse
from django_countries.fields import CountryField


CATEGORY_CHOICES = (
	('S', 'Shirt'),
	('SW', 'Sports Wear'),
	('OW', 'Outwear')
)

LABEL_CHOICES = (
	('P', 'primary'),
	('S', 'secondary'),
	('D', 'danger')
)

class Item(models.Model):
	title = models.CharField(max_length=100)
	price = models.FloatField()
	discount_price = models.FloatField(blank=True, null=True)
	category = models.CharField(choices=CATEGORY_CHOICES, max_length=2)
	label = models.CharField(choices=LABEL_CHOICES, max_length=1)
	slug = models.SlugField()
	description = models.TextField()
	image = models.ImageField()

	def __str__(self):
		return self.title

	def get_absolute_url(self):
		return reverse("core:product", kwargs={
			'slug': self.slug
		})

	def get_add_to_cart_url(self):
		return reverse("core:add-to-cart", kwargs={
			'slug': self.slug
		})

	def get_remove_from_cart_url(self):
		return reverse("core:remove-from-cart", kwargs={
			'slug': self.slug
		})


class OrderItem(models.Model):
	user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
	ordered = models.BooleanField(default=False)
	item = models.ForeignKey(Item, on_delete=models.CASCADE)
	quantity = models.IntegerField(default=1)

	def __str__(self):
		return f"{self.quantity} of {self.item.title}"

	def get_total_item_price(self):
		return self.quantity * self.item.price

	def get_total_discount_item_price(self):
		return self.quantity * self.item.discount_price

	def get_amount_saved(self):
		return self.get_total_item_price() - self.get_total_discount_item_price()

	def get_final_price(self):
		if self.item.discount_price:
			return self.get_total_discount_item_price()
		return self.get_total_item_price()


class Order(models.Model):
	user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
	items = models.ManyToManyField(OrderItem)
	start_date = models.DateTimeField(auto_now_add=True)
	ordered_date = models.DateTimeField()
	ordered = models.BooleanField(default=False)
	reference_id = models.CharField(max_length=20)
	billing_address = models.ForeignKey('BillingAddress',
		on_delete=models.SET_NULL, blank=True, null=True)
	coupon = models.ForeignKey('Coupon',
		on_delete=models.SET_NULL, blank=True, null=True)
	being_delivered = models.BooleanField(default=False)
	received = models.BooleanField(default=False)
	refund_requested = models.BooleanField(default=False)
	refund_granted = models.BooleanField(default=False)


	def __str__(self):
		return self.user.username

	def get_total(self):
		total = 0
		for order_item in self.items.all():
			total += order_item.get_final_price()
		if self.coupon:
			total -= self.coupon.amount
		return round(total, 2)

'''
Change the Billing address to adress and add a type field to determine the type
Add a address_choice tuple to select the type of address - billing or shipping
Add a default boolean field to set as a default address for billing or shipping
Make certain changes in Order for billing address
Add related_name as billing_address or shipping_address to make specific
Change imports and specific places in views
Give address_type when assigning billing address in checkout view
Make migrations
'''


class BillingAddress(models.Model):
	user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
	street_address = models.CharField(max_length=100)
	apartment_address = models.CharField(max_length=100)
	country = CountryField(multiple=False)
	zip = models.CharField(max_length=100)

	def __str__(self):
		return self.user.username


'''
1.
attributes: user, stripe_charge_id, amount, timestamp
Return username as string on calling the class
Make payment model with attributes: made_by, made_on, order_id/reference_id, amount, checksum
Make certain changes in settings and then create views
'''

class Payment(models.Model):
	stripe_charge_id = models.CharField(max_length=50)
	user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True)
	amount = models.FloatField()
	timestamp = models.DateTimeField(auto_now_add=True)

	def __str__(self):
		return self.user.username


class Coupon(models.Model):
	code = models.CharField(max_length=20)
	amount = models.FloatField()

	def __str__(self):
		return self.code


class Refund(models.Model):
	order = models.ForeignKey(Order, on_delete=models.CASCADE)
	reason = models.TextField ()
	email = models.EmailField()
	accepted = models.BooleanField(default=False)

	def __str__(self):
		return f"{self.pk}"
