from functools import wraps
from io import BytesIO

import requests


class ServerError(Exception):
    pass


class NetworkError(Exception):
    pass


def handle_error_response(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)

        except requests.ConnectionError as conn_err:
            raise NetworkError(f"Ошибка сети: {conn_err}") from conn_err

        except requests.HTTPError as http_err:
            status_code = http_err.response.status_code if http_err.response else None
            error_messages = {
                400: "Неправильный запрос",
                401: "Требуется аутентификация",
                403: "Доступ запрещен",
                404: "Ресурс не найден",
            }
            error_message = error_messages.get(status_code, "Неизвестная ошибка")
            raise ServerError(f"Ошибка на стороне сервера: {status_code} - {error_message}") from http_err

        except requests.RequestException as req_err:
            raise ServerError(f"Ошибка запроса: {req_err}") from req_err

        except Exception as e:
            raise Exception("Произошла неизвестная ошибка") from e

    return wrapper


@handle_error_response
def init_strapi_session(token):
    session = requests.Session()
    session.headers.update({
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    })
    return session


@handle_error_response
def get_products(session, api_url):
    response = session.get(f"{api_url}/api/products?populate=*")
    response.raise_for_status()
    products = {item['id']: item for item in response.json().get('data', [])}
    return products


@handle_error_response
def get_image(session, api_url, url_image):
    url = f"{api_url}{url_image}"
    response = session.get(url, stream=True)
    response.raise_for_status()
    return BytesIO(response.content)


@handle_error_response
def get_or_create_user_cart(session, api_url, user_id):
    cart_response = session.get(f"{api_url}/api/carts?filters[telegramId][$eq]={user_id}")
    cart_response.raise_for_status()
    cart_data = cart_response.json()

    if cart_data['meta']['pagination']['total'] == 0:
        payload = {"data": {"telegramId": user_id}}
        create_response = session.post(f"{api_url}/api/carts", json=payload)
        create_response.raise_for_status()
        cart = create_response.json()['data']
    else:
        cart = cart_data['data'][0]

    return cart['id']


@handle_error_response
def get_user_cart_with_items(session, api_url, user_id):
    response = session.get(f"{api_url}/api/carts?filters[telegramId][$eq]={user_id}&populate=cart_items.product")
    response.raise_for_status()
    data = response.json()
    if data.get('meta', {}).get('pagination', {}).get('total', 0) == 0:
        return None
    cart_items = data.get('data', [])[0]
    return cart_items


@handle_error_response
def add_to_cart(session, api_url, product_id, user_id, quantity):
    cart = get_user_cart_with_items(session, api_url, user_id)
    cart_id = cart['id']
    cart_items = cart.get('cart_items', [])

    existing_item = next((item for item in cart_items if item.get('product', {}).get('id') == int(product_id)), None)

    if existing_item:
        new_quantity = existing_item.get('quantity', 0) + quantity
        update_payload = {"data": {"quantity": new_quantity}}
        update_url = f"{api_url}/api/cart-items/{existing_item['documentId']}"
        response = session.put(update_url, json=update_payload)
        response.raise_for_status()
    else:
        create_item = {
            "data": {
                "quantity": quantity,
                "cart_item": cart_id,
                "product": product_id,
            }
        }
        response = session.post(f"{api_url}/api/cart-items", json=create_item)
        response.raise_for_status()


def get_display_cart(cart):
    cart_items = cart.get('cart_items', [])
    short_text_product = []
    for item in cart_items:
        quantity = item.get('quantity')
        product = item.get('product')
        title = product.get('title') if product else None
        price = product.get('price') if product else 0

        short_text_product.append({
            "quantity": quantity,
            "title": title,
            "price": price
        })
    cart_display = ""
    total_price = 0
    for entry in short_text_product:
        total_price += entry['price'] * entry['quantity']
        cart_display += f"\n{entry['title']} — Количество: {entry['quantity']} Цена: {entry['price'] * entry['quantity']} руб."

    cart_display += f"\n\nИтого: {total_price}"
    return {"cart_display": cart_display, "count_items": len(short_text_product)}


@handle_error_response
def remove_from_cart(session, api_url, cart_item_id):
    response = session.get(f"{api_url}/api/cart-items?filters[id][$eq]={cart_item_id}")
    response.raise_for_status()
    cart_item = response.json()

    document_id = cart_item['data'][0]['documentId']
    delete_cart_item = f"{api_url}/api/cart-items/{document_id}"
    del_response = session.delete(delete_cart_item)
    del_response.raise_for_status()



@handle_error_response
def clear_user_cart(session, api_url, user_id):
    cart = get_user_cart_with_items(session, api_url, user_id)
    cart_items = cart.get('cart_items', [])
    for item in cart_items:
        remove_from_cart(session, api_url, item['id'])


def create_order(session, api_url, user_id, email, order_details):
    total = sum(item['product']['price'] * item['quantity'] for item in order_details['cart_items'])
    product_items = [{'product': item['product']['id'], 'quantity': item['quantity']} for item in order_details['cart_items']]
    order_upload = {
        "data": {
            "email": email,
            "tgID": user_id,
            "total": total
        }
    }
    response = session.post(f"{api_url}/api/orders", json=order_upload)
    response.raise_for_status()
    order_id = response.json()['data']['id']
    return create_order_items(session, api_url, order_id, product_items)


@handle_error_response
def create_order_items(session, api_url, order_id, product_items):
    upload_order_items = False
    for item in product_items:
        items_upload = {
            "data": {
                "quantity": item['quantity'],
                "order": {"connect": order_id},
                "product": {"connect": item['product']}
            }
        }

        response = session.post(f"{api_url}/api/order-items", json=items_upload)
        response.raise_for_status()
        upload_order_items = True

    return upload_order_items
