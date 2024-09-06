from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from rest_framework.test import APIClient
from rest_framework import status

from station.models import Route, Station
from station.serializers import RouteSerializer, RouteListSerializer, RouteDetailSerializer


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


ROUTE_URL = reverse("station:route-list")


def detail_url(route_id):
    return reverse("station:route-detail", args=[route_id])


class UnauthenticatedStationApiTest(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()

    def test_auth_required(self):
        res = self.client.get(ROUTE_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedRouteApiTest(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.user = sample_user()
        self.route = sample_route()
        self.client.force_authenticate(self.user)

    def test_list_route(self):
        sample_route()

        res = self.client.get(ROUTE_URL)

        routes = Route.objects.all()
        serializer = RouteListSerializer(routes, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_retrieve_route(self):
        res = self.client.get(detail_url(self.route.id))

        serializer = RouteDetailSerializer(self.route)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_create_route_forbidden(self):
        data = {
            "source": sample_station(),
            "destination": sample_station(name="Station A"),
            "distance": 25
        }

        res = self.client.post(ROUTE_URL, data)

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_filter_routes_by_sourse(self):
        new_station = sample_station(name="Station B")
        new_route = sample_route(source=new_station)

        res = self.client.get(ROUTE_URL, {"source": new_station.id})

        default_route_serializer = RouteListSerializer(self.route)
        new_route_serializer = RouteListSerializer(new_route)

        self.assertIn(new_route_serializer.data, res.data)
        self.assertNotIn(default_route_serializer.data, res.data)

    def test_filter_routes_by_destination(self):
        new_station = sample_station(name="Station C")
        new_route = sample_route(destination=new_station)

        res = self.client.get(ROUTE_URL, {"destination": new_station.id})

        default_route_serializer = RouteListSerializer(self.route)
        new_route_serializer = RouteListSerializer(new_route)

        self.assertIn(new_route_serializer.data, res.data)
        self.assertNotIn(default_route_serializer.data, res.data)


class AdminRouteApiTest(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.user = sample_superuser()
        self.route = sample_route()
        self.client.force_authenticate(self.user)

    def test_create_route(self):
        data = {
            "source": sample_station(name="source_station").id,
            "destination": sample_station(name="destination_station").id,
            "distance": 20
        }

        res = self.client.post(ROUTE_URL, data)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

    def test_create_with_same_source_and_destination(self):
        station = sample_station()
        data = {
            "source": station.id,
            "destination": station.id,
            "distance": 10
        }

        res = self.client.post(ROUTE_URL, data)

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            res.data.get("non_field_errors")[0],
            "Source can't be equal to Destination"
        )

    def test_update_route_not_allowed(self):
        data = {"distance": 10}

        res = self.client.put(detail_url(self.route.id), data)
        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_delete_route_not_allowed(self):
        res = self.client.delete(detail_url(self.route.id))

        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
