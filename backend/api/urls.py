from django.urls import include, path
from rest_framework import routers

from . import views

router = routers.DefaultRouter()

router.register(
    'users',
    views.UserViewSet,
    basename='user'
)
router.register(
    'ingredients',
    views.IngredientViewSet,
    basename='ingredient'
)
router.register(
    'tags',
    views.TagViewSet,
    basename='tag'
)
router.register(
    'recipes',
    views.RecipeViewSet,
    basename='recipe'
)

urlpatterns = [
    path('', include(router.urls)),
    path('auth/', include('djoser.urls.authtoken')),
]
