# food_agent_sqlite.py
"""
Day 7 – Food & Grocery Ordering Voice Agent (SQLite) - Venezuelan Food
- Uses SQLite DB 'order_db.sqlite'
- Seeds Venezuela Catalog (Harina Pan, Queso, Arroz, etc.)
- Tools:
    - find_item (search catalog)
    - add_to_cart / remove_from_cart / update_cart / show_cart
    - add_recipe (ingredients for Hallacas, Pabellón, etc.)
    - place_order (Trigger auto-status update simulation)
    - cancel_order (New Feature)
    - get_order_status / order_history
- Auto-simulation: Status updates every 5 seconds in background.
"""

import json
import logging
import os
import sqlite3
import uuid
import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Annotated

from dotenv import load_dotenv
from pydantic import Field
from livekit.agents import (
    Agent,
    AgentSession,
    JobContext,
    JobProcess,
    RoomInputOptions,
    WorkerOptions,
    cli,
    function_tool,
    RunContext,
)

from livekit.plugins import murf, silero, google, deepgram, noise_cancellation
from livekit.plugins.turn_detector.multilingual import MultilingualModel

# Logging
logger = logging.getLogger("food_agent_sqlite")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
logger.addHandler(handler)

load_dotenv(".env.local")

# DB config & seeding
DB_FILE = "order_db.sqlite"

# Símbolo de moneda constante para fácil cambio si es necesario
CURRENCY_SYMBOL = "$" 


def get_db_path() -> str:
    """Return absolute path for the DB file. If __file__ is not defined (interactive), fall back to cwd."""
    try:
        base = os.path.abspath(os.path.dirname(__file__))
    except NameError:
        base = os.getcwd()
    # ensure directory exists
    if not os.path.isdir(base):
        os.makedirs(base, exist_ok=True)
    return os.path.join(base, DB_FILE)


