import logging
from functools import wraps

import requests
from telegram.error import BadRequest, RetryAfter, TimedOut, Unauthorized
from utils import get_update_info


class ServerError(Exception):
    pass


class NetworkError(Exception):
    pass


logger = logging.getLogger(__name__)


def log_exceptions(func):
    @wraps(func)
    def wrapper(update, context, *args, **kwargs):
        try:
            return func(update, context, *args, **kwargs)
        except Exception as e:
            handle_error(update, context, e)
            return
    return wrapper


def handle_error(update, context, error):
    logger.exception(f"Ошибка при обработке запроса: {error}")
    update_info = get_update_info(update) if update else {}
    query = update_info.get("query")
    message = update_info.get("message")
    chat_id = update_info.get("chat_id")

    error_handlers = {
        BadRequest: "Ошибка запроса: {}",
        Unauthorized: "Ошибка доступа: {}",
        RetryAfter: "Ошибка лимита: {}",
        TimedOut: "Ошибка соединения: {}",
        NetworkError: "Сетевая ошибка: {}",
    }
    for error_type, log_message in error_handlers.items():
        if isinstance(error, error_type):
            logger.error(log_message.format(error))
            return

    error_text = "Извините, произошла ошибка. Пожалуйста, попробуйте позже."
    if query:
        query.answer(text=error_text, show_alert=True)
    elif message:
        message.reply_text(error_text)
    elif chat_id:
        context.bot.send_message(chat_id=chat_id, text=error_text)

    return


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
            raise ServerError("Произошла неизвестная ошибка") from e

    return wrapper
