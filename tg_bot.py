import logging
import re

from environs import Env

from telegram.error import TelegramError
from telegram.ext import (CallbackQueryHandler, CommandHandler,
                          ConversationHandler, Filters, MessageHandler,
                          Updater)

from errors import handle_error, log_exceptions
from utils import get_api_context, get_update_info
from api import (add_to_cart, clear_user_cart, create_order, 
                 get_display_cart, get_image, get_or_create_user_cart, 
                 get_products, get_user_cart_with_items, init_strapi_session,
                 remove_from_cart)
from keyboards import (get_keyboard_back, get_keyboard_cart, get_keyboard_menu,
                       get_keyboard_start)


logger = logging.getLogger(__name__)
HANDLE_MAIN, WAITING_EMAIL = range(2)


@log_exceptions
def handle_start(update, context):
    session, api_url = get_api_context(context)
    products = get_products(session, api_url)
    context.user_data["products"] = products
    text = "Приветствую! 🐟.\n Добро пожаловать в интернет-магазин свежей рыбы"
    update.message.reply_text(text, reply_markup=get_keyboard_start())

    return HANDLE_MAIN


@log_exceptions
def handle_menu(update, context):

    session, api_url = get_api_context(context)
    update_info = get_update_info(update)
    user_id = update_info.get("user_id")
    chat_id = update_info.get("chat_id")
    message_id = update_info.get("message_id")

    context.bot.delete_message(chat_id=chat_id, message_id=message_id)

    products = get_products(session, api_url)
    context.user_data["products"] = products

    cart_items = get_user_cart_with_items(session, api_url, user_id)
    count_items = get_display_cart(cart_items).get("count_items") if cart_items else 0

    text = "🏷️ Наши продукты:\nВыберите рыбу:"
    keyboard = get_keyboard_menu(products, count_items)
    context.bot.send_message(chat_id=chat_id, text=text, reply_markup=keyboard)
    return HANDLE_MAIN


@log_exceptions
def handle_show_product(update, context):
    session, api_url = get_api_context(context)
    update_info = get_update_info(update)
    chat_id, message_id = update_info.get("chat_id"), update_info.get("message_id")
    products = context.user_data["products"]
    user_reply = context.user_data["user_reply"]
    product = products.get(int(user_reply))
    url_image = (
        product.get("image", {})
        .get("formats", {})
        .get("small", {})
        .get("url")
    )
    context.user_data["product_id"] = product.get("id")
    image_data = get_image(session, api_url, url_image)
    text = f"{product.get('title')} ({product.get('price')} руб. за кг.)\n\n{product.get('description')}"
    context.bot.delete_message(chat_id=chat_id, message_id=message_id)
    context.bot.send_photo(
        chat_id=chat_id,
        photo=image_data,
        caption=text,
        reply_markup=get_keyboard_back(product.get("id"))
    )

    return HANDLE_MAIN


@log_exceptions
def handle_my_cart(update, context):
    session, api_url = get_api_context(context)
    update_info = get_update_info(update)
    user_id = update_info.get("user_id")
    query = update_info.get("query")

    cart_items = get_user_cart_with_items(session, api_url, user_id)
    keyboard = get_keyboard_cart(cart_items)

    if not cart_items or not cart_items.get('cart_items', []):
        query.edit_message_text(text="🛒 Ваша корзина пуста", reply_markup=keyboard)
        return HANDLE_MAIN

    cart_display = get_display_cart(cart_items).get("cart_display")

    query.edit_message_text(text=cart_display, reply_markup=keyboard)

    return HANDLE_MAIN


@log_exceptions
def handle_email(update, context):
    update_info = get_update_info(update)
    user_id = update_info.get("user_id")
    message = update_info.get("message")
    chat_id = update_info.get("chat_id")

    if not message:
        context.bot.send_message(chat_id=chat_id, text="📧 Введите ваш email для оформления заказа:")
        return WAITING_EMAIL

    email = message.text.strip()

    if not re.match(r"[\w\.-]+@[\w\.-]+\.\w+", email):
        update.message.reply_text("❌ Неверный формат email. Попробуйте снова:")
        return WAITING_EMAIL

    session, api_url = get_api_context(context)
    order_details = get_user_cart_with_items(session, api_url, user_id)

    if create_order(session, api_url, user_id, email, order_details):
        update.message.reply_text(
                "✅ Заказ успешно оформлен!\n"
                "Скоро с вами свяжется менеджер.\n\n"
                "Новый заказ: /start",
            )
        clear_user_cart(session, api_url, user_id)
        return ConversationHandler.END
    else:
        update.message.reply_text("Не удалось оформить заказ.")
        return HANDLE_MAIN


