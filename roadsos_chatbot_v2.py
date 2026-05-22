"""
RoadSoS - Road Emergency AI Assistant  (v2.0 — Google Maps Enhanced)
Road Safety Hackathon 2026 - BIMSTEC Countries
Theme: AI in Road Safety

NEW in v2.0:
    - Every trauma centre now shows a clickable Google Maps link (opens in browser/app)
    - "Get Directions" URL generated from user's detected/entered location to each hospital
    - Live geocoding via Nominatim (OpenStreetMap, no API key required) to convert
      city/place names → GPS coordinates for distance sorting & directions
    - Google Maps Search fallback link for any hospital name
    - Compact, terminal-friendly output with clearly labelled map links

Software Packages Used:
    - anthropic       : Claude AI SDK for conversational AI (pip install anthropic)
    - requests        : HTTP requests for geocoding / Nominatim API (pip install requests)
    - geopy           : Haversine distance calculations (pip install geopy)
    - colorama        : Coloured terminal output (pip install colorama)
    - python-dotenv   : Environment variable management (pip install python-dotenv)

Assumptions:
    1. Internet access is available (required for AI + geocoding).
    2. Geocoding uses Nominatim (OSM) — free, no key needed. Falls back gracefully.
    3. Google Maps links work on any device — clicking opens Google Maps or the browser.
    4. Emergency numbers are sourced from official government sites; keep updated.
    5. ANTHROPIC_API_KEY environment variable must be set for live AI mode.
    6. "Get Directions" links use the hospital's stored GPS coordinates as the destination;
       origin is either the geocoded user location or left blank (Maps will ask the user).

Author: Team RoadSoS
"""

import os
import json
import math
import time
import datetime
import urllib.parse
from typing import Optional
import anthropic
import requests

# ---------------------------------------------------------------------------
# GOOGLE MAPS URL BUILDERS
# ---------------------------------------------------------------------------

def maps_place_link(lat: float, lon: float, name: str) -> str:
    """
    Returns a Google Maps URL that pins the hospital on the map.
    Format: https://www.google.com/maps/search/?api=1&query=<name>&query_place_id=...
    We use the simpler lat,lon pin approach which always works without an API key.
    """
    encoded_name = urllib.parse.quote(name)
    return f"https://www.google.com/maps/search/?api=1&query={encoded_name}+{lat},{lon}"


def maps_directions_link(
    dest_lat: float,
    dest_lon: float,
    dest_name: str,
    origin_lat: Optional[float] = None,
    origin_lon: Optional[float] = None,
) -> str:
    """
    Returns a Google Maps Directions URL.
    If origin coords are provided, generates a full turn-by-turn route link.
    Otherwise, Google Maps will ask the user for their starting point.
    """
    dest = f"{dest_lat},{dest_lon}"
    if origin_lat is not None and origin_lon is not None:
        origin = f"{origin_lat},{origin_lon}"
        return (
            f"https://www.google.com/maps/dir/?api=1"
            f"&origin={urllib.parse.quote(origin)}"
            f"&destination={urllib.parse.quote(dest)}"
            f"&travelmode=driving"
        )
    else:
        return (
            f"https://www.google.com/maps/dir/?api=1"
            f"&destination={urllib.parse.quote(dest)}"
            f"&travelmode=driving"
        )


def maps_search_link(query: str) -> str:
    """Fallback: Google Maps text search link (useful when only name is known)."""
    return f"https://www.google.com/maps/search/{urllib.parse.quote(query)}"


# ---------------------------------------------------------------------------
# GEOCODING  (Nominatim / OpenStreetMap — no API key needed)
# ---------------------------------------------------------------------------

def geocode_location(place: str, country: Optional[str] = None) -> Optional[dict]:
    """
    Convert a place name to lat/lon using Nominatim (free, no API key).
    Returns {"lat": float, "lon": float, "display_name": str} or None.
    """
    query = f"{place}, {country}" if country else place
    url = "https://nominatim.openstreetmap.org/search"
    params = {
        "q": query,
        "format": "json",
        "limit": 1,
        "addressdetails": 0,
    }
    headers = {"User-Agent": "RoadSoS-Hackathon-2026/2.0 (road_emergency_chatbot)"}
    try:
        resp = requests.get(url, params=params, headers=headers, timeout=5)
        resp.raise_for_status()
        results = resp.json()
        if results:
            r = results[0]
            return {
                "lat": float(r["lat"]),
                "lon": float(r["lon"]),
                "display_name": r.get("display_name", query),
            }
    except Exception:
        pass
    return None


