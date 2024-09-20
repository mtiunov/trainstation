from datetime import datetime

from rest_framework import viewsets, mixins, status
from rest_framework.viewsets import GenericViewSet
from django.db.models import F, Count
from rest_framework.decorators import action
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from station.permissions import IsAdminOrIfAuthenticatedReadOnly

from station.models import (
    Crew,
    TrainType,
    Train,
    Station,
    Route,
    Journey,
    Order,
)

from station.serializers import (
    CrewSerializer,
    TrainTypeSerializer,
    TrainSerializer,
    TrainListSerializer,
    TrainDetailSerializer,
    StationSerializer,
    RouteSerializer,
    RouteListSerializer,
    RouteDetailSerializer,
    JourneySerializer,
    JourneyListSerializer,
    JourneyDetailSerializer,
    OrderSerializer,
    OrderListSerializer,
    TrainImageSerializer,
)


class CrewViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    GenericViewSet
):
    queryset = Crew.objects.all()
    serializer_class = CrewSerializer
    permission_classes = (IsAdminOrIfAuthenticatedReadOnly,)


class TrainTypeViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet
):
    queryset = TrainType.objects.all()
    serializer_class = TrainTypeSerializer
    permission_classes = (IsAdminOrIfAuthenticatedReadOnly,)


class TrainViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet
):
    queryset = Train.objects.select_related("train_type")
    serializer_class = TrainSerializer
    permission_classes = (IsAdminOrIfAuthenticatedReadOnly,)

    @staticmethod
    def _params_to_ints(qs):
        """Converts a list of string IDs to a list of integers"""
        return [int(str_id) for str_id in qs.split(",")]

    def get_queryset(self):
        """Retrieve the trains with filters"""
        name = self.request.query_params.get("name")
        train_type = self.request.query_params.get("trains")

        queryset = self.queryset

        if name:
            queryset = queryset.filter(name__icontains=name)

        if train_type:
            train_type_ids = self._params_to_ints(train_type)
            queryset = queryset.filter(genres__id__in=train_type_ids)

        return queryset.distinct()

    def get_serializer_class(self):
        if self.action == "list":
            return TrainListSerializer

        if self.action == "retrieve":
            return TrainDetailSerializer

        if self.action == "upload_image":
            return TrainImageSerializer

        return TrainSerializer

    @action(
        methods=["POST"],
        detail=True,
        url_path="upload-image",
        permission_classes=[IsAdminUser],
    )
    def upload_image(self, request, pk=None):
        """Endpoint for uploading image to specific train"""
        train = self.get_object()
        serializer = self.get_serializer(train, data=request.data)

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        parameters=[
            OpenApiParameter(
                "name",
                type=OpenApiTypes.STR,
                description="Filter by train name (ex. ?name=Freight Express)",
            ),
            OpenApiParameter(
                "train_type",
                type=OpenApiTypes.STR,
                description="Filter by train_type (ex. ?train_type=Local)",
            ),
        ]
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)


class StationViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet
):
    queryset = Station.objects.all()
    serializer_class = StationSerializer
    permission_classes = (IsAdminOrIfAuthenticatedReadOnly,)


class RouteViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet
):
    queryset = Route.objects.select_related("source", "destination")
    serializer_class = RouteSerializer
    permission_classes = (IsAdminOrIfAuthenticatedReadOnly,)

    @staticmethod
    def _params_to_ints(qs):
        """Converts a list of string IDs to a list of integers"""
        return [int(str_id) for str_id in qs.split(",")]

    def get_queryset(self):
        """Retrieve the trains with filters"""
        source = self.request.query_params.get("source")
        destination = self.request.query_params.get("destination")

        queryset = self.queryset

        if source:
            queryset = queryset.filter(source_id=source)

        if destination:
            queryset = queryset.filter(destination_id=destination)

        return queryset.distinct()

    def get_serializer_class(self):
        if self.action == "list":
            return RouteListSerializer

        if self.action == "retrieve":
            return RouteDetailSerializer

        return RouteSerializer

    @extend_schema(
        parameters=[
            OpenApiParameter(
                "source",
                type=OpenApiTypes.STR,
                description="Filter by source (ex. ?source=Kharkov Passenger)",
            ),
            OpenApiParameter(
                "destination",
                type=OpenApiTypes.STR,
                description=(
                    "Filter by destination "
                    "(ex. ?destination=Lviv Railway Station)"
                ),
            ),
        ]
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)


class JourneyViewSet(viewsets.ModelViewSet):
    queryset = (
        Journey.objects.all()
        .select_related("route__source", "route__destination", "train")
        .annotate(
            tickets_available=(
                F("train__cargo_num") * F("train__places_in_cargo")
                - Count("tickets")
            )
        )
    )
    serializer_class = JourneySerializer
    permission_classes = (IsAdminOrIfAuthenticatedReadOnly,)

    def get_queryset(self):
        queryset = self.queryset

        train_type = self.request.query_params.get("trains")
        from_station = self.request.query_params.get("from")
        to_station = self.request.query_params.get("to")
        departure = self.request.query_params.get("departure_time")
        arrival = self.request.query_params.get("arrival_time")

        if train_type:
            queryset = queryset.filter(train__train_type__icontains=train_type)

        if from_station:
            queryset = queryset.filter(
                route__source__name__icontains=from_station
            )

        if to_station:
            queryset = queryset.filter(
                route__destination__name__icontains=to_station
            )

        if departure:
            departure_time = datetime.strptime(departure, "%Y-%m-%d")
            queryset = queryset.filter(departure_time__date=departure_time)

        if arrival:
            arrival_time = datetime.strptime(arrival, "%Y-%m-%d")
            queryset = queryset.filter(arrival_time__date=arrival_time)

        return queryset

    def get_serializer_class(self):
        if self.action == "list":
            return JourneyListSerializer

        if self.action == "retrieve":
            return JourneyDetailSerializer

        return JourneySerializer

    @extend_schema(
        parameters=[
            OpenApiParameter(
                "train_type",
                type=OpenApiTypes.STR,
                description="Filter by train (ex. ?train_type=Express)",
            ),
            OpenApiParameter(
                "from_station",
                type=OpenApiTypes.STR,
                description=(
                    "Filter by from "
                    "(ex. ?from_station=Kyiv Train Station)"
                ),
            ),
            OpenApiParameter(
                "to_station",
                type=OpenApiTypes.STR,
                description=(
                    "Filter by to "
                    "(ex. ?to_station=Kharkov Passenger)"
                ),
            ),
            OpenApiParameter(
                "departure",
                type=OpenApiTypes.DATE,
                description=(
                    "Filter by datetime of departure"
                    "(ex. ?date=2024-08-20)"
                ),
            ),
            OpenApiParameter(
                "arrival",
                type=OpenApiTypes.DATE,
                description=(
                    "Filter by datetime of arrival"
                    "ex. ?date=2024-08-21)"
                ),
            ),
        ]
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)


class OrderPagination(PageNumberPagination):
    page_size = 10
    max_page_size = 100


class OrderViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    GenericViewSet
):
    queryset = Order.objects.prefetch_related(
        "tickets__journey__route__source",
        "tickets__journey__route__destination",
        "tickets__journey__train"
    )
    serializer_class = OrderSerializer
    pagination_class = OrderPagination
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user)

    def get_serializer_class(self):
        if self.action == "list":
            return OrderListSerializer

        return OrderSerializer

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
