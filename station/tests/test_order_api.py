from datetime import datetime

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from rest_framework.test import APIClient
from rest_framework import status

from station.models import Order, Journey, Route, Station, Train, TrainType
from station.serializers import OrderListSerializer

ORDER_URL = reverse("station:order-list")


def sample_user(**params):
    defaults = {
        "first_name": "Bill",
        "last_name": "Gates"
    }
    defaults.update(params)
    return get_user_model().objects.create_user(**defaults)


def sample_order(**params):
    if not params.get("user"):
        user = sample_user()
    else:
        user = params.get("user")

    defaults = {"user": user}
    defaults.update(params)

    return Order.objects.create(**defaults)


def sample_train_type(**params):
    defaults = {"name": "train_type_name"}
    defaults.update(params)

    return TrainType.objects.create(**defaults)


def sample_journey(**params):
    source_station = Station.objects.create(
        name="Station A",
        latitude=50.4501,
        longitude=30.5234
    )
    destination_station = Station.objects.create(
        name="Station B",
        latitude=49.8397,
        longitude=24.0297
    )
    route = Route.objects.create(
        source=source_station,
        destination=destination_station,
        distance=300
    )
    train = Train.objects.create(
        name="Sample Train",
        cargo_num=10,
        places_in_cargo=50,
        train_type=sample_train_type()
    )

    defaults = {
        "route": route,
        "train": train,
        "departure_time": datetime(
            year=2024,
            month=5,
            day=2,
            hour=13,
            minute=30
        ),
        "arrival_time": datetime(
            year=2024,
            month=5,
            day=3,
            hour=15,
            minute=10
        )
    }
    defaults.update(params)

    return Journey.objects.create(**defaults)


class UnauthenticatedOrderApiTests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()

    def test_auth_required(self):
        res = self.client.get(ORDER_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedCrewApiTests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "test@test.com",
            "testpass"
        )
        self.client.force_authenticate(self.user)

    def test_list_order(self):
        sample_order(user=self.user)

        res = self.client.get(ORDER_URL)

        orders = Order.objects.filter(user=self.user)
        serializer = OrderListSerializer(orders, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data.get("results"), serializer.data)

    def test_create_order_with_tickets(self):
        data = {
            "tickets": [
                {
                    "cargo": 1,
                    "seat": 2,
                    "journey": sample_journey().id
                }
            ]
        }
        res = self.client.post(ORDER_URL, data=data, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

    def test_create_order_without_tickets(self):
        data = {"tickets": []}

        res = self.client.post(ORDER_URL, data=data)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
