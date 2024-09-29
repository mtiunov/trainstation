from django.db import transaction
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from station.models import (
    Crew,
    TrainType,
    Train,
    Station,
    Route,
    Journey,
    Ticket,
    Order,
)


class CrewSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)

    class Meta:
        model = Crew
        fields = ("id", "first_name", "last_name", "full_name")


class TrainTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = TrainType
        fields = ("id", "name")


class TrainSerializer(serializers.ModelSerializer):
    class Meta:
        model = Train
        fields = (
            "id",
            "name",
            "cargo_num",
            "places_in_cargo",
            "train_type",
        )


class TrainListSerializer(TrainSerializer):
    train_capacity = serializers.SerializerMethodField()

    class Meta:
        model = Train
        fields = (
            "id",
            "name",
            "train_type",
            "train_capacity",
        )

    def get_train_capacity(self, obj) -> int:
        return obj.capacity


class TrainDetailSerializer(TrainSerializer):
    train_type = serializers.SlugRelatedField(
        read_only=True, slug_field="name"
    )
    train_capacity = serializers.SerializerMethodField()

    class Meta:
        model = Train
        fields = (
            "id",
            "name",
            "train_type",
            "train_capacity",
        )

    def get_train_capacity(self, obj) -> int:
        return obj.capacity


class TrainImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Train
        fields = ("id", "image")


class StationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Station
        fields = ("id", "name", "latitude", "longitude")


class RouteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Route
        fields = ("id", "source", "destination", "distance")

    def validate(self, attrs):
        if attrs['source'] == attrs['destination']:
            raise serializers.ValidationError(
                "Source can't be equal to Destination"
            )
        return attrs


class RouteListSerializer(RouteSerializer):
    source = serializers.SlugRelatedField(
        read_only=True, slug_field="name"
    )
    destination = serializers.SlugRelatedField(
        read_only=True, slug_field="name"
    )


class RouteDetailSerializer(RouteSerializer):
    source = StationSerializer(read_only=True)
    destination = StationSerializer(read_only=True)


class JourneySerializer(serializers.ModelSerializer):
    class Meta:
        model = Journey
        fields = (
            "id",
            "route",
            "train",
            "departure_time",
            "arrival_time",
            "crew",
        )

    def validate(self, attrs):
        departure_time = attrs.get("departure_time")
        arrival_time = attrs.get("arrival_time")

        if departure_time and arrival_time and departure_time >= arrival_time:
            raise serializers.ValidationError(
                "Departure time can't be bigger than arrival time"
            )

        return attrs


class JourneyListSerializer(JourneySerializer):
    train_name = serializers.CharField(source="train.name", read_only=True)
    route_name = serializers.StringRelatedField(read_only=True)
    tickets_available = serializers.IntegerField(read_only=True)

    class Meta:
        model = Journey
        fields = (
            "id",
            "train_name",
            "route_name",
            "departure_time",
            "arrival_time",
            "tickets_available",
        )


class JourneyDetailSerializer(JourneySerializer):
    route = RouteDetailSerializer(read_only=True)
    train = TrainDetailSerializer(read_only=True)
    crew = CrewSerializer(many=True, read_only=True)
    tickets_available = serializers.IntegerField(read_only=True)

    class Meta:
        model = Journey
        fields = (
            "id",
            "route",
            "train",
            "crew",
            "departure_time",
            "arrival_time",
            "tickets_available",
        )


class TicketSerializer(serializers.ModelSerializer):
    def validate(self, attrs):
        data = super(TicketSerializer, self).validate(attrs=attrs)
        Ticket.validate_ticket(
            attrs["cargo"],
            attrs["seat"],
            attrs["journey"].train,
            ValidationError
        )
        return data

    class Meta:
        model = Ticket
        fields = ("id", "cargo", "seat", "journey")


class TicketListSerializer(TicketSerializer):
    journey = JourneyListSerializer(many=False, read_only=True)


class TicketSeatSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ticket
        fields = ("cargo", "seat")


class OrderSerializer(serializers.ModelSerializer):
    tickets = TicketSerializer(many=True, read_only=False, allow_empty=False)

    class Meta:
        model = Order
        fields = ("id", "tickets", "created_at")

    def create(self, validated_data):
        with transaction.atomic():
            tickets_data = validated_data.pop("tickets")
            order = Order.objects.create(**validated_data)
            for ticket_data in tickets_data:
                Ticket.objects.create(order=order, **ticket_data)
            return order


class OrderListSerializer(OrderSerializer):
    tickets = TicketListSerializer(many=True, read_only=True)
