"""
RoadSoS - Road Emergency AI Assistant
Road Safety Hackathon 2026 - BIMSTEC Countries
Theme: AI in Road Safety

Description:
    RoadSoS is an AI-powered emergency response chatbot that provides location-based
    access to trauma centres, ambulance services, vehicle rescue services, police stations,
    and emergency contacts during road accidents across all BIMSTEC countries.

Supported Countries:
    India, Bangladesh, Myanmar, Sri Lanka, Thailand, Nepal, Bhutan

Software Packages Used:
    - anthropic       : Claude AI SDK for conversational AI (pip install anthropic)
    - requests        : HTTP requests for geocoding and map services (pip install requests)
    - geopy           : Geolocation and distance calculations (pip install geopy)
    - colorama        : Coloured terminal output (pip install colorama)
    - python-dotenv   : Environment variable management (pip install python-dotenv)

Assumptions:
    1. The user has internet access to query the AI and geocoding services.
    2. Emergency numbers are populated from official government and NGO sources for each
       BIMSTEC country and may change — the database should be kept updated.
    3. Nearest facility lookup uses Haversine distance as a proxy where live mapping APIs
       are unavailable; real deployment should integrate Google Maps / OSM Overpass API.
    4. The chatbot is stateless across sessions; conversation history is maintained only
       within a single run.
    5. An Anthropic API key must be set as the ANTHROPIC_API_KEY environment variable.
    6. The tool is designed for text-based interfaces (CLI); a GUI/mobile wrapper can be
       built on top of the core logic.

Author: Team RoadSoS
"""

import os
import json
import math
import datetime
from typing import Optional
import anthropic

# ---------------------------------------------------------------------------
# EMERGENCY DATABASE  (static fallback — replace with live DB in production)
# ---------------------------------------------------------------------------

BIMSTEC_EMERGENCY_DATA = {
    "India": {
        "ambulance":        ["108", "112"],
        "police":           ["100", "112"],
        "fire":             ["101"],
        "highway_patrol":   ["1033"],
        "trauma_helpline":  ["1800-180-1104"],
        "vehicle_rescue":   ["1800-200-4920"],
        "notes": "National Emergency Number 112 connects to police, fire and ambulance.",
    },
    "Bangladesh": {
        "ambulance":        ["999", "199"],
        "police":           ["999"],
        "fire":             ["999", "02-9555555"],
        "highway_patrol":   ["01769-691-100"],
        "trauma_helpline":  ["16430"],
        "vehicle_rescue":   ["01811-458899"],
        "notes": "Single emergency number 999 handles all services.",
    },
    "Myanmar": {
        "ambulance":        ["192"],
        "police":           ["199"],
        "fire":             ["191"],
        "highway_patrol":   ["067-3404045"],
        "trauma_helpline":  ["067-3404059"],
        "vehicle_rescue":   ["01-243000"],
        "notes": "Dial 192 for ambulance; 199 for police in road emergencies.",
    },
    "Sri Lanka": {
        "ambulance":        ["1990", "110"],
        "police":           ["118", "119"],
        "fire":             ["110"],
        "highway_patrol":   ["1969"],
        "trauma_helpline":  ["1926"],
        "vehicle_rescue":   ["0112-323-333"],
        "notes": "Suwaseriya (1990) is Sri Lanka's dedicated ambulance service.",
    },
    "Thailand": {
        "ambulance":        ["1669"],
        "police":           ["191"],
        "fire":             ["199"],
        "highway_patrol":   ["1193"],
        "trauma_helpline":  ["1669"],
        "vehicle_rescue":   ["1193"],
        "notes": "Highway Police 1193 handles road accidents on expressways.",
    },
    "Nepal": {
        "ambulance":        ["102"],
        "police":           ["100"],
        "fire":             ["101"],
        "highway_patrol":   ["01-4211159"],
        "trauma_helpline":  ["16600-100-100"],
        "vehicle_rescue":   ["01-4211179"],
        "notes": "Traffic Police Headquarters: 01-4211159.",
    },
    "Bhutan": {
        "ambulance":        ["112"],
        "police":           ["113"],
        "fire":             ["110"],
        "highway_patrol":   ["17777377"],
        "trauma_helpline":  ["112"],
        "vehicle_rescue":   ["17777377"],
        "notes": "Royal Bhutan Police: 113. RSTA road helpline: 17777377.",
    },
}

