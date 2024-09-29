from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from rest_framework.test import APIClient
from rest_framework import status

from station.models import Station
from station.serializers import StationSerializer


def sample_user(**params):
    defaults = {
        "email": "user@user.com",
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


def sample_station(**params):
    defaults = {
        "name": "Station A",
        "latitude": 45.0,
        "longitude": 25.0
    }
    defaults.update(params)
    return Station.objects.create(**defaults)


STATION_URL = reverse("station:station-list")


def detail_url(station_id):
    return reverse("station:station-detail", args=[station_id])


class UnauthenticatedStationApiTest(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()

    def test_auth_required(self):
        res = self.client.get(STATION_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedStationApiTest(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.user = sample_user()
        self.station = sample_station()
        self.client.force_authenticate(self.user)

    def test_list_station(self):
        sample_station()

        res = self.client.get(STATION_URL)

        stations = Station.objects.all()
        serializer = StationSerializer(stations, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_retrieve_station(self):
        res = self.client.get(detail_url(self.station.id))

        serializer = StationSerializer(self.station)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_create_station_forbidden(self):
        data = {
            "name": "Station A",
            "latitude": 45.0,
            "longitude": 25.0
        }

        res = self.client.post(STATION_URL, data)

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class AdminStationApiTest(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.user = sample_superuser()
        self.station = sample_station()
        self.client.force_authenticate(self.user)

    def test_create_station(self):
        data = {
            "name": "Station B",
            "latitude": 40.0,
            "longitude": 20.0
        }
        res = self.client.post(STATION_URL, data)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

    def test_update_station_not_allowed(self):
        data = {"name": "Station C"}

        res = self.client.put(detail_url(self.station.id), data)

        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_delete_station_not_allowed(self):
        res = self.client.delete(detail_url(self.station.id))

        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
