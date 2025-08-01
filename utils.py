def get_api_context(context):
    return context.bot_data['strapi_session'], context.bot_data['api_url']


def get_update_info(update):
    if update.callback_query:
        return {
            'user_id': str(update.callback_query.from_user.id),
            'chat_id': update.callback_query.message.chat_id,
            'message_id': update.callback_query.message.message_id,
            'query': update.callback_query
        }
    elif update.message:
        return {
            'user_id': str(update.message.from_user.id),
            'chat_id': update.message.chat_id,
            'message_id': update.message.message_id,
            'message': update.message
        }
    else:
        return {}
