import json

from django.core.exceptions import ObjectDoesNotExist
from django.db import IntegrityError
from django.templatetags.static import static
from django.http import JsonResponse
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from foodcartapp.models import Product, Order, OrderProduct


def banners_list_api(request):
    # FIXME move data to db?
    return JsonResponse([
        {
            'title': 'Burger',
            'src': static('burger.jpg'),
            'text': 'Tasty Burger at your door step',
        },
        {
            'title': 'Spices',
            'src': static('food.jpg'),
            'text': 'All Cuisines',
        },
        {
            'title': 'New York',
            'src': static('tasty.jpg'),
            'text': 'Food is incomplete without a tasty dessert',
        }
    ], safe=False, json_dumps_params={
        'ensure_ascii': False,
        'indent': 4,
    })


def product_list_api(request):
    products = Product.objects.select_related('category').available()

    dumped_products = []
    for product in products:
        dumped_product = {
            'id': product.id,
            'name': product.name,
            'price': product.price,
            'special_status': product.special_status,
            'ingridients': product.ingridients,
            'category': {
                'id': product.category.id,
                'name': product.category.name,
            },
            'image': product.image.url,
            'restaurant': {
                'id': product.id,
                'name': product.name,
            }
        }
        dumped_products.append(dumped_product)
    return JsonResponse(dumped_products, safe=False, json_dumps_params={
        'ensure_ascii': False,
        'indent': 4,
    })


@api_view(['POST'])
def register_order(request):
    order_raw = request.data

    if not order_raw:
        content = {'errors': "Order is empty"}
        return Response(content, status=status.HTTP_200_OK)

    firstname = order_raw.get('firstname')
    if not firstname.__class__ == str:
        content = {'errors': "The firstname is not specified or not str"}
        return Response(content, status=status.HTTP_200_OK)

    lastname = order_raw.get('lastname')
    if not lastname.__class__ == str:
        content = {'errors': "The lastname is not specified or not str"}
        return Response(content, status=status.HTTP_200_OK)

    phonenumber = order_raw.get('phonenumber')
    if not phonenumber:
        content = {'errors': "The phonenumber is not specified"}
        return Response(content, status=status.HTTP_200_OK)

    address = order_raw.get('address')
    if not address.__class__ == str:
        content = {'errors': "The address is not specified or not str"}
        return Response(content, status=status.HTTP_200_OK)

    customer = Order.objects.create(firstname=firstname, lastname=lastname, phonenumber=phonenumber, address=address)

    order_products_raw = order_raw.get('products')
    if not order_products_raw:
        content = {'errors': "Product isn't valid"}
        return Response(content, status=status.HTTP_200_OK)

    for order_product in order_products_raw:
        try:
            product = Product.objects.get(id=order_product.get('product'))
        except ObjectDoesNotExist:
            content = {'errors': "Product doesn't exist"}
            return Response(content, status=status.HTTP_200_OK)
        except AttributeError:
            content = {'errors': "Product isn't valid"}
            return Response(content, status=status.HTTP_200_OK)

        OrderProduct.objects.create(order=customer, product=product, quantity=order_product.get('quantity'))

    content = {'success': 'OK'}
    return Response(content, status=status.HTTP_200_OK)


#{"products": [{"product": 1, "quantity": 2}, {"product": 4, "quantity": 3}], "firstname": "Иван1", "lastname": "Ваня1", "phonenumber": "1877777777", "address": "Москва 2"}