@log_exceptions
def handle_quantity_selection(update, context):

    update_info = get_update_info(update)
    query_quantity = update_info.get("query")
    quantity = int(query_quantity.data.split("_")[1])
    context.user_data["quantity"] = quantity
    product_id = context.user_data.get("product_id")

    keyboard = get_keyboard_back(product_id, quantity)
    query_quantity.answer(text=f"Выбрано: {quantity} кг", show_alert=False)

    if query_quantity.message.reply_markup != keyboard:
        query_quantity.edit_message_reply_markup(reply_markup=keyboard)

    return HANDLE_MAIN


@log_exceptions
def handle_add_to_cart(update, context):
    session, api_url = get_api_context(context)
    update_info = get_update_info(update)
    user_id = update_info.get("user_id")
    query = update_info.get("query")
    quantity = context.user_data.get("quantity", 1)
    product_id = context.user_data["product_id"]

    get_or_create_user_cart(session, api_url, user_id)
    add_to_cart(session, api_url, product_id, user_id, quantity)

    query.answer(text=f"✅ Добавлено в корзину: {quantity} кг.", show_alert=True)

    return HANDLE_MAIN


@log_exceptions
def handle_remove_product(update, context):
    session, api_url = get_api_context(context)
    update_info = get_update_info(update)
    query = update_info.get("query")
    user_id = update_info.get("user_id")
    cart_item_id = context.user_data["cart_item_id"]
    remove_from_cart(session, api_url, cart_item_id)
    cart_items = get_user_cart_with_items(session, api_url, user_id)
    cart_display = get_display_cart(cart_items).get("cart_display")
    keyboard = get_keyboard_cart(cart_items)

    old_text = query.message.text
    old_reply_markup = query.message.reply_markup
    keyboard_changed = old_reply_markup != keyboard
    text_changed = old_text != cart_display
    if text_changed or keyboard_changed:
        query.edit_message_text(text=cart_display, reply_markup=keyboard)

    query.answer(text="🗑️ Товар удален из корзины!", show_alert=False)
    return HANDLE_MAIN


@log_exceptions
def handle_description_reply(update, context):
    update_info = get_update_info(update)
    query = update_info.get("query")
    if not query:
        return HANDLE_MAIN
    data = query.data
    handlers = {
            "back": handle_menu,
            "add_cart_": handle_add_to_cart,
            "quantity_": handle_quantity_selection,
            "my_cart": handle_my_cart,
            "show_products": handle_menu,
            "pay": handle_email
        }
    for prefix, handler in handlers.items():
        if data.startswith(prefix):
            return handler(update, context)

    if data.startswith("remove_"):
        context.user_data["cart_item_id"] = int(data[len("remove_"):])
        return handle_remove_product(update, context)

    if data.isdigit():
        context.user_data["user_reply"] = data
        return handle_show_product(update, context)

    query.answer("⚠️ Неизвестная команда", show_alert=True)
    return HANDLE_MAIN



def main():
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=logging.INFO
    )
    env = Env()
    env.read_env()
    strapi_token = env.str("STRAPI_API_TOKEN")
    api_url = env.str("STRAPI_URL")

    tg_token = env.str("TG_TOKEN")
    updater = Updater(tg_token)
    dispatcher = updater.dispatcher
    try:
        strapi_session = init_strapi_session(token=strapi_token)
        dispatcher.bot_data["strapi_session"] = strapi_session
        dispatcher.bot_data["api_url"] = api_url
        dispatcher.add_error_handler(handle_error)
        conv_handler = ConversationHandler(
            entry_points=[CommandHandler("start", handle_start)],
            states={
                HANDLE_MAIN: [
                    CallbackQueryHandler(handle_description_reply),
                ],
                WAITING_EMAIL: [
                    MessageHandler(Filters.text & ~Filters.command, handle_email),
                ],
            },
            fallbacks=[CommandHandler("start", handle_start)],
        )
        dispatcher.add_handler(conv_handler)
        updater.start_polling()
        updater.idle()   

    except TelegramError as error:
        logger.exception(f"Ошибка Telegram: {error}")
    except Exception as error:
        logger.exception(f"Ошибка: {error}")


if __name__ == "__main__":
    main()

















