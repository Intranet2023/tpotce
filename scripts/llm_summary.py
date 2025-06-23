import os
import requests
import geoip2.database
from flask import Flask, Response

MAP_DATA_URL = os.getenv("MAP_DATA_URL", "http://map_data:64299")
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "ollama")
LLM_SERVER_URL = os.getenv("LLM_SERVER_URL", "http://ollama:11434")
LLM_MODEL = os.getenv("LLM_MODEL", "llama3")
LLM_API_KEY = os.getenv("LLM_API_KEY")
GEOIP_DB_PATH = os.getenv("GEOIP_DB_PATH", "/usr/share/GeoIP/GeoLite2-City.mmdb")
EVENT_LIMIT = int(os.getenv("EVENT_LIMIT", "20"))
PORT = int(os.getenv("PORT", "8000"))

app = Flask(__name__)


def fetch_events():
    try:
        r = requests.get(f"{MAP_DATA_URL}/events?limit={EVENT_LIMIT}", timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception:
        return []


def geolocate(ip, reader):
    try:
        response = reader.city(ip)
        city = response.city.name or ""
        country = response.country.iso_code or ""
        return ", ".join(filter(None, [city, country]))
    except Exception:
        return "unknown"


def build_prompt(events):
    lines = []
    for e in events:
        ip = e.get("src_ip") or e.get("ip")
        geo = e.get("geo", "")
        attack = e.get("attack") or e.get("type")
        lines.append(f"{ip} ({geo}) - {attack}")
    joined = "\n".join(lines)
    return (
        "Summarize the following honeypot events in two short paragraphs:\n" + joined
    )


def query_llm(prompt):
    if LLM_PROVIDER.lower() == "ollama":
        payload = {"model": LLM_MODEL, "prompt": prompt}
        r = requests.post(f"{LLM_SERVER_URL}/api/generate", json=payload, timeout=30)
        return r.json().get("response", "")
    else:
        headers = {"Authorization": f"Bearer {LLM_API_KEY}"}
        data = {
            "model": LLM_MODEL,
            "messages": [{"role": "user", "content": prompt}],
        }
        r = requests.post(
            f"{LLM_SERVER_URL}/v1/chat/completions",
            headers=headers,
            json=data,
            timeout=30,
        )
        return r.json()["choices"][0]["message"]["content"]


@app.route("/summary")
def summary():
    events = fetch_events()
    reader = geoip2.database.Reader(GEOIP_DB_PATH)
    for e in events:
        ip = e.get("src_ip") or e.get("ip")
        e["geo"] = geolocate(ip, reader)
    prompt = build_prompt(events)
    result = query_llm(prompt)
    return Response(result, mimetype="text/plain")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT)

