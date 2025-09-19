import secrets

from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import exceptions, status, viewsets
from rest_framework.decorators import action, api_view
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from . import models, serializers
from .constants import BASE_LINK, MAX_CODE_LENGTH, RECIPES_LIMIT
from .filters import IngredientFilter, RecipeFilter
from .permissions import IsAuthenticatedAuthorOrReadOnly


class CustomUserViewSet(viewsets.ModelViewSet):
    """Вьюсет для модели Пользователя."""

    queryset = models.CustomUser.objects.all()
    permission_classes = (AllowAny,)

    def get_serializer_class(self):
        if self.request.method == 'GET':
            return serializers.CustomUserSerializer
        return serializers.CustomUserCreateSerializer

    @action(detail=True,
            methods=['post', 'delete'],
            permission_classes=[IsAuthenticated])
    def subscribe(self, request, pk):
        author = get_object_or_404(models.CustomUser, id=pk)
        user = request.user
        subscription_exists = (
            author.subscribers.filter(subscriber=user).exists()
        )
        recipes_limit = request.query_params.get(
            'recipes_limit', RECIPES_LIMIT
        )
        serializer = serializers.UserWithRecipesSerializer(
            author,
            context={'request': request,
                     'recipes_limit': recipes_limit}
        )

        if request.method == 'POST':
            if user == author:
                raise exceptions.ValidationError(
                    'Нельзя подписаться на самого себя.'
                )
            if subscription_exists:
                raise exceptions.ValidationError(
                    f'Уже подписаны на пользователя {author.username}.'
                )
            author.subscribers.create(subscriber=user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        else:
            if not subscription_exists:
                raise exceptions.ValidationError(
                    f'Не подписаны на пользователя {author.username}.'
                )
            author.subscribers.filter(subscriber=user).delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False,
            methods=['get'],
            permission_classes=[IsAuthenticated])
    def subscriptions(self, request):
        subscriptions = request.user.subscriptions.all()
        subscription_users = [subscr.user for subscr in subscriptions]
        page = self.paginate_queryset(subscription_users)
        recipes_limit = request.query_params.get(
            'recipes_limit', RECIPES_LIMIT
        )
        serializer = serializers.UserWithRecipesSerializer(
            page,
            many=True,
            context={'request': request,
                     'recipes_limit': recipes_limit}
        )
        return self.get_paginated_response(serializer.data)

    @action(detail=False,
            methods=['get'],
            permission_classes=[IsAuthenticated])
    def me(self, request):
        serializer = serializers.CustomUserSerializer(
            request.user,
            context={'request': request}
        )
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=False,
            methods=['put', 'delete'],
            url_path='me/avatar',
            permission_classes=[IsAuthenticated])
    def avatar(self, request):
        user = request.user
        if request.method == 'PUT':
            serializer = serializers.UserAvatarSerializer(
                user, data=request.data
            )
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_200_OK)
            return Response(serializer.errors,
                            status=status.HTTP_400_BAD_REQUEST)
        else:
            if not user.avatar:
                raise exceptions.ValidationError('Аватар не существует.')
            user.avatar.delete()
            user.avatar = None
            user.save()
            return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False,
            methods=['post'],
            permission_classes=[IsAuthenticated])
    def set_password(self, request):
        serializer = serializers.UserSetPasswordSerializer(
            data=request.data,
            context={'request': request}
        )
        if serializer.is_valid():
            serializer.save()
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    """Вьюсет для запросов к модели Ингредиента. Только чтение."""

    queryset = models.Ingredient.objects.all()
    serializer_class = serializers.IngredientSerializer
    permission_classes = (AllowAny,)
    filter_backends = (DjangoFilterBackend,)
    filterset_class = IngredientFilter
    pagination_class = None


class TagViewSet(viewsets.ReadOnlyModelViewSet):
    """Вьюсет для запросов к модели Тега. Только чтение."""

    queryset = models.Tag.objects.all()
    serializer_class = serializers.TagSerializer
    permission_classes = (AllowAny,)
    pagination_class = None


