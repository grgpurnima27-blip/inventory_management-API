from inventory.models import Inventory
from warehouses.services.distance import haversine_distance


def allocate_warehouse(
    tenant,
    product,
    quantity,
    customer_latitude=None,
    customer_longitude=None,
):
    """
    Return the nearest warehouse that has enough stock.
    
    If customer coordinates are provided, find the nearest warehouse.
    If not, fall back to any warehouse with sufficient stock.
    """

    # Base query for all available inventories
    inventories = (
        Inventory.objects
        .select_related("warehouse")
        .filter(
            tenant=tenant,
            product=product,
            quantity__gte=quantity,
        )
    )

    # If coordinates are provided, try to find nearest warehouse
    if customer_latitude is not None and customer_longitude is not None:
        # Filter to warehouses with coordinates
        inventories_with_coords = inventories.filter(
            warehouse__latitude__isnull=False,
            warehouse__longitude__isnull=False,
        )
        
        best_inventory = None
        shortest_distance = None

        for inventory in inventories_with_coords:
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

        if best_inventory:
            return {
                "warehouse": best_inventory.warehouse,
                "inventory": best_inventory,
                "available_quantity": best_inventory.quantity,
                "distance_km": shortest_distance,
            }
        
        # If no warehouse with coordinates found, fall through to fallback

    # Fallback: return first available warehouse without coordinate filtering
    if not inventories.exists():
        return None

    inventory = inventories.first()
    return {
        "warehouse": inventory.warehouse,
        "inventory": inventory,
        "available_quantity": inventory.quantity,
        "distance_km": None,
    }