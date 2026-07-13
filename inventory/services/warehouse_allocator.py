from inventory.models import Inventory
from warehouses.services.distance import haversine_distance


def allocate_warehouse(
    tenant,
    product,
    quantity,
    customer_latitude,
    customer_longitude,
):
    """
    Return the nearest warehouse that has enough stock.
    """

    inventories = (
        Inventory.objects
        .select_related("warehouse")
        .filter(
            tenant=tenant,
            product=product,
            quantity__gte=quantity,
            warehouse__latitude__isnull=False,
            warehouse__longitude__isnull=False,
        )
    )

    best_inventory = None
    shortest_distance = None

    for inventory in inventories:

        warehouse = inventory.warehouse

        distance = haversine_distance(
            customer_latitude,
            customer_longitude,
            warehouse.latitude,
            warehouse.longitude,
        )

        if (
            shortest_distance is None
            or distance < shortest_distance
        ):
            shortest_distance = distance
            best_inventory = inventory

    if best_inventory is None:
        return None

    return {
        "warehouse": best_inventory.warehouse,
        "inventory": best_inventory,
        "available_quantity": best_inventory.quantity,
        "distance_km": shortest_distance,
    }