class RecipeViewSet(viewsets.ModelViewSet):
    """Вьюсет для запросов к модели Рецепта."""

    queryset = (
        models.Recipe.objects.select_related('author')
        .prefetch_related('ingredients', 'tags')
    )
    permission_classes = (IsAuthenticatedAuthorOrReadOnly,)
    http_method_names = ('get', 'post', 'patch', 'delete')
    filter_backends = (DjangoFilterBackend,)
    filterset_class = RecipeFilter

    def get_serializer_class(self):
        if self.request.method == 'GET':
            return serializers.RecipeReadSerializer
        return serializers.RecipeCreateSerializer

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    @action(detail=True,
            methods=['get'],
            url_path='get-link',
            permission_classes=[AllowAny])
    def get_short_link(self, request, pk):
        recipe = get_object_or_404(models.Recipe, id=pk)
        try:
            recipe_link = models.RecipeShortLink.objects.get(recipe=recipe)
            short_code = recipe_link.short_code
        except ObjectDoesNotExist:
            while True:
                short_code = (
                    secrets.token_urlsafe(MAX_CODE_LENGTH)[:MAX_CODE_LENGTH]
                )
                if not (
                    models.RecipeShortLink.objects
                    .filter(short_code=short_code).exists()
                ):
                    break
            models.RecipeShortLink.objects.create(
                recipe=recipe, short_code=short_code
            )
        data = {'short-link': BASE_LINK + short_code}
        return Response(data, status=status.HTTP_200_OK)

    @action(detail=True,
            methods=['post', 'delete'],
            permission_classes=[IsAuthenticated])
    def shopping_cart(self, request, pk):
        user = request.user
        recipe = get_object_or_404(models.Recipe, id=pk)
        in_shopping_cart = user.shopping_cart.filter(recipe=recipe).exists()
        serializer = serializers.RecipeMinifiedSerializer(recipe)

        if request.method == 'POST':
            if in_shopping_cart:
                raise exceptions.ValidationError(
                    f'Рецепт "{recipe.name}" с id={recipe.id} '
                    'уже добавлен в Список покупок.'
                )
            user.shopping_cart.create(recipe=recipe)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        else:
            if not in_shopping_cart:
                raise exceptions.ValidationError(
                    f'Рецепт "{recipe.name}" с id={recipe.id} '
                    'не был добавлен в Список покупок.'
                )
            user.shopping_cart.filter(recipe=recipe).delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True,
            methods=['post', 'delete'],
            permission_classes=[IsAuthenticated])
    def favorite(self, request, pk):
        user = request.user
        recipe = get_object_or_404(models.Recipe, id=pk)
        favorite_exists = user.favorites.filter(recipe=recipe).exists()
        serializer = serializers.RecipeMinifiedSerializer(recipe)

        if request.method == 'POST':
            if favorite_exists:
                raise exceptions.ValidationError(
                    f'Рецепт "{recipe.name}" с id={recipe.id} '
                    'уже добавлен в Избранное.'
                )
            user.favorites.create(recipe=recipe)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        else:
            if not favorite_exists:
                raise exceptions.ValidationError(
                    f'Рецепт "{recipe.name}" с id={recipe.id} '
                    'не был добавлен в Избранное.'
                )
            user.favorites.filter(recipe=recipe).delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False,
            methods=['get'],
            permission_classes=[IsAuthenticated])
    def download_shopping_cart(self, request):
        ingredients = (
            models.IngredientInRecipe.objects
            .filter(recipe__shopping_cart__user=request.user)
            .values(
                'ingredient__name',
                'ingredient__measurement_unit'
            )
            .annotate(
                total_amount=Sum('amount')
            )
        )
        if not ingredients.exists():
            raise exceptions.ValidationError('Список покупок пуст!')

        response = HttpResponse(content_type='text/plain; charset=utf-8')
        response['Content-Disposition'] = (
            'attachment; filename="shopping_list.txt"'
        )
        lines = ['СПИСОК ПОКУПОК\n', '-' * 30 + '\n']
        for ingredient in ingredients:
            line = (
                f"• {ingredient['ingredient__name']} "
                f"({ingredient['ingredient__measurement_unit']}) — "
                f"{ingredient['total_amount']}\n"
            )
            lines.append(line)

        response.writelines(lines)
        return response


@api_view(('GET',))
def short_link_redirect(request, short_code):
    """Функция для перенаправления на страницу рецепта по короткой ссылке."""
    recipe_link = get_object_or_404(
        models.RecipeShortLink,
        short_code=short_code
    )
    return redirect(f'/api/recipes/{recipe_link.recipe.id}/')
