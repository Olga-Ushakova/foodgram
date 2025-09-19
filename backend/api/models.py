from django.contrib.auth.models import AbstractUser
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.core.validators import MinValueValidator
from django.db import models

from . import constants


class CustomUser(AbstractUser):
    """Расширенная модель пользователя."""

    username = models.CharField(
        'Никнейм',
        max_length=constants.NAME_MAX_LENGTH,
        unique=True,
        validators=[UnicodeUsernameValidator()],
    )
    first_name = models.CharField(
        'Имя',
        max_length=constants.NAME_MAX_LENGTH
    )
    last_name = models.CharField(
        'Фамилия',
        max_length=constants.NAME_MAX_LENGTH
    )
    email = models.EmailField(
        'Электронная почта',
        max_length=constants.EMAIL_MAX_LENGTH,
        unique=True
    )
    avatar = models.ImageField(
        'Аватар',
        upload_to='users/',
        blank=True,
        null=True
    )

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name']

    def __str__(self):
        return self.username


class Subscription(models.Model):
    """Модель подписки на пользователя."""

    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='subscribers',
        verbose_name='Пользователь'
    )
    subscriber = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='subscriptions',
        verbose_name='Подписчик'
    )

    class Meta:
        verbose_name = 'Подписка'
        verbose_name_plural = 'Подписки'
        constraints = [
            models.UniqueConstraint(
                fields=('user', 'subscriber'),
                name='unique_user_subscription'
            ),
            models.CheckConstraint(
                check=~models.Q(user=models.F('subscriber')),
                name='prevent_self_follow'
            )
        ]

    def __str__(self):
        return f'{self.subscriber} подписан на пользователя {self.user}'


class Ingredient(models.Model):
    """Модель ингредиента рецепта."""

    name = models.CharField(
        'Название',
        max_length=constants.INGREDIENT_NAME_MAX_LENGTH
    )
    measurement_unit = models.CharField(
        'Единица измерения',
        max_length=constants.MEASURE_UNIT_MAX_LENGTH
    )

    class Meta:
        verbose_name = 'Ингредиент'
        verbose_name_plural = 'Ингредиенты'
        ordering = ('name',)

    def __str__(self):
        return self.name


class Tag(models.Model):
    """Модель тега для классификации данных."""

    name = models.CharField(
        'Название',
        max_length=constants.TAG_MAX_LENGTH,
        unique=True
    )
    slug = models.SlugField(
        'Слаг',
        max_length=constants.TAG_MAX_LENGTH,
        unique=True
    )

    class Meta:
        verbose_name = 'Тег'
        verbose_name_plural = 'Теги'
        ordering = ('name',)

    def __str__(self):
        return self.name


class Recipe(models.Model):
    """Модель рецепта блюда."""

    name = models.CharField(
        'Название',
        max_length=constants.RECIPE_NAME_MAX_LENGTH
    )
    text = models.TextField('Описание')
    image = models.ImageField('Картинка', upload_to='recipes/images/')
    cooking_time = models.PositiveSmallIntegerField(
        'Время приготовления',
        validators=[MinValueValidator(constants.COOK_TIME_MIN_VALUE)],
        help_text='Время приготовления в минутах.'
    )
    pub_date = models.DateTimeField('Дата публикации', auto_now_add=True)
    author = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        verbose_name='Автор'
    )
    ingredients = models.ManyToManyField(
        Ingredient,
        through='IngredientInRecipe',
        verbose_name='Ингредиенты'
    )
    tags = models.ManyToManyField(Tag, verbose_name='Теги')

    class Meta:
        verbose_name = 'Рецепт'
        verbose_name_plural = 'Рецепты'
        default_related_name = 'recipes'
        ordering = ('-pub_date',)

    def __str__(self):
        return self.name


class IngredientInRecipe(models.Model):
    """Модель для хранения количества (граммовки) ингредиентов в рецепте."""

    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name='ingredient_list',
        verbose_name='Рецепт'
    )
    ingredient = models.ForeignKey(
        Ingredient,
        on_delete=models.CASCADE,
        related_name='recipe_ingredients',
        verbose_name='Ингедиент'
    )
    amount = models.PositiveSmallIntegerField(
        'Количество',
        validators=[MinValueValidator(constants.AMOUNT_MIN_VALUE)]
    )

    class Meta:
        verbose_name = 'Ингредиент рецепта'
        verbose_name_plural = 'Ингредиенты рецептов'
        constraints = [
            models.UniqueConstraint(
                fields=['recipe', 'ingredient'],
                name='unique_ingredient_in_recipe'
            )
        ]

    def __str__(self):
        return (f'В рецепт "{self.recipe}" входит {self.amount} '
                f'{self.ingredient.measurement_unit} {self.ingredient}')


class ShoppingCart(models.Model):
    """Модель списка покупок."""

    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        verbose_name='Пользователь'
    )
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        verbose_name='Рецепт'
    )

    class Meta:
        verbose_name = 'Список покупок'
        verbose_name_plural = 'Списки покупок'
        default_related_name = 'shopping_cart'
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'recipe'],
                name='unique_add_to_shopping_cart'
            )
        ]

    def __str__(self):
        return (f'{self.user} добавил(а) рецепт '
                f'"{self.recipe}" в список покупок')


class Favorite(models.Model):
    """Модель для избранных рецептов."""

    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        verbose_name='Пользователь'
    )
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        verbose_name='Рецепт'
    )

    class Meta:
        verbose_name = 'Избранное'
        verbose_name_plural = 'Избранное'
        default_related_name = 'favorites'
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'recipe'],
                name='unique_favorite'
            )
        ]

    def __str__(self):
        return (f'{self.user} добавил(а) рецепт "{self.recipe}" в Избранное')


class RecipeShortLink(models.Model):
    """Модель для коротких ссыллок на рецепты."""

    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        verbose_name='Рецепт'
    )
    short_code = models.CharField(
        max_length=constants.MAX_CODE_LENGTH,
        unique=True,
        verbose_name='Код'
    )

    class Meta:
        verbose_name = 'Короткая ссылка'
        verbose_name_plural = 'Короткие ссылки'
        constraints = [
            models.UniqueConstraint(
                fields=['recipe', 'short_code'],
                name='unique_short_code_for_recipe'
            )
        ]

    def __str__(self):
        return f'Короткая ссылка на рецепт "{self.recipe}"'
