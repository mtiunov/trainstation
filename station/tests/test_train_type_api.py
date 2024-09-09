from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from rest_framework.test import APIClient
from rest_framework import status

from station.models import TrainType, Train
from station.serializers import TrainTypeSerializer


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


def sample_train_type(**params):
    defaults = {"name": "passenger"}
    defaults.update(params)
    return TrainType.objects.create(**defaults)


TRAIN_TYPE_URL = reverse("station:traintype-list")


class UnauthenticatedTrainTypeApiTest(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()

    def test_auth_required(self):
        res = self.client.get(TRAIN_TYPE_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedTrainTypeApiTest(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.user = sample_user()
        self.client.force_authenticate(self.user)

    def test_list_train_type(self):
        sample_train_type()
        sample_train_type()

        res = self.client.get(TRAIN_TYPE_URL)

        train_types = TrainType.objects.all()
        serializer = TrainTypeSerializer(train_types, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_create_train_type_forbidden(self):
        data = {"name": "new_train_type"}

        res = self.client.post(TRAIN_TYPE_URL, data)

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class AdminTrainTypeApiTest(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.user = sample_superuser()
        self.client.force_authenticate(self.user)

    def test_create_train_type(self):
        data = {"name": "new_name_train_type"}
        res = self.client.post(TRAIN_TYPE_URL, data)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(TrainType.objects.last().name, "new_name_train_type")
