from django.templatetags.static import static
from django.http import JsonResponse
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.serializers import ModelSerializer

from foodcartapp.models import Product, Order, OrderProduct


class OrderProductSerializer(ModelSerializer):

    class Meta:
        model = OrderProduct
        fields = ['product', 'quantity', 'price']


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
    products = [OrderProduct(order=order, price=fields.get('product').price, **fields) for fields in products_fields]

    OrderProduct.objects.bulk_create(products)

    return Response({
        'order_id': order.id,
        'firstname': order.firstname,
        'lastname': order.lastname,
        'phonenumber': order.phonenumber,
        'address': order.address,
    })



#{"products": [{"product": 1, "quantity": 2}, {"product": 4, "quantity": 3}], "firstname": "Иван1", "lastname": "Ваня1", "phonenumber": "1877777777", "address": "Москва 2"}
#{"products": [{"product": 1, "quantity": 1}], "firstname": "Василий", "lastname": "Васильевич", "phonenumber": "+79123456789", "address": "Лондон"}
