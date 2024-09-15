from datetime import datetime, timedelta
from operator import itemgetter
from django.contrib.auth import get_user_model

from django.db.models import F, Count
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from station.models import Journey, Station, TrainType, Order, Route, Train, Crew
from station.serializers import JourneyDetailSerializer, JourneyListSerializer
from station.views import JourneyViewSet


def sample_user(**params):
    defaults = {
        "email": "user@user.com",
        "password": "test1234",
        "first_name": "Bill",
        "last_name": "Gates"
    }
    defaults.update(params)
    return get_user_model().objects.create_user(**defaults)


def sample_superuser(**params):
    defaults = {
        "email": "admin@admin.com",
        "password": "testTest",
        "first_name": "Mice",
        "last_name": "Cheese"
    }
    defaults.update(params)
    return get_user_model().objects.create_superuser(**defaults)


def sample_order(**params):
    if not params.get("user"):
        user = sample_user()
    else:
        user = params.get("user")

    defaults = {"user": user}
    defaults.update(params)

    return Order.objects.create(**defaults)


def sample_train(**params):
    train_type = sample_train_type()

    defaults = {
        "name": "sample_train",
        "cargo_num": 10,
        "places_in_cargo": 10,
        "train_type": train_type
    }
    defaults.update(params)
    return Train.objects.create(**defaults)


def sample_route(**params):
    source = sample_station()
    destination = sample_station(
        name="destination", latitude=44.0, longitude=56.0
    )

    defaults = {
        "source": source,
        "destination": destination,
        "distance": 100
    }
    defaults.update(params)

    return Route.objects.create(**defaults)


def sample_train_type(**params):
    defaults = {"name": "train_type_name"}
    defaults.update(params)

    return TrainType.objects.create(**defaults)


def sample_station(**params):
    defaults = {
        "name": "Station A",
        "latitude": 45.0,
        "longitude": 25.0
    }
    defaults.update(params)
    return Station.objects.create(**defaults)


def sample_crew(**params):
    defaults = {
        "first_name": "Bill",
        "last_name": "Gates"
    }
    defaults.update(params)
    return Crew.objects.create(**defaults)


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


JOURNEY_URL = reverse("station:journey-list")


def detail_url(journey_id):
    return reverse("station:journey-detail", args=[journey_id])


class UnauthenticatedJourneyApiTests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()

    def test_auth_required(self):
        res = self.client.get(JOURNEY_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedJourneyApiTests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.user = sample_user()
        self.client.force_authenticate(self.user)

        self.journey = sample_journey()
        self.another_journey = sample_journey(
            route=sample_route(
                source=sample_station(
                    name="new_source_station"
                ),
                destination=sample_station(
                    name="new_destination_station"
                )
            ),
            departure_time=datetime(year=2024, month=8, day=3),
            arrival_time=datetime(year=2024, month=8, day=5)
        )
        self.journeys = Journey.objects.annotate(
            tickets_available=(
                    F("train__cargo_num")
                    * F("train__places_in_cargo")
                    - Count("tickets")
            )
        )

    def test_list_journey(self):
        res = self.client.get(JOURNEY_URL)

        serializer = JourneyListSerializer(self.journeys, many=True)
        serializer_data = sorted(serializer.data, key=itemgetter("id"))

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer_data)

    def test_retrieve_journey(self):
        res = self.client.get(detail_url(self.journey.id))

        journey_with_tickets = Journey.objects.annotate(
            tickets_available=(
                    F("train__cargo_num") * F("train__places_in_cargo")
                    - Count("tickets")
            )
        ).get(id=self.journey.id)

        serializer = JourneyDetailSerializer(journey_with_tickets)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_create_journey_forbidden(self):
        data = {
            "route": sample_route().id,
            "train": sample_train().id,
            "crew": [sample_crew().id],
            "departure_time": (
                    datetime.now() + timedelta(days=1)
            ),
            "arrival_time": (
                    datetime.now() + timedelta(days=2)
            ),
        }
        res = self.client.post(JOURNEY_URL, data)

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_update_journey_forbidden(self):
        data = {
            "arrival_time": (
                    datetime.now() + timedelta(days=2)
            )
        }
        res = self.client.patch(detail_url(self.journey.id), data)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_delete_journey_forbidden(self):
        res = self.client.delete(detail_url(self.journey.id))

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_filter_journeys_by_source_station(self):
        res = self.client.get(JOURNEY_URL, {"from": "new_sour"})

        default_journey_serializer = JourneyListSerializer(self.journey)
        new_journey_serializer = JourneyListSerializer(
            self.journeys.get(id=self.another_journey.id)
        )

        self.assertNotIn(default_journey_serializer.data, res.data)
        self.assertIn(new_journey_serializer.data, res.data)

    def test_filter_journeys_by_destination(self):
        res = self.client.get(JOURNEY_URL, {"to": "new_destin"})

        default_journey_serializer = JourneyListSerializer(self.journey)
        new_journey_serializer = JourneyListSerializer(
            self.journeys.get(id=self.another_journey.id)
        )

        self.assertNotIn(default_journey_serializer.data, res.data)
        self.assertIn(new_journey_serializer.data, res.data)

    def test_filter_by_departure_date(self):
        res = self.client.get(JOURNEY_URL, {"departure_date": "2024-05-01"})

        default_journey_serializer = JourneyListSerializer(self.journey)
        new_journey_serializer = JourneyListSerializer(
            self.journeys.get(id=self.another_journey.id)
        )

        self.assertNotIn(default_journey_serializer.data, res.data)
        self.assertIn(new_journey_serializer.data, res.data)

    def test_filter_by_arrival_date(self):
        res = self.client.get(JOURNEY_URL, {"arrival_date": "2024-05-02"})

        default_journey_serializer = JourneyListSerializer(self.journey)
        new_journey_serializer = JourneyListSerializer(
            self.journeys.get(id=self.another_journey.id)
        )

        self.assertNotIn(default_journey_serializer.data, res.data)
        self.assertIn(new_journey_serializer.data, res.data)


class AdminJourneyApiTest(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.user = sample_superuser()
        self.journey = sample_journey()
        self.client.force_authenticate(self.user)

    def test_create_journey(self):
        data = {
            "route": sample_route().id,
            "train": sample_train().id,
            "crew": [sample_crew().id],
            "departure_time": (
                datetime.now() + timedelta(days=4)
            ),
            "arrival_time": (
                datetime.now() + timedelta(days=5)
            ),
        }
        res = self.client.post(JOURNEY_URL, data)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

    def test_create_journey_with_arrival_less_than_departure_date(self):
        data = {
            "route": sample_route().id,
            "train": sample_train().id,
            "crew": [sample_crew().id],
            "departure_time": (
                    datetime.now() + timedelta(days=5)
            ),
            "arrival_time": (
                    datetime.now() + timedelta(days=2)
            ),
        }
        res = self.client.post(JOURNEY_URL, data)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            res.data.get("non_field_errors")[0],
            "Departure time can't be bigger than arrival time"
        )

    def test_update_journey(self):
        data = {
            "departure_time": (
                    datetime.now() + timedelta(days=3)
            ),
            "arrival_time": (
                    datetime.now() + timedelta(days=6)
            )
        }

        res = self.client.patch(detail_url(self.journey.id), data)

        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_delete_journey(self):
        res = self.client.delete(detail_url(self.journey.id))
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