# ---------------------------------------------------------------------------
# EMERGENCY DATABASE
# ---------------------------------------------------------------------------

BIMSTEC_EMERGENCY_DATA = {
    "India": {
        "ambulance":       ["108", "112"],
        "police":          ["100", "112"],
        "fire":            ["101"],
        "highway_patrol":  ["1033"],
        "trauma_helpline": ["1800-180-1104"],
        "vehicle_rescue":  ["1800-200-4920"],
        "notes": "National Emergency Number 112 connects police, fire and ambulance.",
    },
    "Bangladesh": {
        "ambulance":       ["999", "199"],
        "police":          ["999"],
        "fire":            ["999", "02-9555555"],
        "highway_patrol":  ["01769-691-100"],
        "trauma_helpline": ["16430"],
        "vehicle_rescue":  ["01811-458899"],
        "notes": "Single emergency number 999 handles all services.",
    },
    "Myanmar": {
        "ambulance":       ["192"],
        "police":          ["199"],
        "fire":            ["191"],
        "highway_patrol":  ["067-3404045"],
        "trauma_helpline": ["067-3404059"],
        "vehicle_rescue":  ["01-243000"],
        "notes": "Dial 192 for ambulance; 199 for police in road emergencies.",
    },
    "Sri Lanka": {
        "ambulance":       ["1990", "110"],
        "police":          ["118", "119"],
        "fire":            ["110"],
        "highway_patrol":  ["1969"],
        "trauma_helpline": ["1926"],
        "vehicle_rescue":  ["0112-323-333"],
        "notes": "Suwaseriya (1990) is Sri Lanka's dedicated ambulance service.",
    },
    "Thailand": {
        "ambulance":       ["1669"],
        "police":          ["191"],
        "fire":            ["199"],
        "highway_patrol":  ["1193"],
        "trauma_helpline": ["1669"],
        "vehicle_rescue":  ["1193"],
        "notes": "Highway Police 1193 handles road accidents on expressways.",
    },
    "Nepal": {
        "ambulance":       ["102"],
        "police":          ["100"],
        "fire":            ["101"],
        "highway_patrol":  ["01-4211159"],
        "trauma_helpline": ["16600-100-100"],
        "vehicle_rescue":  ["01-4211179"],
        "notes": "Traffic Police Headquarters: 01-4211159.",
    },
    "Bhutan": {
        "ambulance":       ["112"],
        "police":          ["113"],
        "fire":            ["110"],
        "highway_patrol":  ["17777377"],
        "trauma_helpline": ["112"],
        "vehicle_rescue":  ["17777377"],
        "notes": "Royal Bhutan Police: 113. RSTA road helpline: 17777377.",
    },
}

# ---------------------------------------------------------------------------
# TRAUMA CENTRE DATABASE  (with GPS + phone)
# ---------------------------------------------------------------------------

