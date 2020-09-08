from django.contrib.auth.models import User
from django.db import models
from django.core.cache import cache
from geopy import distance

from foodcartapp.utils import fetch_coordinates


class Restaurant(models.Model):
    name = models.CharField('название', max_length=50)
    address = models.CharField('адрес', max_length=100, blank=True)
    contact_phone = models.CharField('контактный телефон', max_length=50, blank=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'ресторан'
        verbose_name_plural = 'рестораны'


class ProductQuerySet(models.QuerySet):
    def available(self):
        return self.distinct().filter(menu_items__availability=True)


class ProductCategory(models.Model):
    name = models.CharField('название', max_length=50)

    class Meta:
        verbose_name = 'категория'
        verbose_name_plural = 'категории'

    def __str__(self):
        return self.name


class Product(models.Model):
    name = models.CharField('название', max_length=50)
    category = models.ForeignKey(ProductCategory, null=True, blank=True, on_delete=models.SET_NULL,
                                 verbose_name='категория', related_name='products')
    price = models.DecimalField('цена', max_digits=8, decimal_places=2)
    image = models.ImageField('картинка')
    special_status = models.BooleanField('спец.предложение', default=False, db_index=True)
    ingridients = models.CharField('ингредиенты', max_length=200, blank=True)

    objects = ProductQuerySet.as_manager()

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'товар'
        verbose_name_plural = 'товары'


class RestaurantMenuItem(models.Model):
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name='menu_items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='menu_items')
    availability = models.BooleanField('в продаже', default=True, db_index=True)

    def __str__(self):
        return f"{self.restaurant.name} - {self.product.name}"

    class Meta:
        verbose_name = 'пункт меню ресторана'
        verbose_name_plural = 'пункты меню ресторана'
        unique_together = [
            ['restaurant', 'product']
        ]


class Order(models.Model):
    STATUSES = (('unprocessed', 'Необработанный'),
                ('processed', 'Обработанный'))
    PAYMENT_TYPES = (('online', 'Электронно'),
                     ('cash', 'Наличностью'))
    status = models.CharField('Статус заказа', max_length=20, choices=STATUSES, default='unprocessed', db_index=True)
    payment_type = models.CharField('Способ оплаты', max_length=20, choices=PAYMENT_TYPES, default='cash', db_index=True)
    firstname = models.CharField('Имя', max_length=50, db_index=True)
    lastname = models.CharField('Фамилия', max_length=50, db_index=True)
    phonenumber = models.CharField('Телефон', max_length=14, db_index=True)
    address = models.CharField('Адрес', max_length=300, db_index=True)
    comment = models.TextField(blank=True, verbose_name='Комментарий')
    registered_at = models.DateTimeField('Дата создания заказа', auto_now_add=True, db_index=True)
    called_at = models.DateTimeField('Дата звонка', null=True, blank=True, db_index=True)
    delivered_at = models.DateTimeField('Дата доставки заказа', null=True, blank=True, db_index=True)

    def get_order_restaurants(self):
        """
        This method generates many queries,
        please use ".prefetch_related('order_items__product__menu_items__restaurant')".
        """
        order_items = self.order_items.all()
        order_restaurants = []
        for order in order_items:
            menu_items = order.product.menu_items.all()
            for item in menu_items:
                if item.restaurant in order_restaurants:
                    continue
                order_restaurants.append(item.restaurant)
        return order_restaurants

    def get_restaurants_with_distance(self):
        order_restaurants = self.get_order_restaurants()
        order_address = self.address.strip()

        addresses = [restaurant.address.strip() for restaurant in order_restaurants]
        addresses.append(order_address)

        coordinates = get_bulk_cached_coordinates(addresses)

        order_coordinates = coordinates.get(order_address)

        restaurants_with_distance = []
        for restaurant in order_restaurants:
            restaurant_address = restaurant.address.strip()
            restaurant_coordinates = coordinates.get(restaurant_address)
            restaurant_distance = round(distance.distance(order_coordinates, restaurant_coordinates).km, 2)
            restaurants_with_distance.append((restaurant.name, restaurant_distance))

        return sorted(restaurants_with_distance, key=lambda restaurant: restaurant[1])

    def __str__(self):
        return f"{self.firstname} {self.lastname}, {self.address}"

    class Meta:
        verbose_name = 'заказ'
        verbose_name_plural = 'заказы'


class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name='order_items', on_delete=models.CASCADE, verbose_name='Заказ')
    product = models.ForeignKey(Product, related_name='order_items', on_delete=models.PROTECT, verbose_name='Блюдо')
    quantity = models.PositiveSmallIntegerField('Количество')
    price = models.DecimalField('цена', max_digits=8, decimal_places=2)

    def __str__(self):
        return f"{self.product.name}, {self.order.firstname} {self.order.lastname}, {self.order.address}"

    class Meta:
        verbose_name = 'элемент заказа'
        verbose_name_plural = 'элементы заказа'


def get_cached_coordinates(address):
    address = address.strip()
    cache_coordinates = cache.get(address)
    if not cache_coordinates:
        fetched_coordinates = fetch_coordinates(address)
        cache.set(address, fetched_coordinates)
    cache_coordinates = cache.get(address)
    return cache_coordinates


def get_bulk_cached_coordinates(addresses):
    coordinates = cache.get_many(addresses)

    for address in addresses:
        if address not in coordinates:
            address_coordinates = get_cached_coordinates(address)
            coordinates[address] = address_coordinates

    return coordinates