def get_conn():
    path = get_db_path()
    # check_same_thread=False required for async background tasks accessing DB
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def seed_database():
    """Create tables and seed the Venezuelan catalog if empty."""
    try:
        conn = get_conn()
        cur = conn.cursor()

        # Create catalog table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS catalog (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                category TEXT,
                price REAL NOT NULL,
                brand TEXT,
                size TEXT,
                units TEXT,
                tags TEXT -- JSON encoded list
            )
        """)

        # Orders table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                order_id TEXT PRIMARY KEY,
                timestamp TEXT,
                total REAL,
                customer_name TEXT,
                address TEXT,
                status TEXT DEFAULT 'received',
                created_at TEXT DEFAULT (datetime('now')),
                updated_at TEXT DEFAULT (datetime('now'))
            )
        """)

        # Order items
        cur.execute("""
            CREATE TABLE IF NOT EXISTS order_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id TEXT,
                item_id TEXT,
                name TEXT,
                unit_price REAL,
                quantity INTEGER,
                notes TEXT,
                FOREIGN KEY(order_id) REFERENCES orders(order_id) ON DELETE CASCADE
            )
        """)

        # Check if catalog empty
        cur.execute("SELECT COUNT(1) FROM catalog")
        if cur.fetchone()[0] == 0:
            catalog = [
                # Básicos Venezolanos
                ("harina-de-maiz-pan-1kg", "Harina de Maíz PAN", "Básicos", 1.80, "PAN", "1kg", "paquete", json.dumps(["harina", "arepas", "hallacas"])),
                ("arroz-blanco-1kg", "Arroz Granulado Tipo 1", "Básicos", 1.50, "Mary", "1kg", "paquete", json.dumps(["arroz", "pabellon"])),
                ("azucar-1kg", "Azúcar Refinada", "Básicos", 1.20, "Montalban", "1kg", "paquete", json.dumps(["dulce", "basico"])),
                ("sal-1kg", "Sal Marina", "Básicos", 0.80, "Refisal", "1kg", "paquete", json.dumps(["basico", "condimento"])),
                ("aceite-vegetal-1l", "Aceite Comestible", "Básicos", 3.50, "Vatel", "1L", "botella", json.dumps(["cocina", "fritura"])),
                
                # Lácteos y Similares
                ("leche-completa-1l", "Leche Completa", "Lácteos", 2.10, "Lácteos Los Andes", "1L", "cartón", json.dumps(["lacteo", "basico"])),
                ("queso-blanco-rallado-500g", "Queso Blanco Rallado", "Lácteos", 6.50, "Santa Bárbara", "500g", "paquete", json.dumps(["queso", "arepas", "basico"])),
                ("mantequilla-250g", "Margarina con Sal", "Lácteos", 2.50, "Mavesa", "250g", "barra", json.dumps(["lacteo"])),
                
                # Carnes (Simuladas - Precios por 500g o unidad)
                ("carne-de-res-500g", "Carne de Res de Primera", "Carnes", 8.00, "", "500g", "bandeja", json.dumps(["carne", "hallacas"])),
                ("pernil-de-cerdo-500g", "Pernil de Cerdo Fresco", "Carnes", 6.50, "", "500g", "bandeja", json.dumps(["carne", "hallacas"])),
                ("gallina-entera", "Gallina Criolla Entera", "Carnes", 12.00, "", "1.5kg", "unidad", json.dumps(["carne", "hallacas"])),
                ("carne-mechada-500g", "Carne para Pabellón", "Carnes", 7.50, "", "500g", "bandeja", json.dumps(["carne", "pabellon"])),
                ("redondo-de-res-1kg", "Redondo de Res para Asado", "Carnes", 15.00, "", "1kg", "pieza", json.dumps(["carne", "asado-negro"])),
                
                # Condimentos y Extras
                ("aceite-onotado", "Aceite Onotado", "Condimentos", 4.50, "El Gran Chef", "250ml", "frasco", json.dumps(["hallacas", "color"])),
                ("hojas-de-platano-paquete", "Hojas de Plátano", "Extras", 3.00, "Frescas", "20unid", "paquete", json.dumps(["hallacas"])),
                ("pasas-250g", "Pasas Morenas", "Condimentos", 2.00, "La Venezolana", "250g", "paquete", json.dumps(["hallacas", "dulce"])),
                ("aceitunas-rellenas-frasco", "Aceitunas Rellenas", "Condimentos", 4.00, "Serpis", "300g", "frasco", json.dumps(["hallacas"])),
                ("papelon-panela", "Papelón en Panela", "Básicos", 1.50, "El Campesino", "500g", "panela", json.dumps(["dulce", "asado-negro"])),
                ("vegetales-para-sofrito", "Vegetales para Sofrito (Mixto)", "Vegetales", 5.00, "Forum", "500g", "bolsa", json.dumps(["sofrito", "hallacas", "asado-negro"])),
                ("vino-tinto-seco-375ml", "Vino Tinto Seco", "Licores", 7.00, "Santa Elena", "375ml", "botella", json.dumps(["cocina", "asado-negro"])),
                ("platano-maduro-unidad", "Plátano Maduro", "Vegetales", 0.75, "", "unidad", "unidad", json.dumps(["pabellon", "fruta"])),
            ]
            cur.executemany("""
                INSERT INTO catalog (id, name, category, price, brand, size, units, tags)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, catalog)
            conn.commit()
            logger.info(f"✅ Seeded Venezuelan catalog into {get_db_path()}")

        conn.close()
    except Exception as e:
        logger.exception("Failed to seed database: %s", e)


# Seed DB on import/run (safe to call multiple times)
seed_database()

# In-memory per-session cart
@dataclass
class CartItem:
    item_id: str
    name: str
    unit_price: float
    quantity: int = 1
    notes: str = ""

@dataclass
class Userdata:
    cart: List[CartItem] = field(default_factory=list)
    customer_name: Optional[str] = None

# DB Helpers

def find_catalog_item_by_id_db(item_id: str) -> Optional[dict]:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM catalog WHERE LOWER(id) = LOWER(?) LIMIT 1", (item_id,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    record = dict(row)
    try:
        record["tags"] = json.loads(record.get("tags") or "[]")
    except Exception:
        record["tags"] = []
    return record


def search_catalog_by_name_db(query: str) -> List[dict]:
    q = f"%{query.lower()}%"
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT * FROM catalog
        WHERE LOWER(name) LIKE ? OR LOWER(tags) LIKE ?
        LIMIT 50
    """, (q, q))
    rows = cur.fetchall()
    conn.close()
    results = []
    for r in rows:
        rec = dict(r)
        try:
            rec["tags"] = json.loads(rec.get("tags") or "[]")
        except Exception:
            rec["tags"] = []
        results.append(rec)
    return results


