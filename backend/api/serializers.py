from rest_framework import serializers

from . import models
from .constants import RECIPES_LIMIT
from .serializer_fields import Base64ImageField


class UserSerializer(serializers.ModelSerializer):
    """Сериализатор для выдачи данных Пользователя."""

    is_subscribed = serializers.SerializerMethodField()

    class Meta:
        model = models.User
        fields = ('id', 'username', 'first_name', 'last_name',
                  'email', 'avatar', 'is_subscribed')

    def get_is_subscribed(self, user):
        request = self.context.get('request')
        return bool(
            request
            and request.user.is_authenticated
            and user.subscribers.filter(subscriber=request.user).exists()
        )


class UserAvatarSerializer(serializers.ModelSerializer):
    """Сериализатор для работы с аватаром Пользователя."""

    avatar = Base64ImageField()

    class Meta:
        model = models.User
        fields = ('avatar',)

    def check_avatar_exists(self):
        """Проверяет, существует ли аватар у пользователя."""
        if not self.instance.avatar:
            raise serializers.ValidationError('Аватар не существует.')
        return True


class UserWithRecipesSerializer(UserSerializer):
    """Сериализатор для выдачи данных Пользователя вместе с его рецептами."""

    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.SerializerMethodField()

    class Meta:
        model = models.User
        fields = (*UserSerializer.Meta.fields, 'recipes', 'recipes_count')

    def get_recipes(self, user):
        request = self.context.get('request')
        try:
            recipes_limit = int(
                request.query_params.get('recipes_limit', RECIPES_LIMIT)
            )
        except ValueError:
            recipes_limit = RECIPES_LIMIT
        recipes = user.recipes.all()[:recipes_limit]
        return RecipeMinifiedSerializer(recipes, many=True).data

    def get_recipes_count(self, user):
        return user.recipes.count()


class SubscriptionSerializer(serializers.ModelSerializer):
    """Сериализатор для создания Подписки."""

    class Meta:
        model = models.Subscription
        fields = ()

    def validate(self, data):
        user = self.context.get('user')
        subscriber = self.context.get('request').user
        if subscriber == user:
            raise serializers.ValidationError(
                'Нельзя подписаться на самого себя.'
            )
        if user.subscribers.filter(subscriber=subscriber).exists():
            raise serializers.ValidationError(
                f'Уже подписаны на пользователя {user.username}.'
            )
        return {'user': user, 'subscriber': subscriber}

    def to_representation(self, instance):
        return UserWithRecipesSerializer(
            instance.user, context=self.context
        ).data


class TagSerializer(serializers.ModelSerializer):
    """Сериализатор для модели Тега."""

    class Meta:
        model = models.Tag
        fields = ('id', 'name', 'slug')


class IngredientSerializer(serializers.ModelSerializer):
    """Сериализатор для модели Ингредиента."""

    class Meta:
        model = models.Ingredient
        fields = ('id', 'name', 'measurement_unit')


class IngredientInRecipeCreateSerializer(serializers.ModelSerializer):
    """Сериализатор для создания Ингредиента рецепта."""

    id = serializers.PrimaryKeyRelatedField(
        queryset=models.Ingredient.objects.all()
    )

    class Meta:
        model = models.IngredientInRecipe
        fields = ('id', 'amount')


class IngredientInRecipeReadSerializer(serializers.ModelSerializer):
    """Сериализатор для выдачи данных Ингредиента рецепта."""

    id = serializers.IntegerField(source='ingredient.id')
    name = serializers.CharField(source='ingredient.name')
    measurement_unit = serializers.CharField(
        source='ingredient.measurement_unit'
    )

    class Meta:
        model = models.IngredientInRecipe
        fields = ('id', 'name', 'measurement_unit', 'amount')


class RecipeReadSerializer(serializers.ModelSerializer):
    """Сериализатор получения полного Рецепта."""

    author = UserSerializer()
    tags = TagSerializer(many=True)
    ingredients = serializers.SerializerMethodField()
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()

    class Meta:
        model = models.Recipe
        fields = ('id', 'name', 'text', 'tags', 'author',
                  'ingredients', 'cooking_time', 'image',
                  'is_favorited', 'is_in_shopping_cart')
        read_only_fields = fields

    def get_ingredients(self, recipe):
        ingredients = recipe.ingredient_list.all()
        return IngredientInRecipeReadSerializer(ingredients, many=True).data

    def get_is_favorited(self, recipe):
        request = self.context.get('request')
        return bool(
            request
            and request.user.is_authenticated
            and recipe.favorites.filter(user=request.user).exists()
        )

    def get_is_in_shopping_cart(self, recipe):
        request = self.context.get('request')
        return bool(
            request
            and request.user.is_authenticated
            and recipe.shopping_cart.filter(user=request.user).exists()
        )


