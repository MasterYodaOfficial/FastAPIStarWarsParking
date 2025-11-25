import factory

from models import Client, Parking


class ClientFactory(factory.Factory):
    class Meta:
        model = Client

    name = factory.Faker("first_name")
    surname = factory.Faker("last_name")
    credit_card = factory.Maybe(
        factory.Faker("boolean"),
        yes_declaration=factory.Faker("credit_card_number"),
        no_declaration=None,
    )
    car_number = factory.Faker("bothify", text="?###??")


class ParkingFactory(factory.Factory):
    class Meta:
        model = Parking

    address = factory.Faker("address")
    opened = factory.Faker("boolean")
    count_places = factory.Faker("random_int", min=10, max=500)
    count_available_places = factory.LazyAttribute(lambda o: o.count_places)
