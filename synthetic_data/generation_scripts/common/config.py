from faker import Faker
import random

SEED = 42

fake = Faker("en_IN")

Faker.seed(SEED)
random.seed(SEED)