import csv

from django.core.management.base import BaseCommand
from django.db import transaction

from api.models import Ingredient


class Command(BaseCommand):
    help = 'Загрузка данных в модель ингредиентов из csv-файла'

    def add_arguments(self, parser):
        parser.add_argument(
            '--path',
            type=str,
            default='data/',
            help='Путь до csv-файлов'
        )

    @transaction.atomic
    def handle(self, *args, **options):
        base_path = options['path']
        self.load_ingredients(f'{base_path}ingredients.csv')

    def load_ingredients(self, file_path):
        self.stdout.write(f'Загрузка категорий из {file_path}.')
        with open(file_path, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                Ingredient.objects.get_or_create(
                    name=row['name'],
                    defaults={'measurement_unit': row['measurement_unit']}
                )
        self.stdout.write(self.style.SUCCESS('Ингредиенты загружены.'))
