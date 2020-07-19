import json

from django.templatetags.static import static
from django.http import JsonResponse


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


def register_order(request):
    order_raw = json.loads(request.body.decode())

    firstname = order_raw.get('firstname')
    lastname = order_raw.get('lastname')
    phonenumber = order_raw.get('phonenumber')
    address = order_raw.get('address')
    order_products_raw = order_raw.get('products')

    customer = Order.objects.create(firstname=firstname, lastname=lastname, phonenumber=phonenumber, address=address)

    for order_product in order_products_raw:
        product = Product.objects.get(id=order_product.get('product'))
        OrderProduct.objects.create(order=customer, product=product, quantity=order_product.get('quantity'))


    return JsonResponse({})
