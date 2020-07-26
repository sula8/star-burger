from datetime import datetime

from django.contrib.auth.models import User
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
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
    STATUSES = (('unprocessed', 'Необработанный'), ('processed', 'Обработанный'))
    PAYMENT_TYPES = (('online', 'Электронно'), ('cash', 'Наличностью'))
    status = models.CharField('Статус заказа', max_length=20, choices=STATUSES, default='unprocessed')
    payment_type = models.CharField('Способ оплаты', max_length=20, choices=PAYMENT_TYPES, default='cash')
    firstname = models.CharField('Имя', max_length=50, db_index=True)
    lastname = models.CharField('Фамилия', max_length=50, db_index=True)
    phonenumber = models.CharField('Телефон', max_length=14, db_index=True)
    address = models.CharField('Адрес', max_length=300, db_index=True)
    comment = models.TextField(null=True, blank=True, default='', verbose_name='Комментарий')
    registered_at = models.DateTimeField('Дата создания заказа', default=datetime.now())
    called_at = models.DateTimeField('Дата звонка', null=True, blank=True)
    delivered_at = models.DateTimeField('Дата доставки заказа', null=True, blank=True)

    def get_restaurants_with_distance(self):
        order_coordinates = get_cached_coordinates('order', self)

        restaurants = get_cached_order_restaurant(self)

        restaurants_with_distance = []
        for restaurant in restaurants:
            restaurant_name = restaurant[0]
            restaurant_coordinates = restaurant[1]
            restaurant_distance = round(distance.distance(order_coordinates, restaurant_coordinates).km, 2)
            restaurants_with_distance.append((restaurant_name, restaurant_distance))

        return sorted(restaurants_with_distance, key=lambda restaurant: restaurant[1])

    def __str__(self):
        return f"{self.firstname} {self.lastname}, {self.address}"

    class Meta:
        verbose_name = 'заказ'
        verbose_name_plural = 'заказы'


class OrderProduct(models.Model):
    order = models.ForeignKey(Order, related_name='ordered_products', on_delete=models.CASCADE, verbose_name='Заказ')
    product = models.ForeignKey(Product, on_delete=models.PROTECT, verbose_name='Блюдо')
    quantity = models.PositiveSmallIntegerField('Количество')
    price = models.DecimalField('цена', max_digits=8, decimal_places=2, null=True, blank=True)

    def __str__(self):
        return f"{self.product.name}, {self.order.firstname} {self.order.lastname}, {self.order.address}"

    class Meta:
        verbose_name = 'элемент заказа'
        verbose_name_plural = 'элементы заказа'


@receiver(post_save, sender=Order)
def order_post_save_handler(instance, **kwargs):
    order_coordinates_key = f'order_{instance.id}_coordinates'
    if cache.get(order_coordinates_key):
        cache.delete(order_coordinates_key)
    order_coordinates_value = fetch_coordinates(instance.address)

    cache.set(order_coordinates_key, order_coordinates_value)

    ordered_products = instance.ordered_products.all()
    order_restaurants = []
    for product in ordered_products:
        menu_items = product.product.menu_items.all()
        for item in menu_items:
            if item.restaurant in order_restaurants:
                continue
            order_restaurants.append(item.restaurant)

    order_restaurants_with_coordinates = []
    for restaurant in order_restaurants:
        restaurant_coordinates = get_cached_coordinates('restaurant', restaurant)
        order_restaurants_with_coordinates.append((restaurant.name, restaurant_coordinates))

    cache.set(f'order_{instance.id}_restaurants', order_restaurants_with_coordinates)


@receiver(post_save, sender=Restaurant)
def restaurant_post_save_handler(instance, **kwargs):
    restaurant_coordinates_key = f'restaurant_{instance.id}_coordinates'
    if cache.get(restaurant_coordinates_key):
        cache.delete(restaurant_coordinates_key)
    restaurant_coordinates_value = fetch_coordinates(instance.address)
    cache.set(restaurant_coordinates_key, restaurant_coordinates_value)


def get_cached_coordinates(type, instance):
    coordinates = cache.get(f'{type}_{instance.id}_coordinates')
    if not coordinates:
        if type == 'order':
            order_post_save_handler(instance)
        elif type == 'restaurant':
            restaurant_post_save_handler(instance)

    return cache.get(f'{type}_{instance.id}_coordinates')


def get_cached_order_restaurant(instance):
    restaurants = cache.get(f'order_{instance.id}_restaurants')
    if not restaurants:
        order_post_save_handler(instance)
    return cache.get(f'order_{instance.id}_restaurants')
