from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from . import models


@admin.register(models.User)
class UserAdmin(BaseUserAdmin):
    """Настройка админ-зоны для модели Пользователя."""

    list_display = ('username', 'first_name', 'last_name', 'email')
    search_fields = ('email', 'first_name')


@admin.register(models.Tag)
class TagAdmin(admin.ModelAdmin):
    """Настройка админ-зоны для модели Тега."""

    list_display = ('name', 'slug')
    search_fields = ('name',)


@admin.register(models.Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    """Настройка админ-зоны для модели Ингредиента."""

    list_display = ('name', 'measurement_unit')
    search_fields = ('name',)


class IngredientInRecipeInline(admin.TabularInline):
    """Класс для отображения ингредиентов рецепта."""

    model = models.IngredientInRecipe
    extra = 1
    min_num = 1
    verbose_name = 'Ингредиент рецепта'
    verbose_name_plural = 'Ингредиенты рецепта'


@admin.register(models.Recipe)
class RecipeAdmin(admin.ModelAdmin):
    """Настройка админ-зоны для модели Рецепта."""

    list_display = ('name', 'author')
    search_fields = ('name', 'author__username')
    list_filter = ('tags',)
    readonly_fields = ('favorites_count',)
    inlines = [IngredientInRecipeInline]
    filter_horizontal = ('tags',)

    def favorites_count(self, recipe):
        return recipe.favorites.count()
    favorites_count.short_description = 'Кол-во добавлений в Избранное'


admin.site.register(models.Subscription)
admin.site.register(models.IngredientInRecipe)
admin.site.register(models.ShoppingCart)
admin.site.register(models.Favorite)
