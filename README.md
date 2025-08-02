# Fish shop

`Fish shop` - это Telegram-бот, предназначенный для оформления заказа рыбных деликатесов. Он проводит пользователей через ряд шагов, включая выбор рыбы, указание кол-ва в кг и подтверждение заказа. Бот взаимодействует с сервисом CMS Strapi, в котором храниться информация о продуктах, заказах, пользователях.


## Функционал
1. Приветствие
2. Выбор необходимого продукта 
3. Добавление/удаление в корзине пользователя
4. Создание заказа

## Пример работы
 ![fish-shop](https://private-user-images.githubusercontent.com/147311692/473706869-6cf5fada-ea4c-44e2-bac3-3f486f0bab9a.gif?jwt=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJnaXRodWIuY29tIiwiYXVkIjoicmF3LmdpdGh1YnVzZXJjb250ZW50LmNvbSIsImtleSI6ImtleTUiLCJleHAiOjE3NTQxNTYzODksIm5iZiI6MTc1NDE1NjA4OSwicGF0aCI6Ii8xNDczMTE2OTIvNDczNzA2ODY5LTZjZjVmYWRhLWVhNGMtNDRlMi1iYWMzLTNmNDg2ZjBiYWI5YS5naWY_WC1BbXotQWxnb3JpdGhtPUFXUzQtSE1BQy1TSEEyNTYmWC1BbXotQ3JlZGVudGlhbD1BS0lBVkNPRFlMU0E1M1BRSzRaQSUyRjIwMjUwODAyJTJGdXMtZWFzdC0xJTJGczMlMkZhd3M0X3JlcXVlc3QmWC1BbXotRGF0ZT0yMDI1MDgwMlQxNzM0NDlaJlgtQW16LUV4cGlyZXM9MzAwJlgtQW16LVNpZ25hdHVyZT0xNGMxZjRhMmMxOTg2MDk5NzRjMDlmZjdjMTc1ODQ0NzkxZTVlYTRlZDgwNTQzMjQ2M2ZmYmZkODhhNmIxZTc2JlgtQW16LVNpZ25lZEhlYWRlcnM9aG9zdCJ9.i0aWS8nOgmQz8lGSdy9RbR2x8XnIxEjFjckCD71z4kk)

## Архитектура
Архитектура бота состоит из следующих ключевых компонентов:
- `tg_bot`: Логика обработки команд и взаимодействия с пользователем.
- `keyboards.py`: Создание клавиатур для взаимодействия.
- `api.py`: Запросы к сервису Strapi.
- `utils`: Функции для извлечения и подготовки данных из обновлений Telegram и контекста бота.
- `errors`: Логика обработки ошибок.



## Начало работы

1. Клонируйте репозиторий:
```bash
git clone <URL>
cd <directory>
```

2. Установите зависимости:
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

3. Необходимо создать .env файл:

- [STRAPI_API_TOKEN](https://docs.strapi.io/cms/features/api-tokens)
- [STRAPI_URL](https://docs.strapi.io/cms/quick-start#step-6-use-the-api)
- [TG_TOKEN](https://core.telegram.org/bots/tutorial#obtain-your-bot-token)


4. Настройте проект.
В вашем проекте [Strapi](https://docs.strapi.io/cms/quick-start) должны быть созданы следующие основные Collection Types с приблизительной структурой полей и связей.

    4.1. Product (Продукт)

    ```bash
    title (string) — название продукта.
    price (number) — цена за единицу(кг).
    description (text) — описание продукта.
    image (media) — изображение продукта.
    product_items (oneToMany) - связь с CartItem.
    order_items (oneToMany) - связь с OrderItem.
    ```
    4.2. Cart (Корзина)
    ```bash
    telegramId (string) — уникальный идентификатор пользователя Telegram.
    cart_items (oneToMany) — связь с CartItem.
    ```
    4.3. Cart Item (Элемент корзины)
    ```bash
    quantity (number) — количество продукта в корзине.
    cart_item (manyToOne) — связь с картой Cart.
    product (manyToOne) — связь с продуктом Product.
    ```
    4.4. Order (Заказ)
    ```bash
    email (string) — email пользователя для оформления заказа.
    tgID (string) — Telegram ID пользователя.
    total (number) — итоговая сумма заказа.
    order_items (oneToMany) — связь с Order Item.
    ```
    4.5. Order Item (Элемент заказа)
    ```bash
    quantity (number) — количество продукта в заказе.
    order (manyToOne) — связь с Order.
    product (manyToOne) — связь с Product.
    ```
5. Для запуска следуйте иструкции [Strapi](https://docs.strapi.io/cms/quick-start#-part-a-create-a-new-project-with-strapi).

6. Запуск бота.
```bash
python tg_bot.py
```

