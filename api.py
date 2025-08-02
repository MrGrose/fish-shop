import requests

from io import BytesIO
from errors import handle_error_response


@handle_error_response
def init_strapi_session(token):
    session = requests.Session()
    session.headers.update({
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    })
    return session


@handle_error_response
def get_products(session, api_url):
    response = session.get(f"{api_url}/api/products?populate=*", timeout=5)
    response.raise_for_status()
    products = {item["id"]: item for item in response.json().get("data", [])}
    return products


@handle_error_response
def get_image(session, api_url, url_image):
    url = f"{api_url}{url_image}"
    response = session.get(url, stream=True, timeout=5)
    response.raise_for_status()
    return BytesIO(response.content)


@handle_error_response
def get_or_create_user_cart(session, api_url, user_id):
    cart_response = session.get(f"{api_url}/api/carts?filters[telegramId][$eq]={user_id}", timeout=5)
    cart_response.raise_for_status()
    cart_data = cart_response.json()

    if cart_data["meta"]["pagination"]["total"] == 0:
        payload = {"data": {"telegramId": user_id}}
        create_response = session.post(f"{api_url}/api/carts", json=payload)
        create_response.raise_for_status()


@handle_error_response
def get_user_cart_with_items(session, api_url, user_id):
    response = session.get(f"{api_url}/api/carts?filters[telegramId][$eq]={user_id}&populate=cart_items.product", timeout=5)
    response.raise_for_status()
    data = response.json()
    if data.get("meta", {}).get("pagination", {}).get("total", 0) == 0:
        return None
    cart_items = data.get("data", [])[0]
    return cart_items


@handle_error_response
def add_to_cart(session, api_url, product_id, user_id, quantity):
    cart = get_user_cart_with_items(session, api_url, user_id)
    cart_id = cart["id"]
    cart_items = cart.get("cart_items", [])

    existing_item = next((item for item in cart_items if item.get("product", {}).get("id") == int(product_id)), None)

    if existing_item:
        new_quantity = existing_item.get("quantity", 0) + quantity
        update_payload = {"data": {"quantity": new_quantity}}
        update_url = f"{api_url}/api/cart-items/{existing_item["documentId"]}"
        response = session.put(update_url, json=update_payload)
        response.raise_for_status()
    else:
        create_payload = {
            "data": {
                "quantity": quantity,
                "cart_item": cart_id,
                "product": product_id,
            }
        }
        response = session.post(f"{api_url}/api/cart-items", json=create_payload )
        response.raise_for_status()


def get_display_cart(cart):
    if not cart:
        return {"cart_display": "🛒 Ваша корзина пуста", "count_items": 0}

    cart_items = cart.get("cart_items", [])
    product_summaries = []
    for item in cart_items:
        quantity = item.get("quantity")
        product = item.get("product")
        title = product.get("title", "Неизвестный товар")
        price = product.get("price", 0)

        product_summaries.append({
            "quantity": quantity,
            "title": title,
            "price": price
        })
    cart_display = ""
    total_price = 0
    for product_summary in product_summaries:
        total_price += product_summary["price"] * product_summary["quantity"]
        cart_display += f"\n{product_summary['title']} — Количество: {product_summary['quantity']} Цена: {product_summary['price'] * product_summary['quantity']} руб."

    cart_display += f"\n\n💳 Итого: {total_price}"
    return {"cart_display": cart_display, "count_items": len(product_summaries)}


@handle_error_response
def remove_from_cart(session, api_url, cart_item_id):
    response = session.get(f"{api_url}/api/cart-items?filters[id][$eq]={cart_item_id}", timeout=5)
    response.raise_for_status()
    cart_item_data = response.json()

    document_id = cart_item_data["data"][0]["documentId"]
    delete_cart_item = f"{api_url}/api/cart-items/{document_id}"
    del_response = session.delete(delete_cart_item)
    del_response.raise_for_status()



@handle_error_response
def clear_user_cart(session, api_url, user_id):
    cart = get_user_cart_with_items(session, api_url, user_id)
    if not cart:
        return
    cart_items = cart.get("cart_items", [])
    for item in cart_items:
        remove_from_cart(session, api_url, item["id"])


@handle_error_response
def create_order(session, api_url, user_id, email, order_details):
    total = sum(item["product"]["price"] * item["quantity"] for item in order_details["cart_items"])
    product_items = [{"product": item["product"]["id"], "quantity": item["quantity"]} for item in order_details["cart_items"]]
    order_upload = {
        "data": {
            "email": email,
            "tgID": user_id,
            "total": total
        }
    }
    response = session.post(f"{api_url}/api/orders", json=order_upload)
    response.raise_for_status()
    order_id = response.json()["data"]["id"]
    return create_order_items(session, api_url, order_id, product_items)


@handle_error_response
def create_order_items(session, api_url, order_id, product_items):
    upload_order_items = False
    for item in product_items:
        order_item_payload = {
            "data": {
                "quantity": item["quantity"],
                "order": {"connect": order_id},
                "product": {"connect": item["product"]}
            }
        }

        response = session.post(f"{api_url}/api/order-items", json=order_item_payload)
        response.raise_for_status()
        upload_order_items = True

    return upload_order_items