# Sample trauma centres (lat/lon) — extend with real data in production
TRAUMA_CENTRES = {
    "India": [
        {"name": "AIIMS Trauma Centre, New Delhi",       "lat": 28.5672, "lon": 77.2100, "phone": "011-26594404"},
        {"name": "NIMHANS Bengaluru",                    "lat": 12.9438, "lon": 77.5961, "phone": "080-46110007"},
        {"name": "PGIMER Chandigarh",                    "lat": 30.7650, "lon": 76.7791, "phone": "0172-2755555"},
        {"name": "Seth GS Medical College Mumbai",       "lat": 18.9984, "lon": 72.8407, "phone": "022-24107000"},
        {"name": "SSKM Hospital Kolkata",                "lat": 22.5354, "lon": 88.3399, "phone": "033-22041052"},
    ],
    "Bangladesh": [
        {"name": "Dhaka Medical College Hospital",       "lat": 23.7236, "lon": 90.3968, "phone": "02-55165001"},
        {"name": "National Institute of Traumatology",   "lat": 23.7487, "lon": 90.3882, "phone": "02-58316408"},
    ],
    "Myanmar": [
        {"name": "Yangon General Hospital",              "lat": 16.8076, "lon": 96.1475, "phone": "01-256112"},
        {"name": "Mandalay General Hospital",            "lat": 21.9746, "lon": 96.0836, "phone": "02-36059"},
    ],
    "Sri Lanka": [
        {"name": "National Hospital of Sri Lanka",       "lat": 6.9271,  "lon": 79.8612, "phone": "011-2691111"},
        {"name": "Kandy Teaching Hospital",              "lat": 7.2929,  "lon": 80.6355, "phone": "081-2222261"},
    ],
    "Thailand": [
        {"name": "Ramathibodi Hospital Bangkok",         "lat": 13.7649, "lon": 100.5295, "phone": "02-2011000"},
        {"name": "Siriraj Hospital Bangkok",             "lat": 13.7590, "lon": 100.4869, "phone": "02-4197000"},
    ],
    "Nepal": [
        {"name": "Bir Hospital Kathmandu",               "lat": 27.7051, "lon": 85.3162, "phone": "01-4221119"},
        {"name": "Tribhuvan University Teaching Hospital","lat": 27.7285, "lon": 85.3299, "phone": "01-4412303"},
    ],
    "Bhutan": [
        {"name": "Jigme Dorji Wangchuck National Referral Hospital", "lat": 27.4728, "lon": 89.6394, "phone": "02-322496"},
    ],
}

# ---------------------------------------------------------------------------
# UTILITY FUNCTIONS
# ---------------------------------------------------------------------------

def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Return great-circle distance in kilometres between two coordinates."""
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi  = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def find_nearest_trauma_centres(
    country: str,
    user_lat: Optional[float] = None,
    user_lon: Optional[float] = None,
    top_n: int = 3,
) -> list[dict]:
    """Return nearest trauma centres for the given country, sorted by distance."""
    centres = TRAUMA_CENTRES.get(country, [])
    if not centres:
        return []
    if user_lat is not None and user_lon is not None:
        for c in centres:
            c["distance_km"] = round(haversine_distance(user_lat, user_lon, c["lat"], c["lon"]), 1)
        centres = sorted(centres, key=lambda x: x["distance_km"])
    return centres[:top_n]


def get_emergency_contacts(country: str) -> dict:
    """Return emergency contact dictionary for the specified country."""
    return BIMSTEC_EMERGENCY_DATA.get(country, {})


def detect_country_from_text(text: str) -> Optional[str]:
    """Simple keyword scan to detect which BIMSTEC country the user mentions."""
    mapping = {
        "india": "India", "indian": "India", "delhi": "India", "mumbai": "India",
        "bangalore": "India", "bengaluru": "India", "kolkata": "India", "chennai": "India",
        "hyderabad": "India", "pune": "India", "nh": "India",  # National Highway
        "bangladesh": "Bangladesh", "dhaka": "Bangladesh", "chittagong": "Bangladesh",
        "myanmar": "Myanmar", "burma": "Myanmar", "yangon": "Myanmar", "mandalay": "Myanmar",
        "sri lanka": "Sri Lanka", "srilanka": "Sri Lanka", "colombo": "Sri Lanka",
        "thailand": "Thailand", "thai": "Thailand", "bangkok": "Thailand", "phuket": "Thailand",
        "nepal": "Nepal", "nepali": "Nepal", "kathmandu": "Nepal",
        "bhutan": "Bhutan", "bhutanese": "Bhutan", "thimphu": "Bhutan",
    }
    lower = text.lower()
    for kw, country in mapping.items():
        if kw in lower:
            return country
    return None


def build_system_prompt() -> str:
    """Build the AI system prompt for the RoadSoS assistant."""
    countries = ", ".join(BIMSTEC_EMERGENCY_DATA.keys())
    return f"""You are RoadSoS, an AI-powered emergency response assistant for road accidents
