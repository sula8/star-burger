from django.templatetags.static import static
from django.http import JsonResponse
from django.db import transaction, IntegrityError
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.serializers import ModelSerializer

from foodcartapp.models import Product, Order, Basket


class OrderProductSerializer(ModelSerializer):

    class Meta:
        model = Basket
        fields = ['product', 'quantity']


class OrderSerializer(ModelSerializer):
    products = OrderProductSerializer(many=True)

    class Meta:
        model = Order
        fields = ['firstname', 'lastname', 'phonenumber', 'address', 'products']


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


@transaction.atomic
@api_view(['POST'])
def register_order(request):
    serializer = OrderSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    order = Order.objects.create(
        firstname=serializer.validated_data['firstname'],
        lastname=serializer.validated_data['lastname'],
        phonenumber=serializer.validated_data['phonenumber'],
        address=serializer.validated_data['address'],
    )

    products_fields = serializer.validated_data['products']
    if products_fields:
        products = [Basket(order=order, price=fields.get('product').price, **fields) for fields in products_fields]
        Basket.objects.bulk_create(products)
    else:
        raise IntegrityError('Order must have at least one product')

    return Response({
        'order_id': order.id,
        'firstname': order.firstname,
        'lastname': order.lastname,
        'phonenumber': order.phonenumber,
        'address': order.address,
    })