TRAUMA_CENTRES = {
    "India": [
        {"name": "AIIMS Trauma Centre",             "city": "New Delhi",  "lat": 28.5672, "lon": 77.2100, "phone": "011-26594404"},
        {"name": "NIMHANS",                          "city": "Bengaluru",  "lat": 12.9438, "lon": 77.5961, "phone": "080-46110007"},
        {"name": "PGIMER",                           "city": "Chandigarh", "lat": 30.7650, "lon": 76.7791, "phone": "0172-2755555"},
        {"name": "Seth GS Medical College",          "city": "Mumbai",     "lat": 18.9984, "lon": 72.8407, "phone": "022-24107000"},
        {"name": "SSKM Hospital",                    "city": "Kolkata",    "lat": 22.5354, "lon": 88.3399, "phone": "033-22041052"},
        {"name": "Govt Medical College Nagpur",      "city": "Nagpur",     "lat": 21.1565, "lon": 79.0843, "phone": "0712-2744391"},
        {"name": "AIIMS Bhopal",                     "city": "Bhopal",     "lat": 23.1732, "lon": 77.3997, "phone": "0755-2672355"},
        {"name": "JIPMER",                           "city": "Puducherry", "lat": 11.9342, "lon": 79.8280, "phone": "0413-2272380"},
        {"name": "Rajiv Gandhi Govt General Hospital","city": "Chennai",   "lat": 13.0826, "lon": 80.2755, "phone": "044-25305000"},
        {"name": "KGMU Trauma Centre",               "city": "Lucknow",    "lat": 26.9124, "lon": 80.9509, "phone": "0522-2258860"},
    ],
    "Bangladesh": [
        {"name": "Dhaka Medical College Hospital",      "city": "Dhaka",      "lat": 23.7236, "lon": 90.3968, "phone": "02-55165001"},
        {"name": "National Institute of Traumatology",  "city": "Dhaka",      "lat": 23.7487, "lon": 90.3882, "phone": "02-58316408"},
        {"name": "Chittagong Medical College Hospital", "city": "Chittagong", "lat": 22.3605, "lon": 91.8116, "phone": "031-619652"},
        {"name": "Rajshahi Medical College Hospital",   "city": "Rajshahi",   "lat": 24.3745, "lon": 88.6042, "phone": "0721-772150"},
    ],
    "Myanmar": [
        {"name": "Yangon General Hospital",   "city": "Yangon",   "lat": 16.8076, "lon": 96.1475, "phone": "01-256112"},
        {"name": "Mandalay General Hospital", "city": "Mandalay", "lat": 21.9746, "lon": 96.0836, "phone": "02-36059"},
        {"name": "Naypyidaw General Hospital","city": "Naypyidaw","lat": 19.7633, "lon": 96.0785, "phone": "067-404050"},
    ],
    "Sri Lanka": [
        {"name": "National Hospital of Sri Lanka", "city": "Colombo", "lat": 6.9271,  "lon": 79.8612, "phone": "011-2691111"},
        {"name": "Kandy Teaching Hospital",        "city": "Kandy",   "lat": 7.2929,  "lon": 80.6355, "phone": "081-2222261"},
        {"name": "Teaching Hospital Karapitiya",   "city": "Galle",   "lat": 6.0329,  "lon": 80.2168, "phone": "091-2234286"},
        {"name": "Jaffna Teaching Hospital",       "city": "Jaffna",  "lat": 9.6615,  "lon": 80.0255, "phone": "021-2222261"},
    ],
    "Thailand": [
        {"name": "Ramathibodi Hospital",  "city": "Bangkok",    "lat": 13.7649, "lon": 100.5295, "phone": "02-2011000"},
        {"name": "Siriraj Hospital",      "city": "Bangkok",    "lat": 13.7590, "lon": 100.4869, "phone": "02-4197000"},
        {"name": "Maharaj Nakorn Hospital","city": "Chiang Mai","lat": 18.7967, "lon": 98.9544,  "phone": "053-945300"},
        {"name": "Songklanagarind Hospital","city": "Hat Yai",  "lat": 7.0067,  "lon": 100.4987, "phone": "074-451000"},
    ],
    "Nepal": [
        {"name": "Bir Hospital",                         "city": "Kathmandu", "lat": 27.7051, "lon": 85.3162, "phone": "01-4221119"},
        {"name": "Tribhuvan University Teaching Hospital","city": "Kathmandu", "lat": 27.7285, "lon": 85.3299, "phone": "01-4412303"},
        {"name": "B.P. Koirala Institute",               "city": "Dharan",    "lat": 26.8065, "lon": 87.2846, "phone": "025-525555"},
        {"name": "Pokhara Academy of Health Sciences",   "city": "Pokhara",   "lat": 28.2096, "lon": 83.9856, "phone": "061-539142"},
    ],
    "Bhutan": [
        {"name": "Jigme Dorji Wangchuck National Referral Hospital", "city": "Thimphu",  "lat": 27.4728, "lon": 89.6394, "phone": "02-322496"},
        {"name": "Mongar Regional Referral Hospital",                 "city": "Mongar",   "lat": 27.2745, "lon": 91.2402, "phone": "04-641120"},
        {"name": "Central Regional Referral Hospital",                "city": "Gelephu",  "lat": 26.8614, "lon": 90.4916, "phone": "06-251130"},
    ],
}