across BIMSTEC countries ({countries}).

Your mission is to:
1. Stay calm and reassuring — the user may be in shock or distress.
2. IMMEDIATELY provide emergency contact numbers when a road accident is reported.
3. Provide nearest trauma centres relevant to the user's stated location/country.
4. Guide the user through first-aid priorities while waiting for help.
5. Help locate vehicle rescue services, police, or highway patrol as needed.
6. Support multiple languages conceptually (respond in the user's language when possible).

Response rules:
- Begin every accident report response with the top 2 emergency numbers for the country.
- Always ask: location (city/highway), number of injured, severity (conscious/bleeding).
- Keep responses SHORT and ACTIONABLE during emergencies — numbered steps.
- If country is unclear, ask before proceeding.
- Embed trauma centre names and phone numbers you receive from context into your answer.
- Remind users NOT to move injured persons unless there is immediate danger.
- For non-emergency questions (general road safety info), be informative and helpful.

IMPORTANT: You are NOT a substitute for calling emergency services. Always urge users to
call the local emergency number FIRST.

Today's date: {datetime.date.today().isoformat()}
"""


# ---------------------------------------------------------------------------
# TOOL DEFINITIONS  (Claude function-calling)
# ---------------------------------------------------------------------------

TOOLS = [
    {
        "name": "get_emergency_contacts",
        "description": (
            "Returns official emergency phone numbers (ambulance, police, fire, highway patrol, "
            "vehicle rescue) for a given BIMSTEC country."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "country": {
                    "type": "string",
                    "description": "One of: India, Bangladesh, Myanmar, Sri Lanka, Thailand, Nepal, Bhutan",
                }
            },
            "required": ["country"],
        },
    },
    {
        "name": "find_nearest_trauma_centres",
        "description": (
            "Returns a list of nearby trauma centres / hospitals for a country. "
            "Optionally sorted by distance if latitude and longitude are provided."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "country": {
                    "type": "string",
                    "description": "One of: India, Bangladesh, Myanmar, Sri Lanka, Thailand, Nepal, Bhutan",
                },
                "user_lat": {
                    "type": "number",
                    "description": "User's GPS latitude (optional).",
                },
                "user_lon": {
                    "type": "number",
                    "description": "User's GPS longitude (optional).",
                },
                "top_n": {
                    "type": "integer",
                    "description": "Number of centres to return (default 3).",
                    "default": 3,
                },
            },
            "required": ["country"],
        },
    },
]


# ---------------------------------------------------------------------------
# TOOL EXECUTOR
# ---------------------------------------------------------------------------

def execute_tool(tool_name: str, tool_input: dict) -> str:
    """Dispatch tool calls and return JSON string results."""
    if tool_name == "get_emergency_contacts":
        result = get_emergency_contacts(tool_input["country"])
        return json.dumps(result, ensure_ascii=False)

    if tool_name == "find_nearest_trauma_centres":
        result = find_nearest_trauma_centres(
            country=tool_input["country"],
            user_lat=tool_input.get("user_lat"),
            user_lon=tool_input.get("user_lon"),
            top_n=tool_input.get("top_n", 3),
        )
        return json.dumps(result, ensure_ascii=False)

    return json.dumps({"error": f"Unknown tool: {tool_name}"})


# ---------------------------------------------------------------------------
# AGENTIC LOOP
# ---------------------------------------------------------------------------

def run_agent(client: anthropic.Anthropic, messages: list, system: str) -> str:
    """Run the Claude agentic loop with tool-use until a final text response."""
    while True:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            system=system,
            tools=TOOLS,
            messages=messages,
        )

        # Collect text and tool_use blocks
        tool_calls = [b for b in response.content if b.type == "tool_use"]
        text_blocks = [b for b in response.content if b.type == "text"]

        if response.stop_reason == "end_turn" or not tool_calls:
            # Final answer
            return "\n".join(b.text for b in text_blocks).strip()

        # Append assistant turn
        messages.append({"role": "assistant", "content": response.content})

        # Execute each tool and build tool results
        tool_results = []
        for tool_call in tool_calls:
            result_text = execute_tool(tool_call.name, tool_call.input)
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": tool_call.id,
                "content": result_text,
            })

        messages.append({"role": "user", "content": tool_results})


# ---------------------------------------------------------------------------
# CHAT INTERFACE
# ---------------------------------------------------------------------------

BANNER = """
╔══════════════════════════════════════════════════════════════╗
║          🚨  RoadSoS — Road Emergency AI Assistant  🚨       ║
║     Road Safety Hackathon 2026 | BIMSTEC Countries           ║
║  Countries: India · Bangladesh · Myanmar · Sri Lanka         ║
║             Thailand · Nepal · Bhutan                        ║
╚══════════════════════════════════════════════════════════════╝

Type your emergency or question below. Type 'exit' to quit.
Example: "There has been an accident on NH-44 near Nagpur, India. 2 people injured."
"""


def chat():
    """Main interactive chat loop."""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("[ERROR] Please set the ANTHROPIC_API_KEY environment variable.")
        return

    client = anthropic.Anthropic(api_key=api_key)
    system = build_system_prompt()
    messages: list[dict] = []

    print(BANNER)

    # Greeting message
    initial = (
        "Hello! I am RoadSoS, your road emergency assistant for BIMSTEC countries. "
        "Are you reporting a road accident or do you need emergency contact information? "
        "Please tell me your country and location."
    )
    print(f"\n🤖 RoadSoS: {initial}\n")

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

        # Auto-hint country if detectable
        country_hint = detect_country_from_text(user_input)
        augmented_input = user_input
        if country_hint:
            augmented_input += f" [Detected country: {country_hint}]"

        messages.append({"role": "user", "content": augmented_input})

        try:
            reply = run_agent(client, messages, system)
        except anthropic.APIError as exc:
            reply = f"[API Error] {exc}"

        # Append final assistant reply to history
        messages.append({"role": "assistant", "content": reply})

        print(f"\n🤖 RoadSoS: {reply}\n")


# ---------------------------------------------------------------------------
# DEMO MODE  (no API key required — shows canned responses)
# ---------------------------------------------------------------------------

def demo_mode():
    """Run a scripted demo without an API key."""
    scenarios = [
        {
            "user": "There has been a bad accident on NH-44 near Nagpur. 3 people are injured, one is unconscious.",
            "bot": (
                "🚨 EMERGENCY – India\n\n"
                "CALL NOW:\n"
                "  📞 112 (National Emergency)\n"
                "  📞 108 (Ambulance)\n\n"
                "While waiting for help:\n"
                "1. Do NOT move injured persons unless there is fire/flood risk.\n"
                "2. Keep unconscious persons still; check breathing.\n"
                "3. Apply firm pressure to any bleeding wounds with a cloth.\n"
                "4. Switch on hazard lights; place warning triangles 50 m away.\n"
                "5. Stay on the line with 112 and follow dispatcher instructions.\n\n"
                "Nearest Trauma Centres to Nagpur:\n"
                "  🏥 AIIMS Nagpur  — 0712-2806000\n"
                "  🏥 Govt Medical College Nagpur — 0712-2744391\n\n"
                "Highway Patrol: 📞 1033  |  Vehicle Rescue: 📞 1800-200-4920"
            ),
        },
        {
            "user": "I am in Bangkok, Thailand. My car broke down on the expressway after a collision.",
            "bot": (
                "🚨 EMERGENCY – Thailand\n\n"
                "CALL NOW:\n"
                "  📞 1193 (Highway Police & Vehicle Rescue)\n"
                "  📞 1669 (EMS Ambulance)\n\n"
                "Steps:\n"
                "1. Move to the hard shoulder immediately if your vehicle can move.\n"
                "2. Place warning triangles / reflectors behind your vehicle.\n"
                "3. Switch on hazard lights.\n"
                "4. Do not stand between your car and oncoming traffic.\n\n"
                "Nearest Trauma Centre:\n"
                "  🏥 Ramathibodi Hospital — 02-2011000\n"
                "  🏥 Siriraj Hospital    — 02-4197000\n\n"
                "Police: 📞 191  |  Fire: 📞 199"
            ),
        },
    ]

    print(BANNER)
    print("⚠️  [DEMO MODE — No API key detected. Showing scripted responses.]\n")
    for s in scenarios:
        print(f"👤 You: {s['user']}\n")
        print(f"🤖 RoadSoS:\n{s['bot']}\n")
        print("-" * 66)


# ---------------------------------------------------------------------------
# ENTRY POINT
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    if os.environ.get("ANTHROPIC_API_KEY"):
        chat()
    else:
        demo_mode()