def insert_order_db(order_id: str, timestamp: str, total: float, customer_name: str, address: str, status: str, items: List[CartItem]):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO orders (order_id, timestamp, total, customer_name, address, status, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))
    """, (order_id, timestamp, total, customer_name, address, status))
    for ci in items:
        cur.execute("""
            INSERT INTO order_items (order_id, item_id, name, unit_price, quantity, notes)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (order_id, ci.item_id, ci.name, ci.unit_price, ci.quantity, ci.notes))
    conn.commit()
    conn.close()


def get_order_db(order_id: str) -> Optional[dict]:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM orders WHERE order_id = ? LIMIT 1", (order_id,))
    o = cur.fetchone()
    if not o:
        conn.close()
        return None
    order = dict(o)
    cur.execute("SELECT * FROM order_items WHERE order_id = ?", (order_id,))
    items = [dict(r) for r in cur.fetchall()]
    conn.close()
    order["items"] = items
    return order


def list_orders_db(limit: int = 10, customer_name: Optional[str] = None) -> List[dict]:
    conn = get_conn()
    cur = conn.cursor()
    if customer_name:
        cur.execute("SELECT * FROM orders WHERE LOWER(customer_name) = LOWER(?) ORDER BY created_at DESC LIMIT ?", (customer_name, limit))
    else:
        cur.execute("SELECT * FROM orders ORDER BY created_at DESC LIMIT ?", (limit,))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def update_order_status_db(order_id: str, new_status: str) -> bool:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE orders SET status = ?, updated_at = datetime('now') WHERE order_id = ?", (new_status, order_id))
    changed = cur.rowcount
    conn.commit()
    conn.close()
    return changed > 0

# LOGIC & ASYNC SIMULATION

RECIPE_MAP = {
    "hallacas": [
        "harina-de-maiz-pan-1kg",
        "carne-de-res-500g", 
        "pernil-de-cerdo-500g",
        "gallina-entera",
        "aceite-onotado",
        "hojas-de-platano-paquete",
        "pasas-250g",
        "aceitunas-rellenas-frasco",
    ],
    "arepas fritas": [
        "harina-de-maiz-pan-1kg", 
        "queso-blanco-rallado-500g", 
        "aceite-vegetal-1l"
    ],
    "pabellon criollo": [
        "arroz-blanco-1kg", 
        "caraotas-negras-1kg", 
        "carne-mechada-500g", 
        "platano-maduro-unidad"
    ],
    "asado negro": [
        "redondo-de-res-1kg", 
        "papelon-panela", 
        "vegetales-para-sofrito",
        "vino-tinto-seco-375ml"
    ],
}

# Intelligent ingredient inference helpers
import re

_NUMBER_WORDS = {
    'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5,
    'six': 6, 'seven': 7, 'eight': 8, 'nine': 9, 'ten': 10
}

def _parse_servings_from_text(text: str) -> int:
    """Try to extract servings/quantity from informal text like 'for two people' or 'for 3'. Default 1."""
    text = (text or "").lower()
    m = re.search(r"for\s+(\d+)\s*(?:people|person|servings)?", text)
    if m:
        try:
            return max(1, int(m.group(1)))
        except Exception:
            pass
    for word, num in _NUMBER_WORDS.items():
        if f"for {word}" in text:
            return num
    return 1


