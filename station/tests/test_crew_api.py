from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from rest_framework.test import APIClient
from rest_framework import status

from station.models import Crew
from station.serializers import CrewSerializer

CREW_URL = reverse("station:crew-list")


def sample_crew(**params):
    defaults = {
        "first_name": "Bill",
        "last_name": "Gates"
    }
    defaults.update(params)
    return Crew.objects.create(**defaults)


class UnauthenticatedCrewApiTests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()

    def test_auth_required(self):
        res = self.client.get(CREW_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedCrewApiTests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "test@test.com",
            "testpass"
        )
        self.client.force_authenticate(self.user)

    def test_list_crew(self):
        sample_crew()
        sample_crew(first_name="John", last_name="Doe")

        res = self.client.get(CREW_URL)

        crews = Crew.objects.all()
        serializer = CrewSerializer(crews, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_create_crew_forbidden(self):
        data = {
            "first_name": "Bob",
            "last_name": "Snail",
        }
        res = self.client.post(CREW_URL, data)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class AdminCrewApiTests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "admin@admin.com", "testpass", is_staff=True
        )
        self.client.force_authenticate(self.user)

    def test_create_crew(self):
        data = {
            "first_name": "Bob",
            "last_name": "Snail",
        }
        res = self.client.post(CREW_URL, data)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        crew = Crew.objects.get(id=res.data["id"])
        for key in data.keys():
            self.assertEqual(data[key], getattr(crew, key))
