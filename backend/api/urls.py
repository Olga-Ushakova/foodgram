from django.urls import include, path
from django.views.generic import TemplateView
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
    path('docs/',
         TemplateView.as_view(template_name='docs/redoc.html'),
         name='docs'
         ),
    path('docs/openapi-schema.yml',
         TemplateView.as_view(
             template_name='docs/openapi-schema.yml',
             content_type='application/yaml'
         ),
         name='openapi-schema'),
]