def _infer_items_from_tags(query: str, max_results: int = 6) -> List[str]:
    """Try to infer catalog items by matching query words to tags in the catalog. Returns list of item_ids."""
    words = re.findall(r"\w+", (query or "").lower())
    found = []
    conn = get_conn()
    cur = conn.cursor()
    for w in words:
        if len(found) >= max_results:
            break
        q = f"%\"{w}\"%"
        cur.execute("SELECT * FROM catalog WHERE LOWER(tags) LIKE ? OR LOWER(name) LIKE ? LIMIT 10", (q, f"%{w}%"))
        rows = cur.fetchall()
        for r in rows:
            rid = r["id"]
            if rid not in found:
                found.append(rid)
                if len(found) >= max_results:
                    break
    conn.close()
    return found

STATUS_FLOW = ["received", "confirmed", "shipped", "out_for_delivery", "delivered"]


async def simulate_delivery_flow(order_id: str):
    """
    Background task: automatically advances order status every 5 seconds.
    Flow: received -> confirmed -> shipped -> out_for_delivery -> delivered
    """
    logger.info(f"🔄 [Simulation] Started tracking simulation for {order_id}")

    # initial wait
    await asyncio.sleep(5)

    # Loop through statuses starting from index 1 (confirmed)
    for next_status in STATUS_FLOW[1:]:
        # Check if order was cancelled in the meantime
        curr_order = get_order_db(order_id)
        if curr_order and curr_order.get("status") == "cancelled":
            logger.info(f"🛑 [Simulation] Order {order_id} was cancelled. Stopping simulation.")
            return

        update_order_status_db(order_id, next_status)
        logger.info(f"🚚 [Simulation] Order {order_id} updated to '{next_status}'")
        await asyncio.sleep(5)

    logger.info(f"✅ [Simulation] Order {order_id} simulation complete (Delivered).")


def cart_total(cart: List[CartItem]) -> float:
    return round(sum(ci.unit_price * ci.quantity for ci in cart), 2)

# Agent Tools
@function_tool
async def find_item(
    ctx: RunContext[Userdata],
    query: Annotated[str, Field(description="Name or partial name of item (e.g., 'leche', 'queso')")],
) -> str:
    matches = search_catalog_by_name_db(query)
    if not matches:
        return f"No items found matching '{query}'. Try generic names like 'leche' or 'arroz'."
    lines = []
    for it in matches[:10]:
        lines.append(f"- {it['name']} (id: {it['id']}) — {CURRENCY_SYMBOL}{it['price']:.2f} — {it.get('size','')}")
    return "Found:\n" + "\n".join(lines)


@function_tool
async def add_to_cart(
    ctx: RunContext[Userdata],
    item_id: Annotated[str, Field(description="Catalog item id")],
    quantity: Annotated[int, Field(description="Quantity", default=1)] = 1,
    notes: Annotated[str, Field(description="Optional notes")] = "",
) -> str:
    item = find_catalog_item_by_id_db(item_id)
    if not item:
        return f"Item id '{item_id}' not found."

    for ci in ctx.userdata.cart:
        if ci.item_id.lower() == item_id.lower():
            ci.quantity += quantity
            if notes:
                ci.notes = notes
            total = cart_total(ctx.userdata.cart)
            # CAMBIO DE MONEDA: ₹ a $
            return f"Updated '{ci.name}' quantity to {ci.quantity}. Cart total: {CURRENCY_SYMBOL}{total:.2f}"

    ci = CartItem(item_id=item["id"], name=item["name"], unit_price=float(item["price"]), quantity=quantity, notes=notes)
    ctx.userdata.cart.append(ci)
    total = cart_total(ctx.userdata.cart)
    # CAMBIO DE MONEDA: ₹ a $
    return f"Added {quantity} x '{item['name']}' to cart. Cart total: {CURRENCY_SYMBOL}{total:.2f}"