# ---------------------------------------------------------------------------
# UTILITY FUNCTIONS
# ---------------------------------------------------------------------------

def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Return great-circle distance in kilometres."""
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi    = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def enrich_centres_with_maps(
    centres: list[dict],
    user_lat: Optional[float] = None,
    user_lon: Optional[float] = None,
) -> list[dict]:
    """
    Add Google Maps links and (if user coords known) distance + directions URL
    to each trauma centre dict.
    """
    enriched = []
    for c in centres:
        c = dict(c)  # don't mutate original
        lat, lon, name = c["lat"], c["lon"], c["name"]

        # Pin link — opens the hospital on Google Maps
        c["maps_link"] = maps_place_link(lat, lon, name)

        # Directions link — from user's location (or blank origin)
        c["directions_link"] = maps_directions_link(
            lat, lon, name,
            origin_lat=user_lat,
            origin_lon=user_lon,
        )

        # Distance
        if user_lat is not None and user_lon is not None:
            c["distance_km"] = round(haversine_distance(user_lat, user_lon, lat, lon), 1)

        enriched.append(c)

    if user_lat is not None and user_lon is not None:
        enriched.sort(key=lambda x: x.get("distance_km", 9999))

    return enriched


def find_nearest_trauma_centres(
    country: str,
    user_lat: Optional[float] = None,
    user_lon: Optional[float] = None,
    top_n: int = 3,
) -> list[dict]:
    """Return nearest trauma centres with Google Maps links."""
    centres = list(TRAUMA_CENTRES.get(country, []))
    if not centres:
        return []
    enriched = enrich_centres_with_maps(centres, user_lat, user_lon)
    return enriched[:top_n]


def get_emergency_contacts(country: str) -> dict:
    return BIMSTEC_EMERGENCY_DATA.get(country, {})


def geocode_user_location(location_text: str, country: Optional[str] = None) -> Optional[dict]:
    """
    Try to geocode the user's stated location. Adds a small delay to respect
    Nominatim's 1-req/sec policy.
    """
    result = geocode_location(location_text, country)
    time.sleep(1)  # Nominatim rate limit
    return result


def detect_country_from_text(text: str) -> Optional[str]:
    """Keyword scan to detect BIMSTEC country from user message."""
    mapping = {
        "india": "India", "indian": "India", "delhi": "India", "mumbai": "India",
        "bangalore": "India", "bengaluru": "India", "kolkata": "India", "chennai": "India",
        "hyderabad": "India", "pune": "India", "nagpur": "India", "lucknow": "India",
        "bhopal": "India", "nh-": "India", "national highway": "India",
        "bangladesh": "Bangladesh", "dhaka": "Bangladesh", "chittagong": "Bangladesh",
        "rajshahi": "Bangladesh",
        "myanmar": "Myanmar", "burma": "Myanmar", "yangon": "Myanmar", "mandalay": "Myanmar",
        "naypyidaw": "Myanmar",
        "sri lanka": "Sri Lanka", "srilanka": "Sri Lanka", "colombo": "Sri Lanka",
        "kandy": "Sri Lanka", "galle": "Sri Lanka", "jaffna": "Sri Lanka",
        "thailand": "Thailand", "thai": "Thailand", "bangkok": "Thailand",
        "chiang mai": "Thailand", "phuket": "Thailand", "hat yai": "Thailand",
        "nepal": "Nepal", "nepali": "Nepal", "kathmandu": "Nepal",
        "pokhara": "Nepal", "dharan": "Nepal",
        "bhutan": "Bhutan", "bhutanese": "Bhutan", "thimphu": "Bhutan",
        "gelephu": "Bhutan", "mongar": "Bhutan",
    }
    lower = text.lower()
    for kw, country in mapping.items():
        if kw in lower:
            return country
    return None


def extract_location_hint(text: str) -> Optional[str]:
    """
    Try to extract a city / area name from the user's message for geocoding.
    Simple heuristic: looks for 'near X', 'in X', 'at X', 'on X highway'.
    """
    import re
    patterns = [
        r"near\s+([A-Za-z\s\-]+?)(?:,|\.|$|\s+India|\s+Bangladesh|\s+Myanmar|\s+Sri Lanka|\s+Thailand|\s+Nepal|\s+Bhutan)",
        r"in\s+([A-Za-z\s\-]+?)(?:,|\.|$|\s+India|\s+Bangladesh)",
        r"at\s+([A-Za-z\s\-]+?)(?:,|\.|$)",
        r"(?:NH-?\d+|highway)\s+near\s+([A-Za-z\s]+?)(?:,|\.|$)",
    ]
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            loc = m.group(1).strip()
            if len(loc) > 2:
                return loc
    return None


# ---------------------------------------------------------------------------
# SYSTEM PROMPT
# ---------------------------------------------------------------------------

def build_system_prompt() -> str:
    countries = ", ".join(BIMSTEC_EMERGENCY_DATA.keys())
    return f"""You are RoadSoS v2, an AI-powered road emergency assistant for BIMSTEC nations ({countries}).

