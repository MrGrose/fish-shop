from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def get_keyboard_start():
    return InlineKeyboardMarkup([[InlineKeyboardButton("Продукты", callback_data="show_products")],])


def get_keyboard_menu(products, count_items):
    count_items = f"Моя корзина({count_items})" if count_items else "Моя корзина"
    keyboard_start = []
    for product in products.values():
        keyboard_start.append([InlineKeyboardButton(
            text=f"{product['title']}",
            callback_data=f"{product['id']}"
        )])
    keyboard_start.append([InlineKeyboardButton(f"{count_items}", callback_data="my_cart")],)
    return InlineKeyboardMarkup(keyboard_start)


def get_keyboard_back(product_id, selected_quantity=1):
    quantities = [1, 2, 5, 10]
    keyboard = []
    quantity_buttons = []
    for quantity in quantities:
        prefix = "✅ " if quantity == selected_quantity else ""
        quantity_buttons.append(
            InlineKeyboardButton(prefix + str(quantity), callback_data=f"quantity_{quantity}")
        )
    keyboard.append(quantity_buttons)
    keyboard.append([InlineKeyboardButton("Добавить в корзину", callback_data=f"add_cart_{product_id}")])
    keyboard.append([InlineKeyboardButton("В меню", callback_data="back")])
    return InlineKeyboardMarkup(keyboard)


def get_keyboard_cart(cart_items):
    items = cart_items.get('cart_items', [])
    keyboard_cart = []
    for item in items:
        keyboard_cart.append([InlineKeyboardButton(
            text=f"Удалить: {item['product']['title']}",
            callback_data=f"remove_{item['id']}"
        )])
    if keyboard_cart:
        keyboard_cart.append(
            [
                InlineKeyboardButton("В меню", callback_data="back"),
                InlineKeyboardButton("Оплатить", callback_data="pay")
             ],
        )
    else:
        keyboard_cart.append([InlineKeyboardButton("В меню", callback_data="back")])
    return InlineKeyboardMarkup(keyboard_cart)