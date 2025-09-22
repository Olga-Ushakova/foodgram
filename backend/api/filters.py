import django_filters

from .models import Ingredient, Recipe


class RecipeFilter(django_filters.FilterSet):
    """
    Фильтр для модели Рецепта.
    Фильтрует по:
    - id автора рецепта,
    - слагу тега,
    - нахождению в списке покупок,
    - нахождению в избранном.
    """

    is_favorited = django_filters.NumberFilter(
        method='filter_is_favorited'
    )
    is_in_shopping_cart = django_filters.NumberFilter(
        method='filter_is_in_shopping_cart'
    )
    author = django_filters.NumberFilter(
        field_name='author__id'
    )
    tags = django_filters.AllValuesMultipleFilter(
        field_name='tags__slug',
    )

    class Meta:
        model = Recipe
        fields = ('is_favorited', 'is_in_shopping_cart', 'author', 'tags')

    def filter_is_favorited(self, queryset, name, value):
        if self.request.user.is_authenticated and value:
            recipe_ids = (
                self.request.user.favorites
                .values_list('recipe_id', flat=True)
            )
            return queryset.filter(id__in=recipe_ids)
        return queryset

    def filter_is_in_shopping_cart(self, queryset, name, value):
        if self.request.user.is_authenticated and value:
            recipe_ids = (
                self.request.user.shopping_cart
                .values_list('recipe_id', flat=True)
            )
            return queryset.filter(id__in=recipe_ids)
        return queryset


class IngredientFilter(django_filters.FilterSet):
    """
    Фильтр для модели Ингредиента.
    Фильтрует по частичному вхождению строки в начало имени Ингредиента.
    """

    name = django_filters.CharFilter(
        field_name='name',
        lookup_expr='istartswith'
    )

    class Meta:
        model = Ingredient
        fields = ('name',)