CRITICAL BEHAVIOUR:
1. In any accident/emergency, IMMEDIATELY call get_emergency_contacts AND find_nearest_trauma_centres.
2. The trauma centre results already contain 'maps_link' (pin on map) and 'directions_link' (turn-by-turn navigation). ALWAYS include these in your reply — format them as:
       🗺  View on Map: <maps_link>
       🧭  Get Directions: <directions_link>
3. If the user gives a specific location (city, highway, landmark), pass those coordinates so the nearest hospitals are sorted by actual distance.
4. Keep emergency responses SHORT and numbered. Seconds matter.
5. Never omit the Google Maps links — they are the key feature of this tool.
6. Remind users: call emergency services FIRST, then use the map links.

Response format for emergencies:
🚨 EMERGENCY – <Country>

CALL NOW:  📞 <top ambulance number>  |  📞 <police>

── NEAREST TRAUMA CENTRES ──
1. 🏥 <Name> (<City>) — 📞 <phone>  [<distance_km> km]
   🗺  Map: <maps_link>
   🧭  Directions: <directions_link>

(repeat for 2, 3)

FIRST AID STEPS:
1. ...

Highway Patrol: 📞 ...  |  Vehicle Rescue: 📞 ...

Today: {datetime.date.today().isoformat()}
"""


# ---------------------------------------------------------------------------
# TOOL DEFINITIONS
# ---------------------------------------------------------------------------

TOOLS = [
    {
        "name": "get_emergency_contacts",
        "description": "Returns official emergency phone numbers for a BIMSTEC country.",
        "input_schema": {
            "type": "object",
            "properties": {
                "country": {"type": "string", "description": "One of: India, Bangladesh, Myanmar, Sri Lanka, Thailand, Nepal, Bhutan"}
            },
            "required": ["country"],
        },
    },
    {
        "name": "find_nearest_trauma_centres",
        "description": (
            "Returns nearest trauma centres with phone numbers AND Google Maps links "
            "(maps_link to view, directions_link for navigation). "
            "Pass user GPS coords if available for distance-sorted results."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "country":  {"type": "string", "description": "BIMSTEC country name"},
                "user_lat": {"type": "number", "description": "User GPS latitude (optional)"},
                "user_lon": {"type": "number", "description": "User GPS longitude (optional)"},
                "top_n":    {"type": "integer", "description": "Number of centres to return (default 3)", "default": 3},
            },
            "required": ["country"],
        },
    },
    {
        "name": "geocode_location",
        "description": (
            "Converts a place name / city / highway location to GPS coordinates (lat, lon). "
            "Use this when the user mentions a specific location so you can pass coords to "
            "find_nearest_trauma_centres for accurate distance sorting."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "place":   {"type": "string", "description": "City, landmark, or address to geocode"},
                "country": {"type": "string", "description": "Country name to narrow the search (optional)"},
            },
            "required": ["place"],
        },
    },
]


# ---------------------------------------------------------------------------
# TOOL EXECUTOR
# ---------------------------------------------------------------------------

def execute_tool(tool_name: str, tool_input: dict) -> str:
    if tool_name == "get_emergency_contacts":
        return json.dumps(get_emergency_contacts(tool_input["country"]), ensure_ascii=False)

    if tool_name == "find_nearest_trauma_centres":
        result = find_nearest_trauma_centres(
            country=tool_input["country"],
            user_lat=tool_input.get("user_lat"),
            user_lon=tool_input.get("user_lon"),
            top_n=tool_input.get("top_n", 3),
        )
        return json.dumps(result, ensure_ascii=False)

    if tool_name == "geocode_location":
        result = geocode_user_location(tool_input["place"], tool_input.get("country"))
        return json.dumps(result, ensure_ascii=False)

    return json.dumps({"error": f"Unknown tool: {tool_name}"})


# ---------------------------------------------------------------------------
# AGENTIC LOOP
# ---------------------------------------------------------------------------

def run_agent(client: anthropic.Anthropic, messages: list, system: str) -> str:
    while True:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1500,
            system=system,
            tools=TOOLS,
            messages=messages,
        )

        tool_calls  = [b for b in response.content if b.type == "tool_use"]
        text_blocks = [b for b in response.content if b.type == "text"]

        if response.stop_reason == "end_turn" or not tool_calls:
            return "\n".join(b.text for b in text_blocks).strip()

        messages.append({"role": "assistant", "content": response.content})

        tool_results = []
        for tc in tool_calls:
            result_text = execute_tool(tc.name, tc.input)
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": tc.id,
                "content": result_text,
            })
        messages.append({"role": "user", "content": tool_results})


# ---------------------------------------------------------------------------
# BANNER
# ---------------------------------------------------------------------------

BANNER = """
╔═══════════════════════════════════════════════════════════════════╗
║        🚨  RoadSoS v2 — Road Emergency AI Assistant  🚨          ║
║   Road Safety Hackathon 2026 | BIMSTEC Countries                  ║
║   🗺  Now with Google Maps links & live directions!               ║
║   Countries: India · Bangladesh · Myanmar · Sri Lanka             ║
║              Thailand · Nepal · Bhutan                            ║
╚═══════════════════════════════════════════════════════════════════╝