class RecipeCreateSerializer(serializers.ModelSerializer):
    """Сериализатор для создания Рецепта."""

    ingredients = IngredientInRecipeCreateSerializer(many=True)
    tags = serializers.PrimaryKeyRelatedField(
        queryset=models.Tag.objects.all(),
        many=True
    )
    image = Base64ImageField()

    class Meta:
        model = models.Recipe
        fields = ('name', 'text', 'cooking_time',
                  'image', 'ingredients', 'tags')

    def validate(self, data):
        ingredients = data.get('ingredients')
        tags = data.get('tags')

        if not ingredients:
            raise serializers.ValidationError(
                'В рецепте должен быть хотя бы один ингредиент.'
            )

        ingredient_ids = [item['id'].id for item in ingredients]

        if len(ingredient_ids) != len(set(ingredient_ids)):
            raise serializers.ValidationError(
                'Ингредиенты не должны повторяться.'
            )

        if not tags:
            raise serializers.ValidationError(
                'Необходимо указать хотя бы один тег для рецепта.'
            )
        if len(tags) != len(set(tags)):
            raise serializers.ValidationError('Теги не должны повторяться.')
        return data

    @staticmethod
    def add_ingredients(recipe, ingredients):
        for ingredient in ingredients:
            models.IngredientInRecipe.objects.create(
                recipe=recipe,
                ingredient_id=ingredient['id'].id,
                amount=ingredient['amount']
            )

    def create(self, validated_data):
        validated_data['author'] = self.context['request'].user
        ingredients = validated_data.pop('ingredients')
        tags = validated_data.pop('tags')
        recipe = models.Recipe.objects.create(**validated_data)
        recipe.tags.set(tags)
        self.add_ingredients(recipe, ingredients)
        return recipe

    def update(self, recipe, validated_data):
        ingredients = validated_data.pop('ingredients')
        tags = validated_data.pop('tags')
        recipe.tags.set(tags)
        recipe.ingredient_list.all().delete()
        self.add_ingredients(recipe, ingredients)
        return super().update(recipe, validated_data)

    def to_representation(self, instance):
        return RecipeReadSerializer(instance, context=self.context).data


class RecipeMinifiedSerializer(serializers.ModelSerializer):
    """Сериализатор для сокращенного представления рецепта."""

    class Meta:
        model = models.Recipe
        fields = ('id', 'name', 'image', 'cooking_time')


class ShoppingCartSerializer(serializers.ModelSerializer):
    """
    Сериализатор для создания записи о добавлении рецепта в список покупок.
    """

    class Meta:
        model = models.ShoppingCart
        fields = ()

    def validate(self, data):
        user = self.context.get('request').user
        recipe = self.context.get('recipe')
        if user.shopping_cart.filter(recipe=recipe).exists():
            raise serializers.ValidationError(
                f'Рецепт "{recipe.name}" с id={recipe.id} '
                'уже добавлен в Список покупок.'
            )
        return {'user': user, 'recipe': recipe}

    def to_representation(self, instance):
        return RecipeMinifiedSerializer(
            instance.recipe, context=self.context
        ).data


class FavoriteSerializer(serializers.ModelSerializer):
    """
    Сериализатор для создания записи о добавлении рецепта в Избранное.
    """

    class Meta:
        model = models.Favorite
        fields = ()

    def validate(self, data):
        user = self.context.get('request').user
        recipe = self.context.get('recipe')
        if user.favorites.filter(recipe=recipe).exists():
            raise serializers.ValidationError(
                f'Рецепт "{recipe.name}" с id={recipe.id} '
                'уже добавлен в Избранное.'
            )
        return {'user': user, 'recipe': recipe}

    def to_representation(self, instance):
        return RecipeMinifiedSerializer(
            instance.recipe, context=self.context
        ).data
