from rest_framework.pagination import PageNumberPagination

from .constants import PAGE_SIZE


class LimitPagination(PageNumberPagination):
    """
    Пагинатор с параметром limit,
    отвечающим за количество результатов в выдаче.
    """

    page_size_query_param = 'limit'
    page_size = PAGE_SIZE
