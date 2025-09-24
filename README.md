# Foodgram
**Foodgram** - проект, в котором пользователи могут публиковать свои рецепты, добавлять чужие рецепты в избранное и подписываться на публикации других авторов. Также для пользователей доступен сервис "Список покупок", который формирует список продуктов для приготовления выбранных блюд.
## Адрес
Проект доступен по адресу:  
https://getfoodgram.ddns.net/
## Стек технологий
+ Python
+ Django
+ Django REST Framework
+ Docker
## Установка и запуск проекта в Docker
1. **Клонируйте репозиторий:**
```bash
git clone https://github.com/Olga-Ushakova/foodgram.git
```
2. **Создайте файл .env с необходимыми переменными окружения в соответствии с .env.example:**
```bash
touch .env
```
3. **Запустите docker compose. Выполните команды для миграций базы данных, сбора статики:**
```bash
sudo docker compose -f docker-compose.production.yml up
sudo docker compose -f docker-compose.production.yml exec backend python manage.py migrate
sudo docker compose -f docker-compose.production.yml exec backend python manage.py collectstatic
```
## Загрузка данных:
Для загрузки набора ингредиентов для рецептов необходимо выполнить команду:
```bash
sudo docker compose -f docker-compose.production.yml exec backend python manage.py load_data
```
## Документация:
Документация доступна по адресу:  
https://getfoodgram.ddns.net/api/docs
## Примеры запросов
**Регистрация пользователя** (POST)
```bash
/api/users/
```
Пример ответа:
```bash
{ "email": "vpupkin@yandex.ru",
  "username": "vasya.pupkin",
  "first_name": "Вася",
  "last_name": "Иванов",
  "password": "Qwerty123"}
```
**Получение рецепта** (GET)
```bash
/api/recipes/{id}/
```
Пример ответа:
```bash
{ "id": 0,
  "tags": [{"id": 0,
            "name": "Завтрак",
            "slug": "breakfast"}],
  "author": {"email": "user@example.com",
             "id": 0,
             "username": "string",
             "first_name": "Вася",
             "last_name": "Иванов",
             "is_subscribed": false,
             "avatar": "http://foodgram.example.org/media/users/image.png"},
  "ingredients": [{"id": 0,
                   "name": "Картофель отварной",
                   "measurement_unit": "г",
                   "amount": 1}],
  "is_favorited": true,
  "is_in_shopping_cart": true,
  "name": "string",
  "image": "http://foodgram.example.org/media/recipes/images/image.png",
  "text": "string",
  "cooking_time": 1}
```
**Добавить рецепт в избранное** (POST)
```bash
/api/recipes/{id}/favorite/
```
Пример ответа:
```bash
{ "id": 0,
  "name": "string",
  "image": "http://foodgram.example.org/media/recipes/images/image.png",
  "cooking_time": 1}
```

## Автор
[*Ольга Ушакова*](https://github.com/Olga-Ushakova)
