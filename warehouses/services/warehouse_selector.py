# warehouses/services/warehouse_selector.py

from warehouses.models import Warehouse
from warehouses.services.distance import haversine_distance


def get_nearest_warehouse(tenant, latitude, longitude):
    """
    Return the nearest warehouse for a tenant.
    """

    warehouses = Warehouse.objects.filter(
        tenant=tenant
    ).exclude(
        latitude__isnull=True,
        longitude__isnull=True
    )

    nearest = None
    shortest_distance = None

    for warehouse in warehouses:

        distance = haversine_distance(
            latitude,
            longitude,
            warehouse.latitude,
            warehouse.longitude
        )

        if (
            shortest_distance is None
            or distance < shortest_distance
        ):
            shortest_distance = distance
            nearest = warehouse

    if nearest is None:
        return None

    return {
        "warehouse_id": nearest.id,
        "warehouse_name": nearest.name,
        "city": nearest.city,
        "location": nearest.location,
        "latitude": nearest.latitude,
        "longitude": nearest.longitude,
        "distance_km": shortest_distance,
    }