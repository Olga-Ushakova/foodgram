# Константы для api

# Размер страницы при пагинации
PAGE_SIZE = 6

# Для модели Пользователя:
NAME_MAX_LENGTH = 150
EMAIL_MAX_LENGTH = 254

# Для модели Ингредиента:
INGREDIENT_NAME_MAX_LENGTH = 128
MEASURE_UNIT_MAX_LENGTH = 64

# Для модели Тега:
TAG_MAX_LENGTH = 32

# Для модели Рецепта:
RECIPE_NAME_MAX_LENGTH = 256
COOK_TIME_MIN_VALUE = 1
AMOUNT_MIN_VALUE = 1

# Для модели короткой ссылки на рецепт:
MAX_CODE_LENGTH = 8

# Количество рецептов пользователя по умолчанию,
# которое выводится вместе с инфомацией о пользователе
RECIPES_LIMIT = 3

# Базовая часть ссылки для формирования короткой ссылки на рецепт
BASE_LINK = 'https://getfoodgram.ddns.net/s/'
