import random
from datetime import date, timedelta

def random_date(start_year=2018, end_year=2025):
    start = date(start_year, 1, 1)
    end = date(end_year, 12, 31)

    days = (end - start).days

    return start + timedelta(days=random.randint(0, days))


def random_salary(min_salary, max_salary):
    return random.randint(min_salary, max_salary)


def choose(items):
    return random.choice(items)