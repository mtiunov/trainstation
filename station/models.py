from django.core.exceptions import ValidationError
from django.db import models
from django.conf import settings


class Crew(models.Model):
    first_name = models.CharField(max_length=255)
    last_name = models.CharField(max_length=255)

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    def __str__(self):
        return self.first_name + " " + self.last_name


class TrainType(models.Model):
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name


class Train(models.Model):
    name = models.CharField(max_length=255)
    cargo_num = models.PositiveIntegerField()
    places_in_cargo = models.PositiveIntegerField()
    train_type = models.ForeignKey(
        TrainType,
        related_name="trains",
        on_delete=models.PROTECT
    )

    @property
    def capacity(self):
        return self.cargo_num * self.places_in_cargo

    def __str__(self):
        return f"Train: {self.name}"

    class Meta:
        ordering = ["name"]


class Station(models.Model):
    name = models.CharField(max_length=255)
    latitude = models.FloatField()
    longitude = models.FloatField()

    def __str__(self):
        return self.name


class Route(models.Model):
    source = models.ForeignKey(
        Station, related_name="sources", on_delete=models.CASCADE
    )
    destination = models.ForeignKey(
        Station, related_name="destinations", on_delete=models.CASCADE
    )
    distance = models.PositiveIntegerField()

    class Meta:
        constraints = [models.UniqueConstraint(
            fields=["source", "destination"],
            name="unique_train_route"
        )]

    def __str__(self):
        return f"{self.source} to {self.destination}"


class Journey(models.Model):
    route = models.ForeignKey(
        Route,
        related_name="journey_trip",
        on_delete=models.CASCADE
    )
    train = models.ForeignKey(
        Train,
        related_name="journey_trip",
        on_delete=models.CASCADE
    )
    departure_time = models.DateTimeField()
    arrival_time = models.DateTimeField()
    crew = models.ManyToManyField(Crew, related_name="journey_trip")

    class Meta:
        ordering = ["train"]

    def __str__(self):
        return f"Route {self.route} by {self.train.name}"


class Order(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )

    def __str__(self):
        return str(self.created_at)

    class Meta:
        ordering = ["-created_at"]


class Ticket(models.Model):
    cargo = models.PositiveIntegerField()
    seat = models.PositiveIntegerField()
    journey = models.ForeignKey(
        Journey,
        on_delete=models.CASCADE,
        related_name="tickets"
    )
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="tickets"
    )

    class Meta:
        constraints = [models.UniqueConstraint(
            fields=["journey", "cargo", "seat"],
            name="unique_journey_cargo_seat"
        )]
        ordering = ["cargo", "seat"]

    @staticmethod
    def validate_ticket(cargo, seat, train, error_to_raise):
        for ticket_attr_value, ticket_attr_name, train_attr_name in [
            (cargo, "cargo", "cargo_num"),
            (seat, "seat", "places_in_cargo"),
        ]:
            count_attrs = getattr(train, train_attr_name)
            if not (1 <= ticket_attr_value <= count_attrs):
                raise error_to_raise(
                    {
                        ticket_attr_name: f"{ticket_attr_name} "
                        f"number must be in available range: "
                        f"(1, {train_attr_name}): "
                        f"(1, {count_attrs})"
                    }
                )

    def clean(self):
        Ticket.validate_ticket(
            self.cargo,
            self.seat,
            self.journey.train,
            ValidationError,
        )

    def save(
            self,
            force_insert=False,
            force_update=False,
            using=None,
            update_fields=None,
    ):
        self.full_clean()
        return super(Ticket, self).save(
            force_insert, force_update, using, update_fields
        )

    def __str__(self) -> str:
        return (
            f"{self.journey} (cargo: {self.cargo}, seat: {self.seat})"
        )
