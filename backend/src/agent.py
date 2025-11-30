import uuid
from typing import List, Dict, Optional
from datetime import datetime

# --- Product Catalog (Shoes, USD) ---
PRODUCTS: List[Dict] = [
    {
        "id": "snk-001",
        "name": "Performance Running Sneaker",
        "description": "Lightweight mesh sneaker for daily runs.",
        "price": 89.99,
        "currency": "USD",
        "category": "sneaker",
        "attributes": {"size": [7, 8, 9, 10, 11, 12], "color": ["black", "white", "blue"], "brand": "StridePro"},
    },
    {
        "id": "bst-002",
        "name": "Leather Chelsea Boot",
        "description": "Classic pull-on leather boots for formal or casual wear.",
        "price": 149.99,
        "currency": "USD",
        "category": "boot",
        "attributes": {"size": [8, 9, 10, 11], "color": ["brown", "black"], "brand": "Elegance"},
    },
    {
        "id": "sandal-003",
        "name": "Comfort Slide Sandal",
        "description": "Ergonomic slide sandals for indoor and outdoor relaxation.",
        "price": 35.50,
        "currency": "USD",
        "category": "sandal",
        "attributes": {"size": [5, 6, 7, 8, 9, 10], "color": ["grey", "pink"], "brand": "RelaxWear"},
    },
    {
        "id": "snk-004",
        "name": "Retro High-Top Sneaker",
        "description": "Vintage-style sneaker with ankle support.",
        "price": 105.00,
        "currency": "USD",
        "category": "sneaker",
        "attributes": {"size": [9, 10, 11, 12], "color": ["red", "white"], "brand": "Apex"},
    },
]

# --- Order Storage (In-memory) ---
ORDERS: List[Dict] = []

def get_product_by_id(product_id: str) -> Optional[Dict]:
    """Helper to find a product by ID."""
    return next((p for p in PRODUCTS if p['id'] == product_id), None)

def list_products(filters: Optional[Dict] = None) -> List[Dict]:
    """
    Filters and returns a list of products (shoes) from the catalog.
    
    Args:
        filters: An optional dictionary with filters.
                 Example: {"category": "sneaker", "max_price": 100, "color": "black"}

    Returns:
        A list of products that match the criteria.
    """
    if not filters:
        return PRODUCTS[:3]

    results = []
    normalized_filters = {k.lower(): str(v).lower() for k, v in filters.items()}

    for product in PRODUCTS:
        match = True
        
        if 'max_price' in normalized_filters:
            try:
                max_price = float(normalized_filters['max_price'])
                if product['price'] > max_price:
                    match = False
            except ValueError:
                pass 
        
        if 'category' in normalized_filters and match:
            if normalized_filters['category'] not in product['category'].lower():
                match = False

        if 'name' in normalized_filters and match:
            search_term = normalized_filters['name']
            if search_term not in product['name'].lower() and search_term not in product['description'].lower():
                 match = False

        # Filter by attributes (size, color, brand, etc.)
        if 'attribute' in normalized_filters and match:
            search_attr = normalized_filters['attribute']
            attr_found = False
            
            for attr_key, attr_val in product.get('attributes', {}).items():
                if isinstance(attr_val, list):
                    if search_attr in [str(item).lower() for item in attr_val]:
                        attr_found = True
                        break
                elif search_attr in str(attr_val).lower():
                    attr_found = True
                    break
            
            if not attr_found:
                match = False

        if match:
            results.append(product)

    return results

def create_order(line_items: List[Dict]) -> Dict:
    """
    Creates a new order in the shoe commerce system.
    
    Args:
        line_items: List of items to purchase. Format:
                    [{ "product_id": "snk-001", "quantity": 1, "selected_size": 10 }, ...]

    Returns:
        The created order object.
    """
    if not line_items:
        raise ValueError("The list of line items cannot be empty.")

    order_id = str(uuid.uuid4())
    total = 0.0
    processed_items = []
    currency = "USD" 

    for item in line_items:
        product_id = item.get("product_id")
        quantity = item.get("quantity", 1)
        selected_size = item.get("selected_size")

        product = get_product_by_id(product_id)
        
        if product:
            # Note: In a real app, we'd check inventory and size availability here.
            
            price = product['price'] * quantity
            total += price
            
            processed_items.append({
                "product_id": product_id,
                "name": product['name'],
                "quantity": quantity,
                "unit_price": product['price'],
                "line_total": price,
                "size": selected_size,
            })
        else:
            raise ValueError(f"Product with ID {product_id} not found.")

    if not processed_items:
        raise ValueError("No valid items could be processed for the order.")

    new_order = {
        "id": order_id,
        "items": processed_items,
        "total": round(total, 2),
        "currency": currency,
        "created_at": datetime.now().isoformat(),
        "status": "confirmed"
    }

    ORDERS.append(new_order)
    return new_order

def get_last_order() -> Optional[Dict]:
    """
    Returns the last order created.
    """
    return ORDERS[-1] if ORDERS else None