@function_tool
async def remove_from_cart(
    ctx: RunContext[Userdata],
    item_id: Annotated[str, Field(description="Catalog item id to remove")],
) -> str:
    before = len(ctx.userdata.cart)
    ctx.userdata.cart = [ci for ci in ctx.userdata.cart if ci.item_id.lower() != item_id.lower()]
    after = len(ctx.userdata.cart)
    if before == after:
        return f"Item '{item_id}' was not in your cart."
    total = cart_total(ctx.userdata.cart)
    # CAMBIO DE MONEDA: ₹ a $
    return f"Removed item '{item_id}' from cart. Cart total: {CURRENCY_SYMBOL}{total:.2f}"


@function_tool
async def update_cart_quantity(
    ctx: RunContext[Userdata],
    item_id: Annotated[str, Field(description="Catalog item id to update")],
    quantity: Annotated[int, Field(description="New quantity")],
) -> str:
    if quantity < 1:
        return await remove_from_cart(ctx, item_id)
    for ci in ctx.userdata.cart:
        if ci.item_id.lower() == item_id.lower():
            ci.quantity = quantity
            total = cart_total(ctx.userdata.cart)
            # CAMBIO DE MONEDA: ₹ a $
            return f"Updated '{ci.name}' quantity to {ci.quantity}. Cart total: {CURRENCY_SYMBOL}{total:.2f}"
    return f"Item '{item_id}' not found in cart."


@function_tool
async def show_cart(ctx: RunContext[Userdata]) -> str:
    if not ctx.userdata.cart:
        return "Your cart is empty."
    lines = []
    for ci in ctx.userdata.cart:
        # CAMBIO DE MONEDA: ₹ a $
        lines.append(f"- {ci.quantity} x {ci.name} @ {CURRENCY_SYMBOL}{ci.unit_price:.2f} each = {CURRENCY_SYMBOL}{ci.unit_price * ci.quantity:.2f}")
    total = cart_total(ctx.userdata.cart)
    # CAMBIO DE MONEDA: ₹ a $
    return "Your cart:\n" + "\n".join(lines) + f"\nTotal: {CURRENCY_SYMBOL}{total:.2f}"


@function_tool
async def add_recipe(
    ctx: RunContext[Userdata],
    dish_name: Annotated[str, Field(description="Name of dish, e.g. 'hallacas venezolanas', 'pabellon criollo'")],
) -> str:
    key = dish_name.strip().lower()
    if key not in RECIPE_MAP:
        # Actualizado para sugerir recetas venezolanas
        available_dishes = ', '.join(f"'{d}'" for d in RECIPE_MAP.keys())
        return f"Sorry, I don't have a recipe for '{dish_name}'. Try one of these: {available_dishes}."
    added = []
    for item_id in RECIPE_MAP[key]:
        item = find_catalog_item_by_id_db(item_id)
        if not item:
            continue

        found = False
        for ci in ctx.userdata.cart:
            if ci.item_id.lower() == item_id.lower():
                ci.quantity += 1
                found = True
                break
        if not found:
            ctx.userdata.cart.append(CartItem(item_id=item["id"], name=item["name"], unit_price=float(item["price"]), quantity=1))
        added.append(item["name"])

    total = cart_total(ctx.userdata.cart)
    # CAMBIO DE MONEDA: ₹ a $
    return f"Added ingredients for '{dish_name}': {', '.join(added)}. Cart total: {CURRENCY_SYMBOL}{total:.2f}"