Type your emergency or question below. Type 'exit' to quit.
Example: "Accident on NH-44 near Nagpur, India. 2 people injured."
"""


# ---------------------------------------------------------------------------
# CHAT
# ---------------------------------------------------------------------------

def chat():
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("[ERROR] Set ANTHROPIC_API_KEY environment variable.")
        return

    client = anthropic.Anthropic(api_key=api_key)
    system = build_system_prompt()
    messages: list[dict] = []

    print(BANNER)
    print("🤖 RoadSoS: Hello! I'm RoadSoS v2. Report a road accident or ask for "
          "emergency info — I'll provide contacts AND Google Maps links to the nearest "
          "hospitals. Tell me your country and location.\n")

    while True:
        try:
            user_input = input("👤 You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n[Session ended]")
            break

        if not user_input:
            continue
        if user_input.lower() in ("exit", "quit", "bye"):
            print("🤖 RoadSoS: Stay safe. Goodbye!")
            break

        # Build augmented input with auto-detected country
        country_hint = detect_country_from_text(user_input)
        augmented = user_input
        if country_hint:
            augmented += f" [Detected country: {country_hint}]"

        # Try to geocode the user's location for accurate distance sorting
        loc_hint = extract_location_hint(user_input)
        if loc_hint:
            print(f"   📍 Locating '{loc_hint}'...", end="", flush=True)
            geo = geocode_user_location(loc_hint, country_hint)
            if geo:
                augmented += (
                    f" [User GPS approx: lat={geo['lat']:.4f}, lon={geo['lon']:.4f} "
                    f"({geo['display_name'][:60]})]"
                )
                print(f" ✓ ({geo['lat']:.3f}, {geo['lon']:.3f})")
            else:
                print(" (geocoding unavailable, using country-level sort)")

        messages.append({"role": "user", "content": augmented})

        try:
            reply = run_agent(client, messages, system)
        except anthropic.APIError as exc:
            reply = f"[API Error] {exc}"

        messages.append({"role": "assistant", "content": reply})
        print(f"\n🤖 RoadSoS:\n{reply}\n")
        print("─" * 70)


# ---------------------------------------------------------------------------
# DEMO MODE  (no API key — shows richly formatted canned output with map links)
# ---------------------------------------------------------------------------

def demo_mode():
    print(BANNER)
    print("⚠️  [DEMO MODE — No API key. Showing sample output with Google Maps links.]\n")

    scenarios = [
        {
            "user": "Accident on NH-44 near Nagpur, India. 3 injured, one unconscious.",
            "bot": """🚨 EMERGENCY – India

