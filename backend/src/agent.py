# food_agent_sqlite.py

"""
Day 7 – Food & Grocery Ordering Voice Agent (SQLite) - Venezuelan Food
- Uses SQLite DB 'order_db.sqlite'
- Seeds Venezuela Catalog (Harina Pan, Queso, Arroz, etc.)
- Tools: find_item, add_to_cart, remove_from_cart, update_cart, show_cart,
         add_recipe, place_order, cancel_order, get_order_status, order_history
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

DB_FILE = "order_db.sqlite"
CURRENCY_SYMBOL = "$"


def get_db_path() -> str:
    try:
        base = os.path.abspath(os.path.dirname(__file__))
    except NameError:
        base = os.getcwd()
    if not os.path.isdir(base):
        os.makedirs(base, exist_ok=True)
    return os.path.join(base, DB_FILE)


def get_conn():
    path = get_db_path()
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def seed_database():
    try:
        conn = get_conn()
        cur = conn.cursor()

        cur.execute("""
            CREATE TABLE IF NOT EXISTS catalog (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                category TEXT,
                price REAL NOT NULL,
                brand TEXT,
                size TEXT,
                units TEXT,
                tags TEXT
            )
        """)

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

        cur.execute("SELECT COUNT(1) FROM catalog")
        if cur.fetchone()[0] == 0:
            catalog = [
                ("harina-de-maiz-pan-1kg", "Harina de Maíz PAN", "Básicos", 1.80, "PAN", "1kg", "paquete", json.dumps(["harina", "arepas", "hallacas"])),
                ("arroz-blanco-1kg", "Arroz Granulado Tipo 1", "Básicos", 1.50, "Mary", "1kg", "paquete", json.dumps(["arroz", "pabellon"])),
                ("azucar-1kg", "Azúcar Refinada", "Básicos", 1.20, "Montalban", "1kg", "paquete", json.dumps(["dulce", "basico"])),
                ("sal-1kg", "Sal Marina", "Básicos", 0.80, "Refisal", "1kg", "paquete", json.dumps(["basico", "condimento"])),
                ("aceite-vegetal-1l", "Aceite Comestible", "Básicos", 3.50, "Vatel", "1L", "botella", json.dumps(["cocina", "fritura"])),
                ("leche-completa-1l", "Leche Completa", "Lácteos", 2.10, "Lácteos Los Andes", "1L", "cartón", json.dumps(["lacteo", "basico"])),
                ("queso-blanco-rallado-500g", "Queso Blanco Rallado", "Lácteos", 6.50, "Santa Bárbara", "500g", "paquete", json.dumps(["queso", "arepas", "basico"])),
                ("mantequilla-250g", "Margarina con Sal", "Lácteos", 2.50, "Mavesa", "250g", "barra", json.dumps(["lacteo"])),
                ("carne-de-res-500g", "Carne de Res de Primera", "Carnes", 8.00, "", "500g", "bandeja", json.dumps(["carne", "hallacas"])),
                ("pernil-de-cerdo-500g", "Pernil de Cerdo Fresco", "Carnes", 6.50, "", "500g", "bandeja", json.dumps(["carne", "hallacas"])),
                ("gallina-entera", "Gallina Criolla Entera", "Carnes", 12.00, "", "1.5kg", "unidad", json.dumps(["carne", "hallacas"])),
                ("carne-mechada-500g", "Carne para Pabellón", "Carnes", 7.50, "", "500g", "bandeja", json.dumps(["carne", "pabellon"])),
                ("redondo-de-res-1kg", "Redondo de Res para Asado", "Carnes", 15.00, "", "1kg", "pieza", json.dumps(["carne", "asado-negro"])),
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


seed_database()


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


RECIPE_MAP = {
    "hallacas": ["harina-de-maiz-pan-1kg", "carne-de-res-500g", "pernil-de-cerdo-500g", "gallina-entera", "aceite-onotado", "hojas-de-platano-paquete", "pasas-250g", "aceitunas-rellenas-frasco"],
    "arepas": ["harina-de-maiz-pan-1kg", "queso-blanco-rallado-500g", "aceite-vegetal-1l"],
    "pabellon": ["arroz-blanco-1kg", "carne-mechada-500g", "platano-maduro-unidad"],
    "asado negro": ["redondo-de-res-1kg", "papelon-panela", "vegetales-para-sofrito", "vino-tinto-seco-375ml"],
}
import re

_NUMBER_WORDS = {
    'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5,
    'six': 6, 'seven': 7, 'eight': 8, 'nine': 9, 'ten': 10,
    'uno': 1, 'dos': 2, 'tres': 3, 'cuatro': 4, 'cinco': 5,
    'seis': 6, 'siete': 7, 'ocho': 8, 'nueve': 9, 'diez': 10
}


def _parse_servings_from_text(text: str) -> int:
    text = (text or "").lower()
    m = re.search(r"(?:for|para)\s+(\d+)\s*(?:people|person|personas|persona)?", text)
    if m:
        try:
            return max(1, int(m.group(1)))
        except Exception:
            pass
    for word, num in _NUMBER_WORDS.items():
        if f"for {word}" in text or f"para {word}" in text:
            return num
    return 1


def _infer_items_from_tags(query: str, max_results: int = 6) -> List[str]:
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
    logger.info(f"🔄 [Simulation] Started tracking simulation for {order_id}")
    await asyncio.sleep(5)
    for next_status in STATUS_FLOW[1:]:
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


@function_tool
async def find_item(
    ctx: RunContext[Userdata],
    query: Annotated[str, Field(description="Nombre o parte del nombre del producto")],
) -> str:
    matches = search_catalog_by_name_db(query)
    if not matches:
        return f"No encontré productos que coincidan con '{query}'."
    lines = []
    for it in matches[:10]:
        lines.append(f"- {it['name']} (id: {it['id']}) — {CURRENCY_SYMBOL}{it['price']:.2f}")
    return "Encontré:\n" + "\n".join(lines)


@function_tool
async def add_to_cart(
    ctx: RunContext[Userdata],
    item_id: Annotated[str, Field(description="ID del producto")],
    quantity: Annotated[int, Field(description="Cantidad", default=1)] = 1,
    notes: Annotated[str, Field(description="Notas opcionales")] = "",
) -> str:
    item = find_catalog_item_by_id_db(item_id)
    if not item:
        return f"No encontré el producto con id '{item_id}'."
    for ci in ctx.userdata.cart:
        if ci.item_id.lower() == item_id.lower():
            ci.quantity += quantity
            if notes:
                ci.notes = notes
            total = cart_total(ctx.userdata.cart)
            return f"Actualicé '{ci.name}' a {ci.quantity} unidades. Total: {CURRENCY_SYMBOL}{total:.2f}"
    ci = CartItem(item_id=item["id"], name=item["name"], unit_price=float(item["price"]), quantity=quantity, notes=notes)
    ctx.userdata.cart.append(ci)
    total = cart_total(ctx.userdata.cart)
    return f"Agregué {quantity} x '{item['name']}' al carrito. Total: {CURRENCY_SYMBOL}{total:.2f}"


@function_tool
async def remove_from_cart(
    ctx: RunContext[Userdata],
    item_id: Annotated[str, Field(description="ID del producto a eliminar")],
) -> str:
    before = len(ctx.userdata.cart)
    ctx.userdata.cart = [ci for ci in ctx.userdata.cart if ci.item_id.lower() != item_id.lower()]
    after = len(ctx.userdata.cart)
    if before == after:
        return f"El producto '{item_id}' no estaba en tu carrito."
    total = cart_total(ctx.userdata.cart)
    return f"Eliminé '{item_id}' del carrito. Total: {CURRENCY_SYMBOL}{total:.2f}"


@function_tool
async def update_cart_quantity(
    ctx: RunContext[Userdata],
    item_id: Annotated[str, Field(description="ID del producto")],
    quantity: Annotated[int, Field(description="Nueva cantidad")],
) -> str:
    if quantity < 1:
        return await remove_from_cart(ctx, item_id)
    for ci in ctx.userdata.cart:
        if ci.item_id.lower() == item_id.lower():
            ci.quantity = quantity
            total = cart_total(ctx.userdata.cart)
            return f"Actualicé '{ci.name}' a {ci.quantity} unidades. Total: {CURRENCY_SYMBOL}{total:.2f}"
    return f"El producto '{item_id}' no está en tu carrito."


@function_tool
async def show_cart(ctx: RunContext[Userdata]) -> str:
    if not ctx.userdata.cart:
        return "Tu carrito está vacío."
    lines = []
    for ci in ctx.userdata.cart:
        lines.append(f"- {ci.quantity} x {ci.name} @ {CURRENCY_SYMBOL}{ci.unit_price:.2f} = {CURRENCY_SYMBOL}{ci.unit_price * ci.quantity:.2f}")
    total = cart_total(ctx.userdata.cart)
    return "Tu carrito:\n" + "\n".join(lines) + f"\nTotal: {CURRENCY_SYMBOL}{total:.2f}"


@function_tool
async def add_recipe(
    ctx: RunContext[Userdata],
    dish_name: Annotated[str, Field(description="Nombre del plato")],
) -> str:
    key = dish_name.strip().lower()
    if key not in RECIPE_MAP:
        available = ', '.join(f"'{d}'" for d in RECIPE_MAP.keys())
        return f"No tengo receta para '{dish_name}'. Intenta: {available}."
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
    return f"Agregué ingredientes para '{dish_name}': {', '.join(added)}. Total: {CURRENCY_SYMBOL}{total:.2f}"


@function_tool
async def ingredients_for(
    ctx: RunContext[Userdata],
    request: Annotated[str, Field(description="Solicitud en lenguaje natural")],
) -> str:
    text = (request or "").strip()
    servings = _parse_servings_from_text(text)
    m = re.search(r"ingredientes? (?:para|de) (.+)", text, re.I)
    if m:
        dish = m.group(1)
    else:
        m2 = re.search(r"(?:hacer|preparar|necesito para) (.+)", text, re.I)
        dish = m2.group(1) if m2 else text
    dish = re.sub(r"para\s+\w+(?: personas| persona)?", "", dish, flags=re.I).strip()
    key = dish.lower()
    item_ids = RECIPE_MAP.get(key, _infer_items_from_tags(dish))
    if not item_ids:
        return f"No pude determinar ingredientes para '{request}'."
    added = []
    for iid in item_ids:
        item = find_catalog_item_by_id_db(iid)
        if not item:
            continue
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
    return f"Agregué {', '.join(added)} para '{dish}' ({servings} porciones). Total: {CURRENCY_SYMBOL}{total:.2f}"


@function_tool
async def place_order(
    ctx: RunContext[Userdata],
    customer_name: Annotated[str, Field(description="Nombre del cliente")],
    address: Annotated[str, Field(description="Dirección de entrega")],
) -> str:
    if not ctx.userdata.cart:
        return "Tu carrito está vacío."
    order_id = str(uuid.uuid4())[:8]
    now = datetime.utcnow().isoformat() + "Z"
    total = cart_total(ctx.userdata.cart)
    insert_order_db(order_id=order_id, timestamp=now, total=total, customer_name=customer_name, address=address, status="received", items=ctx.userdata.cart)
    ctx.userdata.cart = []
    ctx.userdata.customer_name = customer_name
    try:
        asyncio.create_task(simulate_delivery_flow(order_id))
    except RuntimeError:
        pass
    return f"¡Pedido realizado! ID: {order_id}. Total: {CURRENCY_SYMBOL}{total:.2f}. El rastreo express está activado."


@function_tool
async def cancel_order(
    ctx: RunContext[Userdata],
    order_id: Annotated[str, Field(description="ID del pedido")],
) -> str:
    o = get_order_db(order_id)
    if not o:
        return f"No encontré el pedido {order_id}."
    status = o.get("status", "")
    if status == "delivered":
        return f"El pedido {order_id} ya fue entregado."
    if status == "cancelled":
        return f"El pedido {order_id} ya está cancelado."
    update_order_status_db(order_id, "cancelled")
    return f"Pedido {order_id} cancelado exitosamente."


@function_tool
async def get_order_status(
    ctx: RunContext[Userdata],
    order_id: Annotated[str, Field(description="ID del pedido")],
) -> str:
    o = get_order_db(order_id)
    if not o:
        return f"No encontré el pedido {order_id}."
    return f"Pedido {order_id} — Estado: {o.get('status')}. Actualizado: {o.get('updated_at')}"


@function_tool
async def order_history(
    ctx: RunContext[Userdata],
    customer_name: Annotated[Optional[str], Field(description="Nombre del cliente", default=None)] = None,
) -> str:
    rows = list_orders_db(limit=5, customer_name=customer_name)
    if not rows:
        return "No hay pedidos."
    lines = [f"- {o['order_id']} | {CURRENCY_SYMBOL}{o['total']:.2f} | {o.get('status')}" for o in rows]
    prefix = "Pedidos Recientes" + (f" de {customer_name}" if customer_name else "")
    return prefix + ":\n" + "\n".join(lines)


class FoodAgent(Agent):
    def __init__(self):
        super().__init__(
            instructions="""Eres Marielena, asistente de compras de Forum Supermayoristas. Hablas SIEMPRE en español con acento venezolano amigable. Usas frases como '¡Hola!', '¡Chévere!'. Ayudas a buscar productos, gestionar el carrito, sugerir recetas venezolanas (hallacas, arepas, pabellón) y hacer pedidos. Los precios son en dólares ($). Saluda con entusiasmo y confirma cada acción.""",
            tools=[find_item, add_to_cart, remove_from_cart, update_cart_quantity, show_cart, add_recipe, ingredients_for, place_order, cancel_order, get_order_status, order_history],
        )


def prewarm(proc: JobProcess):
    try:
        proc.userdata["vad"] = silero.VAD.load()
    except Exception:
        logger.warning("VAD prewarm failed")


async def entrypoint(ctx: JobContext):
    ctx.log_context_fields = {"room": ctx.room.name}
    logger.info("🚀 STARTING Marielena Agent")
    userdata = Userdata()
    session = AgentSession(
        stt=deepgram.STT(model="nova-3", language="es"),
        llm=google.LLM(model="gemini-2.0-flash"),
        tts=murf.TTS(voice="es-MX-luisa", style="Conversational", text_pacing=True),
        turn_detection=MultilingualModel(),
        vad=ctx.proc.userdata.get("vad"),
        userdata=userdata,
    )
    await session.start(agent=FoodAgent(), room=ctx.room, room_input_options=RoomInputOptions(noise_cancellation=noise_cancellation.BVC()))
    await ctx.connect()


if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint, prewarm_fnc=prewarm))