@function_tool
async def ingredients_for(
    ctx: RunContext[Userdata],
    request: Annotated[str, Field(description="Natural language request, e.g. 'ingredients for peanut butter sandwich for two'")],
) -> str:
    """Handle high-level ingredient requests like 'ingredients for peanut butter sandwich' or 'get me pasta for two people'.
    Attempts a map lookup first, then falls back to tag inference.
    """
    text = (request or "").strip()
    servings = _parse_servings_from_text(text)

    # try to extract a dish phrase after common verbs
    m = re.search(r"ingredients? for (.+)", text, re.I)
    if m:
        dish = m.group(1)
    else:
        m2 = re.search(r"(?:make|for making|get me what i need for|i need) (.+)", text, re.I)
        dish = m2.group(1) if m2 else text

    # remove trailing 'for X people' fragments
    dish = re.sub(r"for\s+\w+(?: people| person| persons)?", "", dish, flags=re.I).strip()
    key = dish.lower()

    item_ids = []
    if key in RECIPE_MAP:
        item_ids = RECIPE_MAP[key]
    else:
        item_ids = _infer_items_from_tags(dish)

    if not item_ids:
        # Actualizado para sugerir artículos venezolanos
        return f"Sorry, I couldn't determine ingredients for '{request}'. Try a simpler phrase like 'queso' or 'arepas'."

    added = []
    for iid in item_ids:
        item = find_catalog_item_by_id_db(iid)
        if not item:
            continue
        # add with servings as quantity
        found = False
        for ci in ctx.userdata.cart:
            if ci.item_id.lower() == iid.lower():
                ci.quantity += servings
                found = True
                break
        if not found:
            ctx.userdata.cart.append(CartItem(item_id=item['id'], name=item['name'], unit_price=float(item['price']), quantity=servings))
        added.append(item['name'])

    total = cart_total(ctx.userdata.cart)
    # CAMBIO DE MONEDA: ₹ a $
    return f"I've added {', '.join(added)} to your cart for '{dish}'. (Servings: {servings}). Cart total: {CURRENCY_SYMBOL}{total:.2f}"


@function_tool
async def place_order(
    ctx: RunContext[Userdata],
    customer_name: Annotated[str, Field(description="Customer name")],
    address: Annotated[str, Field(description="Delivery address")],
) -> str:
    if not ctx.userdata.cart:
        return "Your cart is empty."

    order_id = str(uuid.uuid4())[:8]
    now = datetime.utcnow().isoformat() + "Z"
    total = cart_total(ctx.userdata.cart)

    # 1. Persist to DB
    insert_order_db(order_id=order_id, timestamp=now, total=total, customer_name=customer_name, address=address, status="received", items=ctx.userdata.cart)

    # 2. Clear Cart
    ctx.userdata.cart = []
    ctx.userdata.customer_name = customer_name

    # 3. Trigger Background Simulation (Received -> Shipped -> Out for delivery...)
    try:
        # create a background task on the running event loop
        asyncio.create_task(simulate_delivery_flow(order_id))
    except RuntimeError:
        # If there is no running loop, schedule on a new loop in a background thread
        loop = asyncio.new_event_loop()
        asyncio.get_running_loop() if asyncio.get_event_loop().is_running() else None
        # fire-and-forget: run in background
        asyncio.get_event_loop().call_soon_threadsafe(lambda: asyncio.create_task(simulate_delivery_flow(order_id)))

    # CAMBIO DE MONEDA: ₹ a $
    return f"Order placed successfully! Order ID: {order_id}. Total: {CURRENCY_SYMBOL}{total:.2f}. I have initiated express shipping; the status will update automatically shortly."


@function_tool
async def cancel_order(
    ctx: RunContext[Userdata],
    order_id: Annotated[str, Field(description="Order ID to cancel")],
) -> str:
    o = get_order_db(order_id)
    if not o:
        return f"No order found with id {order_id}."

    status = o.get("status", "")
    if status == "delivered":
        return f"Order {order_id} has already been delivered and cannot be cancelled."

    if status == "cancelled":
        return f"Order {order_id} is already cancelled."

    # Update DB
    update_order_status_db(order_id, "cancelled")
    return f"Order {order_id} has been cancelled successfully."


@function_tool
async def get_order_status(
    ctx: RunContext[Userdata],
    order_id: Annotated[str, Field(description="Order ID to check")],
) -> str:
    o = get_order_db(order_id)
    if not o:
        return f"No order found with id {order_id}."
    return f"Order {order_id} status: {o.get('status', 'unknown')}. Updated at: {o.get('updated_at')}"


