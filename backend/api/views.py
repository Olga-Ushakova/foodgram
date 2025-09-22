from django.conf import settings
from django.db.models import Sum
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from djoser.views import UserViewSet as DjoserUserViewSet
from rest_framework import exceptions, status, viewsets
from rest_framework.decorators import action, api_view
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from . import models, serializers
from .filters import IngredientFilter, RecipeFilter
from .permissions import IsAuthenticatedAuthorOrReadOnly


class UserViewSet(DjoserUserViewSet):
    """Вьюсет для модели Пользователя."""

    queryset = models.User.objects.all()
    serializer_class = serializers.UserSerializer
    permission_classes = (AllowAny,)

    @action(detail=True,
            methods=['post'],
            permission_classes=[IsAuthenticated])
    def subscribe(self, request, id):
        user = get_object_or_404(models.User, id=id)
        serializer = serializers.SubscriptionSerializer(
            data={},
            context={'request': request,
                     'user': user}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @subscribe.mapping.delete
    def unsubscribe(self, request, id):
        user = get_object_or_404(models.User, id=id)
        delete_count, _ = (
            user.subscribers.filter(subscriber=request.user).delete()
        )
        if not delete_count:
            raise exceptions.ValidationError(
                f'Не подписаны на пользователя {user.username}.'
            )
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False,
            methods=['get'],
            permission_classes=[IsAuthenticated])
    def subscriptions(self, request):
        subscriptions = request.user.subscriptions.all()
        subscription_users = [subscr.user for subscr in subscriptions]
        page = self.paginate_queryset(subscription_users)
        serializer = serializers.UserWithRecipesSerializer(
            page,
            many=True,
            context={'request': request}
        )
        return self.get_paginated_response(serializer.data)

    @action(detail=False,
            methods=['get'],
            permission_classes=[IsAuthenticated])
    def me(self, request):
        return super().me(request)

    @action(detail=False,
            methods=['put'],
            url_path='me/avatar',
            permission_classes=[IsAuthenticated])
    def avatar(self, request):
        serializer = serializers.UserAvatarSerializer(
            request.user,
            data=request.data,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)

    @avatar.mapping.delete
    def delete_avatar(self, request):
        serializer = serializers.UserAvatarSerializer(request.user)
        serializer.check_avatar_exists()
        request.user.avatar.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


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

    @action(detail=True,
            methods=['get'],
            url_path='get-link',
            permission_classes=[AllowAny])
    def get_short_link(self, request, pk):
        recipe = get_object_or_404(models.Recipe, id=pk)
        data = {'short-link': settings.BASE_LINK + recipe.short_code}
        return Response(data, status=status.HTTP_200_OK)

    @action(detail=True,
            methods=['post'],
            permission_classes=[IsAuthenticated])
    def shopping_cart(self, request, pk):
        recipe = get_object_or_404(models.Recipe, id=pk)
        serializer = serializers.ShoppingCartSerializer(
            data={},
            context={'request': request,
                     'recipe': recipe}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @shopping_cart.mapping.delete
    def delete_from_shopping_cart_(self, request, pk):
        recipe = get_object_or_404(models.Recipe, id=pk)
        delete_count, _ = (
            request.user.shopping_cart.filter(recipe=recipe).delete()
        )
        if not delete_count:
            raise exceptions.ValidationError(
                f'Рецепт "{recipe.name}" с id={recipe.id} '
                'не был добавлен в Список покупок.'
            )
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True,
            methods=['post'],
            permission_classes=[IsAuthenticated])
    def favorite(self, request, pk):
        recipe = get_object_or_404(models.Recipe, id=pk)
        serializer = serializers.FavoriteSerializer(
            data={},
            context={'request': request,
                     'recipe': recipe}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @favorite.mapping.delete
    def unfavorite(self, request, pk):
        recipe = get_object_or_404(models.Recipe, id=pk)
        delete_count, _ = request.user.favorites.filter(recipe=recipe).delete()
        if not delete_count:
            raise exceptions.ValidationError(
                f'Рецепт "{recipe.name}" с id={recipe.id} '
                'не был добавлен в Избранное.'
            )
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
    recipe = get_object_or_404(models.Recipe, short_code=short_code)
    recipe_url = request.build_absolute_uri(f'/recipes/{recipe.id}/')
    return HttpResponseRedirect(recipe_url)
