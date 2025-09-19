from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.password_validation import validate_password
from djoser.serializers import UserCreateSerializer
from rest_framework import serializers

from . import models
from .constants import AMOUNT_MIN_VALUE
from .serializer_fields import Base64ImageField


class CustomUserCreateSerializer(UserCreateSerializer):
    """Сериализатор для создания Пользователя."""

    class Meta(UserCreateSerializer.Meta):
        model = models.CustomUser


class CustomUserSerializer(serializers.ModelSerializer):
    """Сериализатор для выдачи данных Пользователя."""

    is_subscribed = serializers.SerializerMethodField()

    class Meta:
        model = models.CustomUser
        fields = ('id', 'username', 'first_name', 'last_name',
                  'email', 'avatar', 'is_subscribed')

    def get_is_subscribed(self, user):
        request = self.context.get('request')
        return (request.user.is_authenticated
                and user.subscribers
                .filter(subscriber=request.user).exists())


class UserAvatarSerializer(serializers.ModelSerializer):
    """Сериализатор для работы с аватаром Пользователя."""

    avatar = Base64ImageField()

    class Meta:
        model = models.CustomUser
        fields = ('avatar',)


class UserSetPasswordSerializer(serializers.ModelSerializer):
    """Сериализатор для смены пароля Пользователя."""

    new_password = serializers.CharField(write_only=True)
    current_password = serializers.CharField(write_only=True)

    class Meta:
        model = models.CustomUser
        fields = ('new_password', 'current_password')

    def validate_current_password(self, current_password):
        user = self.context['request'].user
        if not user.check_password(current_password):
            raise serializers.ValidationError('Текущий пароль неверен.')
        return current_password

    def validate_new_password(self, new_password):
        validate_password(new_password)
        return new_password

    def save(self):
        user = self.context['request'].user
        user.set_password(self.validated_data['new_password'])
        user.save()
        update_session_auth_hash(self.context['request'], user)


class UserWithRecipesSerializer(CustomUserSerializer):
    """Сериализатор для выдачи данных Пользователя вместе с его рецептами."""

    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.SerializerMethodField()

    class Meta:
        model = models.CustomUser
        fields = ('id', 'username', 'first_name', 'last_name', 'email',
                  'avatar', 'is_subscribed', 'recipes', 'recipes_count')

    def get_recipes(self, user):
        recipes_limit = int(self.context.get('recipes_limit'))
        recipes = user.recipes.all()[:recipes_limit]
        return RecipeMinifiedSerializer(recipes, many=True).data

    def get_recipes_count(self, user):
        return user.recipes.count()


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


class IngredientInRecipeCreateSerializer(serializers.Serializer):
    """Сериализатор для создания Ингредиента рецепта."""

    id = serializers.IntegerField(required=True)
    amount = serializers.IntegerField(
        min_value=AMOUNT_MIN_VALUE,
        required=True
    )


class RecipeReadSerializer(serializers.ModelSerializer):
    """Сериализатор получения полного Рецепта."""

    author = CustomUserSerializer()
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
        return [
            {
                'id': item.ingredient.id,
                'name': item.ingredient.name,
                'measurement_unit': item.ingredient.measurement_unit,
                'amount': item.amount
            }
            for item in ingredients
        ]

    def get_is_favorited(self, recipe):
        user = self.context['request'].user
        return (user.is_authenticated
                and recipe.favorites.filter(user=user).exists())

    def get_is_in_shopping_cart(self, recipe):
        user = self.context['request'].user
        return (user.is_authenticated
                and recipe.shopping_cart.filter(user=user).exists())


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

        ingredient_ids = [item['id'] for item in ingredients]

        if len(ingredient_ids) != len(set(ingredient_ids)):
            raise serializers.ValidationError(
                'Ингредиенты не должны повторяться.'
            )

        existing_ingredients = models.Ingredient.objects.filter(
            id__in=ingredient_ids
        )
        if existing_ingredients.count() != len(ingredient_ids):
            existing_ids = set(
                existing_ingredients.values_list('id', flat=True)
            )
            missing_ids = set(ingredient_ids) - existing_ids
            raise serializers.ValidationError(
                f'Ингредиенты с id {missing_ids} не существуют.'
            )

        if not tags:
            raise serializers.ValidationError(
                'Необходимо указать хотя бы один тег для рецепта.'
            )
        if len(tags) != len(set(tags)):
            raise serializers.ValidationError('Теги не должны повторяться.')
        return data

    def add_ingredients(self, recipe, ingredients):
        for ingredient in ingredients:
            models.IngredientInRecipe.objects.create(
                recipe=recipe,
                ingredient=models.Ingredient.objects.get(id=ingredient['id']),
                amount=ingredient['amount']
            )

    def create(self, validated_data):
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
        for attr, value in validated_data.items():
            setattr(recipe, attr, value)
        recipe.save()
        return recipe

    def to_representation(self, instance):
        return RecipeReadSerializer(instance, context=self.context).data


class RecipeMinifiedSerializer(serializers.ModelSerializer):
    """Сериализатор для сокращенного представления рецепта."""

    class Meta:
        model = models.Recipe
        fields = ['id', 'name', 'image', 'cooking_time']
        read_only_fields = fields
