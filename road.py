# RoadSoS - Improved Hackathon Version (Single File)
# Fix: Handles missing anthropic module gracefully + adds basic tests

import os
import json
import math
import datetime
import copy
from typing import Optional, List, Dict

# Safe import (FIX for your error)
try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

# ================= CONFIG =================
MODEL = "claude-sonnet-4-20250514"
MAX_TOKENS = 800

# ================= DATA =================
BIMSTEC_EMERGENCY_DATA = {
    "India": {"ambulance": ["108", "112"], "police": ["100", "112"], "fire": ["101"]},
    "Bangladesh": {"ambulance": ["999"], "police": ["999"], "fire": ["999"]},
    "Thailand": {"ambulance": ["1669"], "police": ["191"], "fire": ["199"]},
    "Nepal": {"ambulance": ["102"], "police": ["100"], "fire": ["101"]},
}

TRAUMA_CENTRES = {
    "India": [
        {"name": "AIIMS Delhi", "lat": 28.5672, "lon": 77.2100, "phone": "01126594404"},
        {"name": "NIMHANS Bangalore", "lat": 12.9438, "lon": 77.5961, "phone": "08046110007"},
    ]
}

# ================= UTILITIES =================
def haversine(lat1, lon1, lat2, lon2):
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))


def detect_country(text: str) -> Optional[str]:
    text = text.lower()
    if "india" in text or "delhi" in text:
        return "India"
    if "bangkok" in text or "thailand" in text:
        return "Thailand"
    return None

# ================= CORE FUNCTIONS =================
def get_contacts(country: str) -> Dict:
    return BIMSTEC_EMERGENCY_DATA.get(country, {})


def nearest_centres(country: str, lat=None, lon=None) -> List[Dict]:
    centres = copy.deepcopy(TRAUMA_CENTRES.get(country, []))
    if lat is not None and lon is not None:
        for c in centres:
            c["distance"] = round(haversine(lat, lon, c["lat"], c["lon"]), 2)
        centres.sort(key=lambda x: x.get("distance", 999))
    return centres[:3]

# ================= SYSTEM PROMPT =================
def system_prompt():
    return f"""
You are RoadSoS, an emergency assistant.

RULES:
- Always give emergency numbers first
- Keep answers short
- Give step-by-step help
- Ask location and injury severity
- Do NOT give long explanations

Date: {datetime.date.today()}
"""

# ================= FALLBACK =================
def fallback(country: Optional[str]):
    if not country:
        return "⚠️ Unable to detect location. Call local emergency number immediately."

    contacts = get_contacts(country)
    ambulance = contacts.get("ambulance", ["N/A"])[0]

    return (
        f"🚨 EMERGENCY ({country})\n"
        f"📞 Ambulance: {ambulance}\n"
        "1. Stay calm\n"
        "2. Do NOT move injured unless danger\n"
        "3. Apply pressure to bleeding"
    )

# ================= AGENT =================
def run_agent(client, messages, system):
    if not ANTHROPIC_AVAILABLE:
        country = detect_country(messages[-1]["content"])
        return fallback(country)

    try:
        res = client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=system,
            messages=messages
        )
        return res.content[0].text
    except Exception:
        country = detect_country(messages[-1]["content"])
        return fallback(country)

# ================= CHAT =================
def chat():
    api_key = os.getenv("ANTHROPIC_API_KEY")

    if not api_key or not ANTHROPIC_AVAILABLE:
        demo()
        return

    client = anthropic.Anthropic(api_key=api_key)
    system = system_prompt()
    messages = []

    print("\n🚨 RoadSoS Ready (type 'exit')\n")

    while True:
        user = input("You: ")
        if user.lower() in ["exit", "quit"]:
            break

        country = detect_country(user)
        if country:
            user += f" [Country: {country}]"

        messages.append({"role": "user", "content": user})

        reply = run_agent(client, messages, system)

        messages.append({"role": "assistant", "content": reply})
        print("\nBot:", reply, "\n")

# ================= DEMO =================
def demo():
    print("⚠️ DEMO MODE (Anthropic not installed or API key missing)\n")
    print("User: Accident in Delhi\n")
    print("Bot: 🚨 Call 112 or 108 immediately. Apply pressure to bleeding. Do not move injured.\n")

# ================= TESTS =================
def run_tests():
    print("Running basic tests...\n")

    # Test 1: country detection
    assert detect_country("Accident in Delhi") == "India"
    assert detect_country("Crash in Bangkok") == "Thailand"

    # Test 2: contacts
    india = get_contacts("India")
    assert "ambulance" in india

    # Test 3: nearest centres
    centres = nearest_centres("India", 28.5, 77.2)
    assert len(centres) > 0

    print("All tests passed!\n")

# ================= MAIN =================
if __name__ == "__main__":
    run_tests()
    chat()