CALL NOW:  📞 112 (National Emergency)  |  📞 108 (Ambulance)

── NEAREST TRAUMA CENTRES TO NAGPUR ──
1. 🏥 Govt Medical College Nagpur (Nagpur) — 📞 0712-2744391  [~1.2 km]
   🗺  Map: https://www.google.com/maps/search/?api=1&query=Govt+Medical+College+Nagpur+21.1565,79.0843
   🧭  Directions: https://www.google.com/maps/dir/?api=1&destination=21.1565,79.0843&travelmode=driving

2. 🏥 AIIMS Bhopal (Bhopal) — 📞 0755-2672355  [~285 km]
   🗺  Map: https://www.google.com/maps/search/?api=1&query=AIIMS+Bhopal+23.1732,77.3997
   🧭  Directions: https://www.google.com/maps/dir/?api=1&destination=23.1732,77.3997&travelmode=driving

3. 🏥 KGMU Trauma Centre (Lucknow) — 📞 0522-2258860  [~508 km]
   🗺  Map: https://www.google.com/maps/search/?api=1&query=KGMU+Trauma+Centre+26.9124,80.9509
   🧭  Directions: https://www.google.com/maps/dir/?api=1&destination=26.9124,80.9509&travelmode=driving

FIRST AID STEPS:
1. Do NOT move injured persons unless fire/flood risk.
2. Keep unconscious person still — check breathing.
3. Press cloth firmly on any bleeding wounds.
4. Switch on hazard lights; place triangles 50 m back.
5. Stay on line with 112 — follow their instructions.

Highway Patrol: 📞 1033  |  Vehicle Rescue: 📞 1800-200-4920""",
        },
        {
            "user": "I'm in Bangkok near Siam, Thailand. Car collision on expressway.",
            "bot": """🚨 EMERGENCY – Thailand

CALL NOW:  📞 1193 (Highway Police & Rescue)  |  📞 1669 (Ambulance EMS)

── NEAREST TRAUMA CENTRES TO SIAM, BANGKOK ──
1. 🏥 Ramathibodi Hospital (Bangkok) — 📞 02-2011000  [~3.5 km]
   🗺  Map: https://www.google.com/maps/search/?api=1&query=Ramathibodi+Hospital+13.7649,100.5295
   🧭  Directions: https://www.google.com/maps/dir/?api=1&origin=13.7455,100.5331&destination=13.7649,100.5295&travelmode=driving

2. 🏥 Siriraj Hospital (Bangkok) — 📞 02-4197000  [~5.1 km]
   🗺  Map: https://www.google.com/maps/search/?api=1&query=Siriraj+Hospital+13.759,100.4869
   🧭  Directions: https://www.google.com/maps/dir/?api=1&origin=13.7455,100.5331&destination=13.759,100.4869&travelmode=driving

FIRST AID STEPS:
1. Move to hard shoulder if vehicle can move.
2. Place warning triangles behind your vehicle.
3. Switch on hazard lights immediately.
4. Do not stand between car and moving traffic.

Police: 📞 191  |  Fire: 📞 199""",
        },
    ]

    for s in scenarios:
        print(f"👤 You: {s['user']}\n")
        print(f"🤖 RoadSoS:\n{s['bot']}\n")
        print("─" * 70 + "\n")

    print("\n💡 TIP: The 🗺 Map links open the hospital pinned on Google Maps.")
    print("         The 🧭 Directions links start turn-by-turn navigation to the hospital.")
    print("         These links work in any browser or the Google Maps mobile app.\n")


# ---------------------------------------------------------------------------
# ENTRY POINT
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    if os.environ.get("ANTHROPIC_API_KEY"):
        chat()
    else:
        demo_mode()