@function_tool
async def order_history(
    ctx: RunContext[Userdata],
    customer_name: Annotated[Optional[str], Field(description="Optional customer name to filter", default=None)] = None,
) -> str:
    rows = list_orders_db(limit=5, customer_name=customer_name)
    if not rows:
        return "No orders found."
    lines = []
    for o in rows:
        # CAMBIO DE MONEDA: ₹ a $
        lines.append(f"- {o['order_id']} | {CURRENCY_SYMBOL}{o['total']:.2f} | Status: {o.get('status')}")
    prefix = "Recent Orders"
    if customer_name:
        prefix += f" for {customer_name}"
    return prefix + ":\n" + "\n".join(lines)

# Agent Definition
class FoodAgent(Agent):
    def __init__(self):
        super().__init__(
    instructions="""
    You are **Marielena**, a highly professional, friendly, and enthusiastic AI voice shopping assistant for **'Forum Supermayoristas'**, the major Venezuelan supermarket chain.
    
    **Primary Goal:** Help the customer quickly and easily find ingredients, get recipe lists, and manage their shopping cart using only voice commands.
    
    ### Key Rules and Persona
    1. **ALWAYS respond to the customer in SPANISH (español).**
    2. Be conversational and highly professional. Use friendly Venezuelan phrases occasionally (e.g., '¡Hola!', '¡Chévere!').
    3. Use the **US Dollar ($)** for all prices and totals, as this is the primary currency for Forum Supermayoristas.
    4. After using a tool, respond clearly, professionally, and enthusiastically in **SPANISH** based on the tool's result.
    5. Start the conversation with a warm, Marielena-style greeting in SPANISH (e.g., "¡Hola vale! Soy Marielena de Forum, ¡estoy lista para ayudarte con tus compras!").
    
    ### Capabilities and Tool Usage
    You must use the provided tools to fulfill customer requests.
    
    1. **Catalog:** Search for Venezuelan items (e.g., leche, frutas, sal, Pasta, arroz). Use the `find_item` tool.
    2. **Cart Management:** Use `add_to_cart`, `remove_from_cart`, `update_cart_quantity`, and `show_cart` to manage the customer's items.
    3. **Recipes:** When a customer asks for a recipe (e.g., Hallacas Venezolanas, Maggi, Paneer Butter Masala), use the `add_recipe` tool. List the ingredients clearly and ask if they want to add them to the cart.
    4. **Orders:** * When the customer is done, offer to place the order using the `place_order` tool.
        * When placing an order, mention that **express tracking is enabled**.
        * You can **CANCEL** an order if the user asks, provided it's not delivered yet (use `cancel_order`).
        * If the user asks "Where is my order?" (¿Dónde está mi pedido?), use `get_order_status` to check the status. Since the status advances automatically (simulated), encourage them to check back in a few seconds.
        * Use `order_history` to retrieve past orders.
    """,
    tools=[find_item, add_to_cart, remove_from_cart, update_cart_quantity, show_cart, add_recipe, place_order, cancel_order, get_order_status, order_history],
)

def prewarm(proc: JobProcess):
    # load VAD model and stash on process userdata
    try:
        proc.userdata["vad"] = silero.VAD.load()
    except Exception:
        logger.warning("VAD prewarm failed; continuing without preloaded VAD.")


async def entrypoint(ctx: JobContext):
    ctx.log_context_fields = {"room": ctx.room.name}
    logger.info("\n" + "🇻🇪" * 12)
    logger.info("🚀 STARTING Marielena (Venezuelan Context + Auto-Tracking)")

    userdata = Userdata()

    session = AgentSession(
        stt=deepgram.STT(model="nova-3"),
        llm=google.LLM(model="gemini-2.5-flash"),
        tts=murf.TTS(
            voice="es-MX-luisa",
            style="Conversational",
            text_pacing=True,
        ),
        turn_detection=MultilingualModel(),
        vad=ctx.proc.userdata.get("vad"),
        userdata=userdata,
    )

    await session.start(
        agent=FoodAgent(),
        room=ctx.room,
        room_input_options=RoomInputOptions(noise_cancellation=noise_cancellation.BVC()),
    )

    await ctx.connect()


if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint, prewarm_fnc=prewarm))
