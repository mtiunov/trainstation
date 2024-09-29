from django.contrib import admin

from .models import (
    Crew,
    TrainType,
    Train,
    Station,
    Route,
    Journey,
    Order,
    Ticket,
)

admin.site.register(Crew)
admin.site.register(Train)
admin.site.register(TrainType)
admin.site.register(Station)
admin.site.register(Route)
admin.site.register(Journey)
admin.site.register(Order)
admin.site.register(Ticket)
