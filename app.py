import streamlit as st
import streamlit.components.v1 as components
import plotly.graph_objects as go
import requests
import datetime
import time
import pandas as pd
from collections import defaultdict
import concurrent.futures # To fetch city data concurrently
import math


# -----------------------------------------------------------------------------
# Page Configuration
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Air 13X - Air Quality Analyzer",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# -----------------------------------------------------------------------------
# AQI & Health Recommendations Configuration
# -----------------------------------------------------------------------------
# ... (AQI_CATEGORIES, HEALTH_RECOMMENDATIONS, get_aqi_category unchanged) ...
AQI_CATEGORIES = {
    (0, 50): {"label": "Good", "color": "#5EC445"}, (51, 100): {"label": "Moderate", "color": "#F5E769"},
    (101, 150): {"label": "Unhealthy for Sensitive Groups", "color": "#FE9B57"}, (151, 200): {"label": "Unhealthy", "color": "#FE6A69"},
    (201, 300): {"label": "Very Unhealthy", "color": "#A97ABC"}, (301, 500): {"label": "Hazardous", "color": "#A06A7B"}
}
HEALTH_RECOMMENDATIONS = {
    "Good": {"short": "Air quality is satisfactory.", "details": "It's a great day to be active outside."},
    "Moderate": {"short": "Acceptable air quality.", "details": "Unusually sensitive individuals: Consider reducing prolonged or heavy exertion outdoors."},
    "Unhealthy for Sensitive Groups": {"short": "Sensitive groups may experience health effects.", "details": "**Sensitive groups (heart/lung disease, older adults, children):** Reduce prolonged/heavy exertion outdoors. Take more breaks.\n\n**General public:** Okay outside, watch for symptoms."},
    "Unhealthy": {"short": "Some may experience health effects; sensitive groups more serious effects.", "details": "**Sensitive groups:** Avoid prolonged/heavy exertion outdoors. Move activities indoors or reschedule.\n\n**General public:** Reduce prolonged/heavy exertion outdoors."},
    "Very Unhealthy": {"short": "Health alert: Increased risk for everyone.", "details": "**Sensitive groups:** Avoid all physical activity outdoors. Move activities indoors.\n\n**General public:** Avoid prolonged/heavy exertion. Consider moving activities indoors."},
    "Hazardous": {"short": "Health warning: Emergency conditions.", "details": "**Everyone:** Avoid all physical activity outdoors.\n\n**Sensitive groups:** Remain indoors, keep activity low."},
    "Unknown": {"short": "AQI category could not be determined.", "details": "Health recommendations unavailable."}
}
def get_aqi_category(aqi):
    if aqi is None: return "Unknown", "#808080"
    try: aqi = int(aqi)
    except (ValueError, TypeError): return "Unknown", "#808080"
    for (lower, upper), category in AQI_CATEGORIES.items():
        if lower <= aqi <= upper: return category["label"], category["color"]
    if aqi > 500: return AQI_CATEGORIES[(301, 500)]["label"], AQI_CATEGORIES[(301, 500)]["color"]
    return "Unknown", "#808080"

OWM_AQI_MAP = {1: "Good (1)", 2: "Fair (2)", 3: "Moderate (3)", 4: "Poor (4)", 5: "Very Poor (5)"}
def get_owm_aqi_forecast_category(aqi_value): return OWM_AQI_MAP.get(aqi_value, "Unknown") # (Unchanged)

# -----------------------------------------------------------------------------
# Configuration for Ranking Feature
# -----------------------------------------------------------------------------
# ... (CITIES_FOR_RANKING unchanged) ...
CITIES_FOR_RANKING = [
    "@1437", "@3362", "@990", "lahore", "karachi", "kolkata", "mumbai",
    "kathmandu", "hanoi", "jakarta/central", "bangkok", "shanghai", "wuhan",
    "london", "paris", "los angeles", "new york", "mexico city", "sao paulo", "lima"
]

# -----------------------------------------------------------------------------
# Initialize Session State Variables
# -----------------------------------------------------------------------------
# ... (default_states unchanged) ...
default_states = {
    'iqair_api_key': "", 'openweathermap_api_key': "", 'waqi_api_key': "",
    'mapbox_token': "", 'country': "", 'state_region': "", 'city': "",
    'view_data_clicked': False, 'weather_data': None, 'weather_error': None,
    'aqi_data': None, 'aqi_error': None, 'coordinates': None, 'coordinates_error': None,
    'history_data': None, 'history_error': None, 'forecast_data': None, 'forecast_error': None,
    'nearby_data': None, 'nearby_error': None, 'map_data': None, 'map_error': None,
    'ranking_data': None, 'ranking_error': None
}
for key, default_value in default_states.items():
    if key not in st.session_state: st.session_state[key] = default_value

# -----------------------------------------------------------------------------
# Styling
# -----------------------------------------------------------------------------
# ... (Full CSS block - unchanged) ...
dashboard_bg = "#030412"; sidebar_bg = "#030524"; card_bg = "#21263F"
primary_button_color = "#9D0E53"; text_color = "#FFFFFF"; hint_text_color = "#C7C7C7"
secondary_text_color = "#8AAEFB"; HISTORY_LINE_COLOR = "#1f77b4"; HISTORY_MARKER_COLOR = "#ff7f0e"
PLOTLY_TEMPLATE = "plotly_dark"
st.markdown(f"""<style>
    .stApp {{ background-color: {dashboard_bg}; color: {text_color}; }}
    [data-testid="stSidebar"] > div:first-child {{ background-color: {sidebar_bg}; }}
    .stTextInput input, .stTextArea textarea {{ color: {text_color}; background-color: #2b304a; }}
    ::placeholder {{ color: {hint_text_color} !important; opacity: 1 !important; }} :-ms-input-placeholder {{ color: {hint_text_color} !important; }} ::-ms-input-placeholder {{ color: {hint_text_color} !important; }}
    .st-expanderHeader {{ color: {secondary_text_color}; font-weight: bold; }} .st-expander {{ background-color: #132660; border: none !important; border-radius: 10px; margin-bottom: 10px; }} .st-expander p {{ color: {text_color}; }}
    div.stButton > button:first-child {{ background-color: {primary_button_color}; color: {text_color}; border-radius: 5px; padding: 0.5rem 1rem; border: none; width: 100%; font-weight: bold; }} div.stButton > button:hover {{ background-color: #bf1169; color: {text_color}; }}
    .header-text {{ color: {text_color}; font-size: 24px; font-weight: bold; margin-bottom: 0; }} .header-subtext {{ color: {secondary_text_color}; font-size: 12px; margin-top: 0; }}
    h3 {{ color: {secondary_text_color}; font-weight: bold; }} .data-container {{ background-color: {card_bg}; padding: 15px; border-radius: 10px; margin-bottom: 15px; border: 1px solid #3a3f5a; min-height: 150px; }}
    .footer {{ position: fixed; left: 0; bottom: 0; width: 100%; background-color: {sidebar_bg}; color: {secondary_text_color}; text-align: center; padding: 5px; font-size: 12px; z-index: 100; }} .main .block-container {{ padding-bottom: 60px; }}
    .plotly-gauge .gauge-value {{ fill: {text_color} !important; font-size: 28px !important; font-weight: bold; }} .plotly-gauge .title-text {{ fill: {text_color} !important; }}
    .recommendation-category {{ font-weight: bold; padding: 5px 10px; border-radius: 5px; display: inline-block; margin-bottom: 10px; }} .recommendation-details {{ font-size: 0.95rem; line-height: 1.4; }}
    .plotly .yaxislayer-above .ytick text {{ fill: {text_color} !important; }}
     .mapboxgl-ctrl-attrib a {{ color: {hint_text_color} !important; }}
     .plotly .mapboxgl-marker svg g circle {{ stroke: #FFFFFF !important; }}
     .analytical-note {{ font-size: 0.9rem; color: {hint_text_color}; padding-top: 10px; border-top: 1px dashed #444; margin-top: 15px; }}
</style>""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# Header (remains the same)
# -----------------------------------------------------------------------------
# ... (Header markdown unchanged) ...
st.markdown('<h1 style="text-align:center; color:white; font-weight:bold; font-size:40px;">AIR 13X</h1>', unsafe_allow_html=True)
st.markdown('<p class="header-subtext" style="text-align:center; color:#FFFFFF;">AIR means Air. 13 means SDG 3, 11, 13; these three represent air pollution, and X is the app\'s version.</p>', unsafe_allow_html=True)
st.markdown("---")

# ElevenLabs Conversation Widget at the top right
#elevenlabs_embed_code = """
#<div style="position: Centered; top: 50px; right: 80px; z-index: 100;">
#    <elevenlabs-convai agent-id="rHhQqxWxk4pue21ttj6s"></elevenlabs-convai>
#    <script src="https://elevenlabs.io/convai-widget/index.js" async type="text/javascript"></script>
#</div>
#"""

#components.html(elevenlabs_embed_code, height=150) # Adjust height as needed

# -----------------------------------------------------------------------------
# API Call Functions --- REVERTED History to OWM ---
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# API Call Functions --- ADD THESE NEW FUNCTIONS ---
# -----------------------------------------------------------------------------

@st.cache_data(ttl=86400) # Cache for 1 day
def get_iqair_countries(api_key):
    """Fetches a list of supported countries from IQAir."""
    if not api_key:
        return [], "IQAir API Key missing."
    base_url = "http://api.airvisual.com/v2/countries"
    params = {"key": api_key}
    try:
        response = requests.get(base_url, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()
        if data.get("status") == "success":
            countries = [item["country"] for item in data.get("data", [])]
            return sorted(countries), None # Return sorted list of country names
        else:
            return [], f"IQAir Error (Countries): {data.get('data', {}).get('message', 'Unknown')}"
    except requests.exceptions.HTTPError as http_err:
        if response.status_code == 401: return [], "IQAir Error (Countries): Invalid API Key."
        if response.status_code == 400: # Often indicates key issues too
             try: error_msg = response.json().get("data", {}).get("message", str(http_err))
             except: error_msg = str(http_err)
             return [], f"IQAir Error (Countries): {error_msg}"
        else: return [], f"IQAir Error (Countries): HTTP Error {response.status_code} - {http_err}"
    except requests.exceptions.RequestException as err:
        return [], f"IQAir Error (Countries): Request failed - {err}"
    except Exception as e:
        return [], f"IQAir Error (Countries): Unexpected error - {e}"

@st.cache_data(ttl=3600) # Cache for 1 hour
def get_iqair_states(api_key, country):
    """Fetches a list of supported states for a given country from IQAir."""
    if not api_key: return [], "IQAir API Key missing."
    if not country: return [], "Country not selected."
    base_url = "http://api.airvisual.com/v2/states"
    params = {"country": country, "key": api_key}
    try:
        response = requests.get(base_url, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()
        if data.get("status") == "success":
            states = [item["state"] for item in data.get("data", [])]
            return sorted(states), None
        else:
            # Check for specific no_states_found error
            if data.get("data", {}).get("message") == "no_states_found":
                 return [], None # Return empty list, not an error
            else:
                 return [], f"IQAir Error (States): {data.get('data', {}).get('message', 'Unknown')}"
    except requests.exceptions.HTTPError as http_err:
        if response.status_code == 401: return [], "IQAir Error (States): Invalid API Key."
        if response.status_code == 400: # Often indicates key/param issues
             try: error_msg = response.json().get("data", {}).get("message", str(http_err))
             except: error_msg = str(http_err)
             return [], f"IQAir Error (States): {error_msg}"
        else: return [], f"IQAir Error (States): HTTP Error {response.status_code} - {http_err}"
    except requests.exceptions.RequestException as err:
        return [], f"IQAir Error (States): Request failed - {err}"
    except Exception as e:
        return [], f"IQAir Error (States): Unexpected error - {e}"

@st.cache_data(ttl=3600) # Cache for 1 hour
def get_iqair_cities(api_key, country, state):
    """Fetches a list of supported cities for a given country and state from IQAir."""
    if not api_key: return [], "IQAir API Key missing."
    if not country: return [], "Country not selected."
    if not state: return [], "State/Region not selected."
    base_url = "http://api.airvisual.com/v2/cities"
    params = {"state": state, "country": country, "key": api_key}
    try:
        response = requests.get(base_url, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()
        if data.get("status") == "success":
            cities = [item["city"] for item in data.get("data", [])]
            return sorted(cities), None
        else:
            # Check for specific no_cities_found error
            if data.get("data", {}).get("message") == "no_cities_found":
                 return [], None # Return empty list, not an error
            else:
                 return [], f"IQAir Error (Cities): {data.get('data', {}).get('message', 'Unknown')}"
    except requests.exceptions.HTTPError as http_err:
        if response.status_code == 401: return [], "IQAir Error (Cities): Invalid API Key."
        if response.status_code == 400: # Often indicates key/param issues
             try: error_msg = response.json().get("data", {}).get("message", str(http_err))
             except: error_msg = str(http_err)
             return [], f"IQAir Error (Cities): {error_msg}"
        else: return [], f"IQAir Error (Cities): HTTP Error {response.status_code} - {http_err}"
    except requests.exceptions.RequestException as err:
        return [], f"IQAir Error (Cities): Request failed - {err}"
    except Exception as e:
        return [], f"IQAir Error (Cities): Unexpected error - {e}"

# --- Place these functions near your existing API functions like get_iqair_aqi ---
# ... rest of your API functions ...

# --- OWM History Function --- RE-ADDED ---
# @st.cache_data(ttl=1800) # Example Caching (30 mins)
def get_owm_history(api_key, lat, lon, days=7):
    """Fetches air pollution history (PM2.5) for the last 'days' from OWM."""
    if lat is None or lon is None: return None, "History Error: Invalid coordinates."

    base_url = "http://api.openweathermap.org/data/2.5/air_pollution/history"
    end_time = int(time.time()) # Now (Unix timestamp)
    start_time = end_time - (days * 24 * 60 * 60) # 'days' ago

    params = {"lat": lat, "lon": lon, "start": start_time, "end": end_time, "appid": api_key}
    try:
        response = requests.get(base_url, params=params, timeout=20)
        response.raise_for_status()
        data = response.json()

        if "list" in data: # OWM returns 'list' even if empty
            history = []
            for entry in data["list"]:
                # Ensure we have both timestamp and pm2.5
                dt_unix = entry.get("dt")
                pm25_value = entry.get("components", {}).get("pm2_5")
                if dt_unix is not None and pm25_value is not None:
                     dt_object = datetime.datetime.fromtimestamp(dt_unix, tz=datetime.timezone.utc)
                     history.append({"timestamp": dt_object, "pm25": pm25_value})

            return sorted(history, key=lambda x: x["timestamp"]), None # Sort just in case
        else:
            # This case is unlikely if the API call itself succeeded
            return [], "History Error: Unexpected response format from OWM (missing 'list')."

    except requests.exceptions.HTTPError as http_err:
        if response.status_code == 401: return None, "History Error: Invalid OWM API Key."
        else: return None, f"History Error: OWM HTTP Error {response.status_code} - {http_err}"
    except requests.exceptions.RequestException as err:
        return None, f"History Error: Request failed - {err}"
    except Exception as e:
        return None, f"History Error: Unexpected error processing OWM history - {e}"

# --- REMOVED get_openaq_history function ---

# --- Other Existing API Functions (Unchanged) ---
# ... (get_waqi_feed, get_waqi_map_stations, get_coordinates, _fetch_owm_coords, ...) ...
# ... (get_iqair_aqi, get_openweathermap_weather, get_owm_5day_weather_forecast, ...) ...
# ... (get_owm_aqi_forecast, get_waqi_nearby_stations unchanged) ...
def get_waqi_feed(api_key, city_identifier): # (Unchanged)
    if not api_key: return None, f"Ranking Error ({city_identifier}): WAQI API Key missing."
    encoded_city = requests.utils.quote(city_identifier); base_url = f"https://api.waqi.info/feed/{encoded_city}/"; params = {"token": api_key}
    try:
        response = requests.get(base_url, params=params, timeout=10); data = response.json()
        if data.get("status") == "ok":
            aqi_data = data.get("data", {}).get("aqi"); station_name = data.get("data", {}).get("city", {}).get("name", city_identifier)
            valid_aqi = None
            if aqi_data is not None:
                try: aqi_float = float(aqi_data); valid_aqi = int(aqi_float)
                except (ValueError, TypeError): valid_aqi = None
            if valid_aqi is not None: return {"name": station_name, "aqi": valid_aqi}, None
            else: return None, None # Skip silently if no valid AQI
        elif data.get("status") == "error":
             error_message = data.get("data", "Unknown WAQI error.")
             if error_message == "Unknown station": return None, None
             elif error_message == "Invalid key": return None, f"Ranking Error ({city_identifier}): Invalid WAQI API Key."
             else: return None, f"Ranking Error ({city_identifier}): WAQI API - {error_message}"
        else: return None, None # Skip silently on other statuses like 'nope'
    except requests.exceptions.RequestException as err: return None, f"Ranking Error ({city_identifier}): Request failed - {err}"
    except Exception as e: return None, f"Ranking Error ({city_identifier}): Unexpected error - {e}"

def get_waqi_map_stations(api_key, lat1=-90, lon1=-180, lat2=90, lon2=180): # (Unchanged)
    if not api_key: return None, "Map Error: WAQI API Key missing."
    bounds = f"{lat1:.4f},{lon1:.4f},{lat2:.4f},{lon2:.4f}"; base_url = f"https://api.waqi.info/map/bounds/"; params = {"latlng": bounds, "token": api_key, "networks": "all"}
    try:
        response = requests.get(base_url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        if data.get("status") == "ok":
            stations = data.get("data", [])
            processed_stations = []
            for station in stations:
                aqi_str = station.get("aqi")
                if aqi_str and aqi_str != "-":
                    try:
                        aqi_val = int(aqi_str)
                        lat = station.get("lat")
                        lon = station.get("lon")
                        if lat is not None and lon is not None: processed_stations.append({"name": station.get("station", {}).get("name", "Unknown"), "aqi": aqi_val, "lat": lat, "lon": lon})
                    except (ValueError, TypeError): continue
            return processed_stations, None
        else: error_message = data.get("data", "Unknown WAQI error."); return None, f"Map Error: WAQI API - {error_message}"
    except requests.exceptions.RequestException as err: return None, f"Map Error: Request failed - {err}"
    except Exception as e: return None, f"Map Error: Unexpected error - {e}"

def get_coordinates(api_key, city, state="", country=""): # (Unchanged)
    coords, error = None, None; location_query_full = f"{city},{state},{country}".strip(',')
    coords, error = _fetch_owm_coords(api_key, location_query_full)
    if coords is None and error and "Invalid API key" not in error:
        location_query_simple = f"{city},{country}".strip(',')
        if location_query_simple != location_query_full:
            # st.info(f"Retrying geocoding with simplified query: {location_query_simple}") # Optional info
            coords, error = _fetch_owm_coords(api_key, location_query_simple)
    return coords, error

def _fetch_owm_coords(api_key, location_query): # (Unchanged)
    base_url = "http://api.openweathermap.org/geo/1.0/direct"; params = {"q": location_query, "limit": 1, "appid": api_key}
    try:
        response = requests.get(base_url, params=params, timeout=10); response.raise_for_status(); data = response.json()
        if data and isinstance(data, list):
            coords = {"lat": data[0].get("lat"), "lon": data[0].get("lon"), "name": data[0].get("name"), "country": data[0].get("country")}
            if coords["lat"] is not None and coords["lon"] is not None: return coords, None
            else: return None, f"Geocoding failed: Lat/Lon not found for '{location_query}'."
        else: return None, f"Geocoding failed: Location '{location_query}' not found."
    except requests.exceptions.HTTPError as http_err:
         if response.status_code == 401: return None, "Geocoding Error: Invalid OWM API Key."
         else: return None, f"Geocoding Error: HTTP Error for '{location_query}' - {http_err}"
    except requests.exceptions.RequestException as err: return None, f"Geocoding Error: Request failed for '{location_query}' - {err}"
    except Exception as e: return None, f"Geocoding Error: Unexpected error for '{location_query}' - {e}"

def get_iqair_aqi(api_key, city, state, country): # (Unchanged)
    base_url = "http://api.airvisual.com/v2/city"; params = {"city": city, "state": state, "country": country, "key": api_key}
    try:
        response = requests.get(base_url, params=params, timeout=15); response.raise_for_status(); data = response.json()
        if data.get("status") == "success":
            current_data = data.get("data", {}).get("current", {}); pollution_data = current_data.get("pollution", {})
            aqi_details = {"aqi_us": pollution_data.get("aqius"), "main_pollutant_us": pollution_data.get("mainus"), "pollutant_ts": pollution_data.get("ts")}
            return aqi_details, None
        else: return None, f"IQAir API Error: {data.get('data', {}).get('message', 'Unknown')}"
    except requests.exceptions.RequestException as err: return None, f"IQAir API Error: Request failed - {err}"
    except Exception as e: return None, f"An error occurred processing IQAir data: {e}"

def get_openweathermap_weather(api_key, city, state="", country=""): # (Unchanged)
    location_query = f"{city},{country}"; base_url = "http://api.openweathermap.org/data/2.5/weather?"
    complete_url = f"{base_url}appid={api_key}&q={location_query}&units=metric"
    try:
        response = requests.get(complete_url, timeout=15); response.raise_for_status(); data = response.json()
        if data.get("cod") != 200: return None, f"OWM API Error: {data.get('message', 'Unknown')} (Code: {data.get('cod')})"
        main_data = data.get("main", {}); weather_info = data.get("weather", [{}])[0]; wind_data = data.get("wind", {})
        weather_details = {"temperature": main_data.get("temp"), "feels_like": main_data.get("feels_like"), "humidity": main_data.get("humidity"), "pressure": main_data.get("pressure"), "description": weather_info.get("description", "N/A").capitalize(), "icon": weather_info.get("icon"), "wind_speed": wind_data.get("speed"), "city_name": data.get("name"), "country": data.get("sys", {}).get("country"), "timestamp": data.get("dt")}
        return weather_details, None
    except requests.exceptions.RequestException as err: return None, f"OWM API Error: Request failed - {err}"
    except Exception as e: return None, f"An error occurred processing weather data: {e}"

def get_owm_5day_weather_forecast(api_key, lat, lon): # (Unchanged)
    if lat is None or lon is None: return None, "Forecast Error: Invalid coordinates."
    base_url = "http://api.openweathermap.org/data/2.5/forecast"; params = {"lat": lat, "lon": lon, "appid": api_key, "units": "metric"}
    try:
        response = requests.get(base_url, params=params, timeout=15); response.raise_for_status(); data = response.json()
        daily_summaries = defaultdict(lambda: {"min_temp": float('inf'), "max_temp": float('-inf'), "conditions": [], "icons": []})
        if "list" not in data: return None, "Weather Forecast Error: Unexpected API response format."
        for item in data["list"]: # Process 3-hourly data...
             dt_object = datetime.datetime.fromtimestamp(item.get("dt"), tz=datetime.timezone.utc); date_key = dt_object.date(); temp = item.get("main", {}).get("temp")
             weather_info = item.get("weather", [{}])[0]; description = weather_info.get("description"); icon = weather_info.get("icon"); hour = dt_object.hour
             if temp is not None: daily_summaries[date_key]["min_temp"] = min(daily_summaries[date_key]["min_temp"], temp); daily_summaries[date_key]["max_temp"] = max(daily_summaries[date_key]["max_temp"], temp)
             if description: daily_summaries[date_key]["conditions"].append(description)
             if icon:
                  if hour >= 11 and hour <= 14: daily_summaries[date_key]["icons"].insert(0, icon)
                  else: daily_summaries[date_key]["icons"].append(icon)
        processed_forecast = [] # Finalize summaries...
        for date_key in sorted(daily_summaries.keys()):
             summary = daily_summaries[date_key]
             most_common_condition = max(set(summary["conditions"]), key=summary["conditions"].count) if summary["conditions"] else "N/A"; chosen_icon = summary["icons"][0] if summary["icons"] else None
             processed_forecast.append({"date": date_key, "max_temp": summary["max_temp"] if summary["max_temp"] != float('-inf') else None, "min_temp": summary["min_temp"] if summary["min_temp"] != float('inf') else None, "description": most_common_condition.capitalize(), "icon": chosen_icon})
        return processed_forecast[:6], None
    except requests.exceptions.RequestException as err: return None, f"Weather Forecast Error: Request failed - {err}"
    except Exception as e: return None, f"Weather Forecast Error: Unexpected error - {e}"

def get_owm_aqi_forecast(api_key, lat, lon): # (Unchanged)
    if lat is None or lon is None: return None, "AQI Forecast Error: Invalid coordinates."
    base_url = "http://api.openweathermap.org/data/2.5/air_pollution/forecast"; params = {"lat": lat, "lon": lon, "appid": api_key}
    try:
        response = requests.get(base_url, params=params, timeout=15); response.raise_for_status(); data = response.json()
        hourly_forecasts = data.get("list", []); daily_max_aqi = {} # Process hourly...
        for hour_data in hourly_forecasts:
            dt_object = datetime.datetime.fromtimestamp(hour_data.get("dt"), tz=datetime.timezone.utc); date_key = dt_object.date(); owm_aqi = hour_data.get("main", {}).get("aqi")
            if owm_aqi is not None:
                 if date_key not in daily_max_aqi or owm_aqi > daily_max_aqi[date_key]: daily_max_aqi[date_key] = owm_aqi
        return daily_max_aqi, None
    except requests.exceptions.RequestException as err: return None, f"AQI Forecast Error: Request failed - {err}"
    except Exception as e: return None, f"AQI Forecast Error: Unexpected error - {e}"

def get_waqi_nearby_stations(api_key, lat, lon, radius_deg=1.5, max_stations=10): # (Unchanged)
    if lat is None or lon is None: return None, "Nearby Error: Invalid coordinates."
    if not api_key: return None, "Nearby Error: WAQI API Key missing."
    lat1 = lat - radius_deg; lon1 = lon - radius_deg; lat2 = lat + radius_deg; lon2 = lon + radius_deg
    lat1 = max(-90, lat1); lon1 = max(-180, lon1); lat2 = min(90, lat2); lon2 = min(180, lon2)
    bounds = f"{lat1:.4f},{lon1:.4f},{lat2:.4f},{lon2:.4f}"; base_url = f"https://api.waqi.info/map/bounds/"; params = {"latlng": bounds, "token": api_key}
    try:
        response = requests.get(base_url, params=params, timeout=20); response.raise_for_status(); data = response.json()
        if data.get("status") == "ok":
            stations = data.get("data", []); processed_stations = []
            for station in stations:
                station_lat = station.get("lat"); station_lon = station.get("lon")
                if station_lat is not None and station_lon is not None:
                     if abs(station_lat - lat) < 0.01 and abs(station_lon - lon) < 0.01: continue
                aqi_str = station.get("aqi");
                if aqi_str and aqi_str != "-":
                    try: aqi_val = int(aqi_str); station_name = station.get("station", {}).get("name", "Unknown Station"); processed_stations.append({ "name": station_name, "aqi": aqi_val, "lat": station_lat, "lon": station_lon, "url": station.get("station", {}).get("url") })
                    except (ValueError, TypeError): continue
            sorted_stations = sorted(processed_stations, key=lambda x: x["aqi"], reverse=True)
            return sorted_stations[:max_stations], None
        else: error_message = data.get("data", "Unknown WAQI error."); return None, f"Nearby Error: WAQI API - {error_message}"
    except requests.exceptions.RequestException as err: return None, f"Nearby Error: Request failed - {err}"
    except Exception as e: return None, f"Nearby Error: Unexpected error - {e}"

# -----------------------------------------------------------------------------
# Plotting and Display Functions
# -----------------------------------------------------------------------------
# --- History Chart --- UPDATED (Plotting function unchanged, but will use OWM data) ---
def create_history_line_chart(history_data, value_key='pm25', y_axis_label='PM2.5 (µg/m³)', title=f'PM2.5 Concentration - Last 7 Days (OWM) for {st.session_state.city}'):
    """Creates a Plotly line chart for historical data, handling single points."""
    chart_title = title
    if not history_data:
        fig = go.Figure(); fig.update_layout(title="No Historical PM2.5 Data Available (OWM)", template=PLOTLY_TEMPLATE, paper_bgcolor=card_bg, plot_bgcolor=card_bg, xaxis={'visible': False}, yaxis={'visible': False}, height=300); return fig

    timestamps = [item["timestamp"] for item in history_data]
    values = [item[value_key] for item in history_data] # Use the specified key

    if len(history_data) <= 1:
        plot_mode = 'markers'
        if len(history_data) == 1: chart_title += " (Only 1 data point available)"
    else: plot_mode = 'lines+markers'

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=timestamps, y=values, mode=plot_mode, name=value_key.upper(),
        line=dict(color=HISTORY_LINE_COLOR, width=2),
        marker=dict(color=HISTORY_MARKER_COLOR, size=7),
        hovertemplate=f'<b>%{{x|%Y-%m-%d %H:%M}}</b><br>{value_key.upper()}: %{{y:.2f}}<extra></extra>'
    ))
    fig.update_layout(
        title=chart_title, xaxis_title='Date/Time', yaxis_title=y_axis_label,
        template=PLOTLY_TEMPLATE, paper_bgcolor=card_bg, plot_bgcolor=card_bg,
        xaxis=dict(gridcolor='#555'), yaxis=dict(gridcolor='#555'),
        hovermode='x unified', height=350, margin=dict(l=40, r=20, t=50, b=40)
    )
    if len(history_data) == 1 and values:
         y_val = values[0]
         fig.update_layout(yaxis_range=[max(0, y_val - 5), y_val + 5])

    return fig

# --- Other Plotting Functions (Unchanged) ---
# ... (create_aqi_gauge, display_forecast_table, create_nearby_bar_chart, ...) ...
# ... (create_world_map, create_ranking_bar_chart, generate_analytical_note unchanged) ...
def create_aqi_gauge(aqi_value):
    # Default values for unknown AQI
    if aqi_value is None:
        aqi_value = -1  # Use -1 to indicate unknown
    try:
        aqi_value = int(aqi_value)
    except (ValueError, TypeError):
        aqi_value = -1

    aqi_label, aqi_color = get_aqi_category(aqi_value)
    if aqi_value < 0:
        display_value_text = "N/A"
        title_text = "AQI Unavailable"
        bar_color = "#808080"  # Grey for unknown
        needle_angle = 180  # Point straight left (0 position)
    else:
        display_value_text = str(aqi_value)
        title_text = f"<b>{aqi_label}</b>"
        bar_color = aqi_color
        # Needle Angle Calculation: Map AQI value (0-500) to angle (180-0 degrees)
        clamped_value = max(0, min(aqi_value, 500))
        needle_angle = 180 - (clamped_value / 500) * 180

    # Define Gauge Steps using AQI_CATEGORIES
    gauge_steps = []
    cumulative_upper = 0
    for (lower, upper), category in AQI_CATEGORIES.items():
        step_lower = lower if lower > 0 else 0
        step_upper = upper if upper <= 500 else 500
        step_lower = max(step_lower, cumulative_upper)
        if step_upper > step_lower:
            gauge_steps.append({'range': [step_lower, step_upper], 'color': category["color"]})
            cumulative_upper = step_upper
        if cumulative_upper >= 500:
            break

    if cumulative_upper < 500 and gauge_steps:
        last_color = gauge_steps[-1]['color']
        gauge_steps.append({'range': [cumulative_upper, 500], 'color': last_color})
    elif not gauge_steps:
        gauge_steps = [{'range': [0, 500], 'color': '#808080'}]

    # Create the Indicator Figure
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=max(0, aqi_value) if aqi_value >= 0 else 0,
        number={
            'valueformat': '.0f',
            'suffix': " US AQI" if aqi_value >= 0 else "",
            'font': {'size': 35, 'color': text_color},
        },
        title={
            'text': title_text,
            'font': {'size': 18, 'color': aqi_color if aqi_value >= 0 else hint_text_color}
        },
        gauge={
            'axis': {
                'range': [0, 500],
                'tickvals': [0, 50, 100, 150, 200, 300, 500],
                'ticktext': ['0', '50', '100', '150', '200', '300', '500'],
                'tickfont': {'size': 10, 'color': hint_text_color},
                'tickwidth': 1,
                'tickcolor': text_color
            },
            'bar': {'color': "rgba(0,0,0,0)", 'thickness': 0},
            'bgcolor': "rgba(0,0,0,0)",
            'borderwidth': 0,
            'steps': gauge_steps,
        }
    ))

    # Customize Layout for Speedometer Look
    fig.update_layout(
        paper_bgcolor=card_bg,
        plot_bgcolor='rgba(0,0,0,0)',
        font={'color': text_color, 'family': "Roboto, sans-serif"},
        height=280,
        margin=dict(l=20, r=20, t=60, b=30, pad=0),
    )

    # Add the Needle Shape
    center_x = 0.5
    center_y = 0.05
    needle_length = 0.35
    needle_rad = math.radians(needle_angle)
    tip_x = center_x + needle_length * math.cos(needle_rad)
    tip_y = center_y + needle_length * math.sin(needle_rad)

    # Base of the needle (create a small triangle base)
    base_width = 0.03
    angle_left_rad = math.radians(needle_angle + 90)
    angle_right_rad = math.radians(needle_angle - 90)
    base1_x = center_x + base_width * math.cos(angle_left_rad)
    base1_y = center_y + base_width * math.sin(angle_left_rad)
    base2_x = center_x + base_width * math.cos(angle_right_rad)
    base2_y = center_y + base_width * math.sin(angle_right_rad)

    # Add the needle as a path (triangle)
    fig.add_shape(
        type="path",
        path=f" M {base1_x},{base1_y} L {tip_x},{tip_y} L {base2_x},{base2_y} Z",
        fillcolor=text_color,
        line=dict(color=text_color, width=1)
    )

    # Add a small circle at the pivot point
    fig.add_shape(
        type="circle",
        x0=center_x - base_width * 0.8,
        y0=center_y - base_width * 0.8,
        x1=center_x + base_width * 0.8,
        y1=center_y + base_width * 0.8,
        fillcolor=text_color,
        line=dict(color=text_color)
    )

    # Handle N/A display explicitly
    if aqi_value < 0:
        fig.update_traces(
            number={'font': {'size': 1, 'color': 'rgba(0,0,0,0)'}},
            selector=dict(type='indicator')
        )
        fig.add_annotation(
            x=0.5,
            y=0.3,
            text=display_value_text,
            showarrow=False,
            font=dict(size=35, color=hint_text_color)
        )

    # Add AQI category labels below the gauge (Good, Moderate, etc.) with colored backgrounds
    categories = [
    {"label": "Good", "range": "0-50", "color": AQI_CATEGORIES[(0, 50)]["color"]},
    {"label": "Moderate", "range": "51-100", "color": AQI_CATEGORIES[(51, 100)]["color"]},
    {"label": "Unhealthy for Sensitive Groups", "range": "101-150", "color": AQI_CATEGORIES[(101, 150)]["color"]},
    {"label": "Unhealthy", "range": "151-200", "color": AQI_CATEGORIES[(151, 200)]["color"]},
    {"label": "Very Unhealthy", "range": "201-300", "color": AQI_CATEGORIES[(201, 300)]["color"]},
    {"label": "Hazardous", "range": "301-500", "color": AQI_CATEGORIES[(301, 500)]["color"]}
]

num_categories = len(categories)
x_positions = [i / (num_categories - 1) if num_categories > 1 else 0.5 for i in range(num_categories)]
y_position = -0.1

for idx, category in enumerate(categories):
    fig.add_annotation(
        x=x_positions[idx],
        y=y_position,
        text=f"{category['label']}<br>{category['range']}",
        showarrow=False,
        font=dict(size=10, color="#FFFFFF"),
        align="center",
        bgcolor=category["color"],
        bordercolor=category["color"],
        borderwidth=1,
        borderpad=4
    )

    

    return fig

def display_forecast_table(weather_forecast, aqi_forecast): # (Unchanged)
    if not weather_forecast: st.info("Weather forecast data unavailable."); return
    combined_data = [] # Combine weather/aqi...
    for day_weather in weather_forecast:
        date_key = day_weather["date"]; max_aqi = aqi_forecast.get(date_key); aqi_category = get_owm_aqi_forecast_category(max_aqi) if max_aqi else "N/A"
        icon_url = f"http://openweathermap.org/img/wn/{day_weather['icon']}.png" if day_weather.get('icon') else None
        combined_data.append({"Date": date_key.strftime("%a, %b %d"), "Condition": day_weather["description"], "IconURL": icon_url, "Max Temp (°C)": f"{day_weather.get('max_temp'):.1f}" if day_weather.get('max_temp') is not None else "N/A", "Min Temp (°C)": f"{day_weather.get('min_temp'):.1f}" if day_weather.get('min_temp') is not None else "N/A", "Max AQI (OWM)": aqi_category })
    if not combined_data: st.info("No combined forecast data."); return
    df = pd.DataFrame(combined_data); st.dataframe(df, use_container_width=True, hide_index=True, # Display dataframe...
                 column_config={ "IconURL": st.column_config.ImageColumn("Icon", width="small"), "Date": st.column_config.TextColumn(width="small"), "Condition": st.column_config.TextColumn(width="medium"), "Max Temp (°C)": st.column_config.TextColumn(width="small"), "Min Temp (°C)": st.column_config.TextColumn(width="small"), "Max AQI (OWM)": st.column_config.TextColumn("AQI Fcst", help="Max Daily OWM AQI (1-5 Scale)", width="small") },
                 column_order=("Date", "IconURL", "Condition", "Max Temp (°C)", "Min Temp (°C)", "Max AQI (OWM)"))

def create_nearby_bar_chart(station_data): # (Unchanged)
    if not station_data:
        fig = go.Figure(); fig.update_layout(title="No Nearby Stations Found", template=PLOTLY_TEMPLATE, paper_bgcolor=card_bg, plot_bgcolor=card_bg, xaxis={'visible': False}, yaxis={'visible': False}, height=300); return fig
    plot_data = station_data[::-1]; station_names = [s['name'][:30] + '...' if len(s['name']) > 30 else s['name'] for s in plot_data]
    aqi_values = [s['aqi'] for s in plot_data]; bar_colors = [get_aqi_category(s['aqi'])[1] for s in plot_data]
    hover_texts = [f"Station: {s['name']}<br>AQI: {s['aqi']}<br>Lat/Lon: {s['lat']:.3f}, {s['lon']:.3f}<extra></extra>" for s in plot_data]
    fig = go.Figure(go.Bar(y=station_names, x=aqi_values, orientation='h', marker=dict(color=bar_colors), hoverinfo='text', hovertext=hover_texts))
    fig.update_layout(title=f'Top {len(station_names)} Nearby Stations (US AQI)', xaxis_title='Air Quality Index (US EPA)', yaxis_title='Station Name', template=PLOTLY_TEMPLATE, paper_bgcolor=card_bg, plot_bgcolor=card_bg, yaxis=dict(tickfont=dict(size=10)), xaxis=dict(gridcolor='#555'), height=max(300, len(station_names) * 35), margin=dict(l=150, r=20, t=50, b=40))
    return fig

def create_world_map(station_data, mapbox_token, center_lat=23.8, center_lon=90.4, zoom=5): # (Unchanged)
    if not station_data:
        fig = go.Figure(go.Scattermapbox()); fig.update_layout(title="No Station Data Available for Map", mapbox=dict(style="dark", accesstoken=mapbox_token, center=dict(lat=center_lat, lon=center_lon), zoom=1), template=PLOTLY_TEMPLATE, paper_bgcolor=card_bg, height=500, margin={"r":0,"t":30,"l":0,"b":0}); return fig
    lats = [s['lat'] for s in station_data]; lons = [s['lon'] for s in station_data]; aqi_values = [s['aqi'] for s in station_data]
    station_names = [s['name'] for s in station_data]; marker_colors = [get_aqi_category(s['aqi'])[1] for s in station_data]
    hover_texts = [f"<b>{s['name']}</b><br>AQI: {s['aqi']}<extra></extra>" for s in station_data]
    marker_sizes = [15 if s['aqi'] > 200 else (12 if s['aqi'] > 100 else 9) for s in station_data]
    fig = go.Figure(go.Scattermapbox(lat=lats, lon=lons, mode='markers', marker=go.scattermapbox.Marker(size=marker_sizes, color=marker_colors, opacity=0.8), text=station_names, hoverinfo='text', customdata=[s['aqi'] for s in station_data], hovertemplate=hover_texts))
    fig.update_layout(title='Live Air Pollution Map (WAQI Stations)', mapbox=dict(style='dark', accesstoken=mapbox_token, center=go.layout.mapbox.Center(lat=center_lat, lon=center_lon), zoom=zoom, pitch=0), showlegend=False, template=PLOTLY_TEMPLATE, paper_bgcolor=card_bg, height=600, margin={"r":0,"t":40,"l":0,"b":0})
    return fig

def create_ranking_bar_chart(ranking_data, top_n=10): # (Unchanged)
    if not ranking_data:
        fig = go.Figure(); fig.update_layout(title=f"Data Unavailable for City Ranking", template=PLOTLY_TEMPLATE, paper_bgcolor=card_bg, plot_bgcolor=card_bg, xaxis={'visible': False}, yaxis={'visible': False}, height=300); return fig
    sorted_data = sorted(ranking_data, key=lambda x: x["aqi"], reverse=True); plot_data = sorted_data[:top_n]; plot_data = plot_data[::-1]
    city_names = [s['name'][:30] + '...' if len(s['name']) > 30 else s['name'] for s in plot_data]
    aqi_values = [s['aqi'] for s in plot_data]; bar_colors = [get_aqi_category(s['aqi'])[1] for s in plot_data]
    hover_texts = [f"City: {s['name']}<br>AQI: {s['aqi']}<extra></extra>" for s in plot_data]
    fig = go.Figure(go.Bar(y=city_names, x=aqi_values, orientation='h', marker=dict(color=bar_colors), hoverinfo='text', hovertext=hover_texts))
    fig.update_layout(title=f'Top {len(plot_data)} Polluted Cities (from monitored list)', xaxis_title='Air Quality Index (US EPA)', yaxis_title='City Name', template=PLOTLY_TEMPLATE, paper_bgcolor=card_bg, plot_bgcolor=card_bg, yaxis=dict(tickfont=dict(size=10)), xaxis=dict(gridcolor='#555'), height=max(300, len(plot_data) * 35), margin=dict(l=150, r=20, t=50, b=40))
    return fig

def generate_analytical_note(aqi_data, weather_data): # (Unchanged)
    # ... (analytical note generation code) ...
    notes = []; aqi_value = aqi_data.get('aqi_us') if aqi_data else None
    wind_speed = weather_data.get('wind_speed') if weather_data else None; humidity = weather_data.get('humidity') if weather_data else None
    description = weather_data.get('description', '').lower() if weather_data else ''; wind_threshold_low = 1.5; wind_threshold_high = 5.0; humidity_threshold_high = 75
    if wind_speed is not None:
        if wind_speed > wind_threshold_high: notes.append("Strong winds may help disperse pollutants.")
        elif wind_speed < wind_threshold_low: notes.append("Light winds might lead to pollutant accumulation.")
    if 'rain' in description or 'drizzle' in description or 'shower' in description: notes.append("Precipitation can help wash pollutants from the air.")
    if humidity is not None and humidity > humidity_threshold_high: notes.append("High humidity can sometimes contribute to haze.")
    if aqi_value is not None:
        if aqi_value > 150: notes.append("Current AQI levels are high, consider health recommendations.")
        elif aqi_value < 50: notes.append("Air quality appears good.")
    if not notes: return "General weather conditions observed."
    return " | ".join(notes[:2]) + (". *Note: General observations.*" if notes else "")

# -----------------------------------------------------------------------------
# Sidebar Implementation (Unchanged from previous version)
# -----------------------------------------------------------------------------
with st.sidebar:
    # ... (sidebar code unchanged) ...
    st.header("Settings & Search")
    st.subheader("API Keys")
    st.caption("Enter personal API keys from IQAir, OpenWeatherMap, WAQI (aqicn.org), and Mapbox.")

    # --- API Key Inputs (Unchanged) ---
    st.session_state.iqair_api_key = st.text_input("IQAir API Key", type="password", value=st.session_state.iqair_api_key, placeholder="Required for AQI & Location Lists") 
    st.caption("eg: 52f95a10-d7d8-4003-b919-7bad7a57cd08") # Added example hint
    st.session_state.openweathermap_api_key = st.text_input("OpenWeatherMap API Key", type="password", value=st.session_state.openweathermap_api_key, placeholder="Required for Weather & Forecasts")
    st.caption("eg: 924f28bc729c8d8d37a0a9e0471a0b6d") # Added example hint
    st.session_state.waqi_api_key = st.text_input("WAQI API Key (aqicn.org)", type="password", value=st.session_state.waqi_api_key, placeholder="Required for Nearby, Map, Ranking")
    st.caption("eg: 2fe106271126a1394205ba0ff5606c5bd165f20a") # Added example hint
    st.session_state.mapbox_token = st.text_input("Mapbox Access Token", type="password", value=st.session_state.mapbox_token, placeholder="Required for World Map display")
    st.caption("eg: pk.eyJ1IjoiYXZvZWR1IiwiYSI6ImNtOXZhdm51NDBocmsya29wZjQwOWYwYjEifQ.eO5JA-fwx1WLJIYVQYLwIw") # Added example hint (matches Mapbox format)

    st.markdown("---")
    st.subheader("Search Location")
    st.caption("Select location using the dropdowns below.")

    # --- Dynamic Select Boxes ---
    countries_list, country_error = get_iqair_countries(st.session_state.iqair_api_key)
    states_list, state_error = [], None
    cities_list, city_error = [], None

    # Display error if fetching countries failed (and key was provided)
    if country_error and st.session_state.iqair_api_key:
        st.error(f"Could not load countries: {country_error}")

    # --- Country Selection ---
    # Find index of previously selected country, default to 0 if not found or list empty
    try:
        country_index = countries_list.index(st.session_state.country) if st.session_state.country in countries_list else 0
    except ValueError:
        country_index = 0 # Default if list is empty or selection invalid

    selected_country = st.selectbox(
        "Country",
        options=countries_list,
        index=country_index,
        placeholder="Select Country...",
        key='country_selector', # Use a distinct key
        disabled=not st.session_state.iqair_api_key or not countries_list # Disable if no key or no countries
    )

    # --- State/Region Selection ---
    # Only fetch states if a country is selected and IQAir key is valid
    if selected_country and st.session_state.iqair_api_key:
        states_list, state_error = get_iqair_states(st.session_state.iqair_api_key, selected_country)
        if state_error:
            st.error(f"Could not load states for {selected_country}: {state_error}")

    # Find index of previously selected state
    try:
         state_index = states_list.index(st.session_state.state_region) if st.session_state.state_region in states_list else 0
    except ValueError:
         state_index = 0

    selected_state = st.selectbox(
        "State / Region",
        options=states_list,
        index=state_index,
        placeholder="Select State/Region...",
        key='state_selector',
        disabled=not selected_country or not states_list # Disable if no country or no states
    )

    # --- City Selection ---
    # Only fetch cities if a state and country are selected and IQAir key is valid
    if selected_state and selected_country and st.session_state.iqair_api_key:
        cities_list, city_error = get_iqair_cities(st.session_state.iqair_api_key, selected_country, selected_state)
        if city_error:
            st.error(f"Could not load cities for {selected_state}: {city_error}")

    # Find index of previously selected city
    try:
        city_index = cities_list.index(st.session_state.city) if st.session_state.city in cities_list else 0
    except ValueError:
        city_index = 0

    selected_city = st.selectbox(
        "City",
        options=cities_list,
        index=city_index,
        placeholder="Select City...",
        key='city_selector',
        disabled=not selected_state or not cities_list # Disable if no state or no cities
    )

    # --- Update session state when selections change ---
    # Check if selections have actually changed to avoid unnecessary updates
    if selected_country != st.session_state.country:
        st.session_state.country = selected_country
        # IMPORTANT: Reset state and city if country changes
        st.session_state.state_region = ""
        st.session_state.city = ""
        # Force rerun to update dependent dropdowns
        st.rerun()

    if selected_state != st.session_state.state_region:
        st.session_state.state_region = selected_state
        # IMPORTANT: Reset city if state changes
        st.session_state.city = ""
        # Force rerun to update dependent dropdowns
        st.rerun()

    if selected_city != st.session_state.city:
        st.session_state.city = selected_city
        # Don't need to rerun here unless city change should trigger something immediately

    # --- View Data Button ---
    if st.button("View Data", key="view_data_button"):
        # Reset data and errors before fetching
        st.session_state.weather_data = None; st.session_state.weather_error = None
        st.session_state.aqi_data = None; st.session_state.aqi_error = None
        st.session_state.coordinates = None; st.session_state.coordinates_error = None
        st.session_state.history_data = None; st.session_state.history_error = None
        st.session_state.forecast_data = None; st.session_state.forecast_error = None
        st.session_state.nearby_data = None; st.session_state.nearby_error = None
        st.session_state.map_data = None; st.session_state.map_error = None
        st.session_state.ranking_data = None; st.session_state.ranking_error = None

        # Validation
        valid = True
        if not st.session_state.iqair_api_key: st.warning("IQAir API Key is required."); valid = False
        if not st.session_state.openweathermap_api_key: st.warning("OpenWeatherMap API Key is required."); valid = False
        if not st.session_state.waqi_api_key: st.warning("WAQI API Key is required."); valid = False
        if not st.session_state.mapbox_token: st.warning("Mapbox Access Token is required."); valid = False
        # Check if selections are made
        if not st.session_state.country: st.warning("Please select a Country."); valid = False
        if not st.session_state.state_region and states_list: st.warning("Please select a State/Region."); valid = False # Only require if states exist for the country
        if not st.session_state.city and cities_list: st.warning("Please select a City."); valid = False # Only require if cities exist for the state

        if valid:
            st.session_state.view_data_clicked = True
            st.info("Fetching data...")
            # Rerun to clear warnings and start fetching in the main area
            st.rerun()
        else:
            st.session_state.view_data_clicked = False
# --- End of Sidebar Replacement ---

# -----------------------------------------------------------------------------
# Main Dashboard Area --- UPDATED FETCH LOGIC FOR #3 ---
# -----------------------------------------------------------------------------
st.header("Dashboard")

if st.session_state.view_data_clicked:
    # --- Fetch Data Sequentially ---
    fetch_success = True; lat = None; lon = None
    # 0. Get Coordinates
    if st.session_state.coordinates is None and st.session_state.coordinates_error is None:
         with st.spinner("Finding location coordinates..."): st.session_state.coordinates, st.session_state.coordinates_error = get_coordinates(st.session_state.openweathermap_api_key, st.session_state.city, st.session_state.state_region, st.session_state.country)
    if st.session_state.coordinates_error: st.error(f"Location Error: {st.session_state.coordinates_error}"); fetch_success = False
    elif st.session_state.coordinates: lat = st.session_state.coordinates.get('lat'); lon = st.session_state.coordinates.get('lon')
    else: fetch_success = False # Coordinates are essential for most dependent features

    # Fetch Ranking Data Concurrently (Unchanged)
    if st.session_state.ranking_data is None and st.session_state.ranking_error is None:
        ranking_results = []; ranking_errors = []
        with st.spinner(f"Fetching AQI for major cities..."):
            with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                future_to_city = {executor.submit(get_waqi_feed, st.session_state.waqi_api_key, city): city for city in CITIES_FOR_RANKING}
                for future in concurrent.futures.as_completed(future_to_city):
                    city = future_to_city[future]
                    try:
                        data, error = future.result()
                        if error and "Unknown station" not in error and "Unexpected WAQI status" not in error: ranking_errors.append(error) # Log only critical errors
                        elif data: ranking_results.append(data)
                    except Exception as exc: ranking_errors.append(f"Ranking Error ({city}): Exception - {exc}")
            st.session_state.ranking_data = ranking_results
            unique_errors = list(set(ranking_errors))
            if unique_errors: st.session_state.ranking_error = "; ".join(unique_errors[:2]) + ('...' if len(unique_errors) > 2 else '')

    if fetch_success: # Fetch dependent data only if coordinates are valid
        # 1. Fetch AQI (IQAir)
        if st.session_state.aqi_data is None and st.session_state.aqi_error is None:
            with st.spinner("Fetching AQI..."): st.session_state.aqi_data, st.session_state.aqi_error = get_iqair_aqi(st.session_state.iqair_api_key, st.session_state.city, st.session_state.state_region, st.session_state.country)
        # 2. Fetch Current Weather (OWM)
        if st.session_state.weather_data is None and st.session_state.weather_error is None:
             with st.spinner("Fetching Weather..."): st.session_state.weather_data, st.session_state.weather_error = get_openweathermap_weather(st.session_state.openweathermap_api_key, st.session_state.city, st.session_state.state_region, st.session_state.country)

        # --- 3. Fetch History (OWM) --- REVERTED CALL ---
        if st.session_state.history_data is None and st.session_state.history_error is None:
             with st.spinner("Fetching Air Quality History (OWM)..."): # Indicate source
                 st.session_state.history_data, st.session_state.history_error = get_owm_history(
                     st.session_state.openweathermap_api_key, lat, lon, days=7
                 )

        # 4. Fetch Nearby Stations (WAQI)
        if st.session_state.nearby_data is None and st.session_state.nearby_error is None:
             with st.spinner("Fetching Nearby Stations..."): st.session_state.nearby_data, st.session_state.nearby_error = get_waqi_nearby_stations(st.session_state.waqi_api_key, lat, lon) # Uses updated radius from function default
        # 5. Fetch Forecasts (OWM Weather + OWM AQI)
        if st.session_state.forecast_data is None and st.session_state.forecast_error is None:
             with st.spinner("Fetching Forecast..."):
                weather_fc_res, weather_fc_err = get_owm_5day_weather_forecast(st.session_state.openweathermap_api_key, lat, lon)
                aqi_fc_res, aqi_fc_err = get_owm_aqi_forecast(st.session_state.openweathermap_api_key, lat, lon)
                if weather_fc_err or aqi_fc_err: st.session_state.forecast_error = f"Weather: {weather_fc_err or 'OK'} | AQI: {aqi_fc_err or 'OK'}"; st.session_state.forecast_data = None
                elif weather_fc_res is not None and aqi_fc_res is not None: st.session_state.forecast_data = {"weather": weather_fc_res, "aqi": aqi_fc_res}
                else: st.session_state.forecast_error = "Failed to retrieve complete forecast data."; st.session_state.forecast_data = None
        # 6. Fetch Map Data (WAQI)
        if st.session_state.map_data is None and st.session_state.map_error is None:
             with st.spinner("Fetching Map Data..."):
                 map_lat1 = lat - 10; map_lon1 = lon - 10; map_lat2 = lat + 10; map_lon2 = lon + 10
                 map_lat1 = max(-90, map_lat1); map_lon1 = max(-180, map_lon1); map_lat2 = min(90, map_lat2); map_lon2 = min(180, map_lon2)
                 st.session_state.map_data, st.session_state.map_error = get_waqi_map_stations(st.session_state.waqi_api_key, map_lat1, map_lon1, map_lat2, map_lon2)

    # --- Display Location Header (Unchanged) ---
    st.markdown(f'<p style="color:#CACACA; margin-top: 0rem; margin-bottom: 0.5rem;">Showing Data for: {st.session_state.country}, {st.session_state.state_region}, {st.session_state.city}</p>', unsafe_allow_html=True)
   
    
    # --- Data Visualization Sections ---
    colA, colB = st.columns(2)
    with colA:
    st.markdown(f'<h3 style="color:#FFFFFF;">Air Quality Index in <b>{st.session_state.city}</b></h3>', unsafe_allow_html=True)
    
    if st.session_state.aqi_error:
        st.error(f"AQI Error: {st.session_state.aqi_error}")
        st.plotly_chart(create_aqi_gauge(None), use_container_width=True)
    elif st.session_state.aqi_data:
        aqi_val = st.session_state.aqi_data.get('aqi_us')
        st.plotly_chart(create_aqi_gauge(aqi_val), use_container_width=True)

        # Display Timestamp and Main Pollutant (if available) below the gauge
        timestamp = st.session_state.aqi_data.get('pollutant_ts')
        main_pollutant = st.session_state.aqi_data.get('main_pollutant_us')
        if timestamp and main_pollutant:
            dt_object = datetime.datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=datetime.timezone.utc)
            st.markdown(f"""
            <div style="line-height: 1.5;">
                <span>Main Pollutant: {main_pollutant.upper()}</span><br>
                <span>Last Updated: {dt_object.strftime('%Y-%m-%d %H:%M:%S UTC')}</span>
            </div>
            """, unsafe_allow_html=True)
        

    # st.markdown("</div>", unsafe_allow_html=True) # Remove if you were using container divs
    # --- ADD End: New AQI Display Block ---

    with colB: # --- Health Recommendations (#2) --- (Display unchanged)
    # Health Recommendations Box
    # st.markdown('<div class="data-container">', unsafe_allow_html=True)        
        st.markdown('<h3 style="color:#FFFFFF;">Health Recommendations</h3>', unsafe_allow_html=True)

        # Health content
        if st.session_state.aqi_error:
            st.warning("Cannot display recommendations (AQI error).")
        elif st.session_state.aqi_data:
            aqi_val = st.session_state.aqi_data.get('aqi_us')
            category_label, category_color = get_aqi_category(aqi_val)
            recommendation = HEALTH_RECOMMENDATIONS.get(category_label, HEALTH_RECOMMENDATIONS["Unknown"])
    
            if category_label != "Unknown":
                text_clr = "#000000" if category_label in ["Moderate", "Good"] else "#FFFFFF";
                st.markdown(f'<span class="recommendation-category" style="background-color:{category_color}; color:{text_clr};">{category_label} ({aqi_val})</span>', unsafe_allow_html=True)
                st.markdown(f"**{recommendation['short']}**");
                st.markdown(f'<div class="recommendation-details">{recommendation["details"]}</div>', unsafe_allow_html=True)
            else:
                st.info("AQI category unknown.")
                st.write(recommendation['details'])

            # Embed ElevenLabs inside same container
            # --- Insert the ElevenLabs widget code here ---
            # Make sure this variable definition is included!
            elevenlabs_embed_code_in_box = """
            <div style="z-index: 100; margin-top: 20px;"> <elevenlabs-convai agent-id="rHhQqxWxk4pue21ttj6s"></elevenlabs-convai> 
                <script src="https://elevenlabs.io/convai-widget/index.js" async type="text/javascript"></script>
            </div>
            """
            # Now use the defined variable
            components.html(elevenlabs_embed_code_in_box, height=150)
            
        else:
            st.info("Waiting for AQI data...")

        st.markdown("</div>", unsafe_allow_html=True)
        
        
    # --- History Chart (#3) --- DISPLAY UPDATED ---
    #st.markdown('<div class="data-container">', unsafe_allow_html=True)
    st.markdown(f'<h3 style="color:#FFFFFF;">Historic Air Quality Graph (PM2.5 - OWM) for <b>{st.session_state.city}</b></h3>', unsafe_allow_html=True)
    if not fetch_success and st.session_state.coordinates_error: st.warning("Cannot fetch history (Location Error).")
    elif st.session_state.history_error: st.error(f"{st.session_state.history_error}") # Display specific OWM error
    elif st.session_state.history_data is not None:
        # Use the same plotting function, it handles sparse data from OWM too
        st.plotly_chart(create_history_line_chart(st.session_state.history_data, value_key='pm25', y_axis_label='PM2.5 (µg/m³)', title='PM2.5 Concentration - Last 7 Days (OWM)'), use_container_width=True)
        if 0 < len(st.session_state.history_data) <= 1:
             st.caption("Note: Limited historical data points available from OWM API for the selected period.")
        elif not st.session_state.history_data: # Check for empty list []
             st.caption("Note: No historical data points returned by OWM API for the selected period.")
    elif fetch_success: st.info("Historical data loading (OWM)...")
    else: st.info("Historical data unavailable.")

    # --- Layout for bottom features ---
    colC, colD = st.columns(2)
    with colC:
        # --- Nearby Stations (#4) --- (Display unchanged)
        #st.markdown('<div class="data-container">', unsafe_allow_html=True)
        st.markdown(f'<h3 style="color:#FFFFFF;">Most Polluted Locations Near <b>{st.session_state.city}</b></h3>', unsafe_allow_html=True)
        # ... (display code unchanged) ...
        if not fetch_success and st.session_state.coordinates_error: st.warning("Cannot fetch nearby stations (Location Error).")
        elif st.session_state.nearby_error: st.error(f"{st.session_state.nearby_error}")
        elif st.session_state.nearby_data is not None: st.plotly_chart(create_nearby_bar_chart(st.session_state.nearby_data), use_container_width=True)
        elif fetch_success: st.info("Nearby stations data loading...")
        else: st.info("Nearby stations data unavailable.")
        st.markdown("</div>", unsafe_allow_html=True)
        # --- Top Cities (#7) --- (Display unchanged)
        #st.markdown('<div class="data-container">', unsafe_allow_html=True);
        st.markdown('<h3 style="color:#FFFFFF;">Live AQI - Selected Major Cities</h3>', unsafe_allow_html=True)
        # ... (display code unchanged) ...
        if st.session_state.ranking_error: st.error(f"City Ranking Error: {st.session_state.ranking_error}")
        elif st.session_state.ranking_data is not None: st.plotly_chart(create_ranking_bar_chart(st.session_state.ranking_data, top_n=10), use_container_width=True)
        else: st.info("Major city AQI data loading...")
        st.markdown("</div>", unsafe_allow_html=True)
    with colD:
         # --- Weather Report (#5) w/ Note --- (Display unchanged)
        #st.markdown('<div class="data-container">', unsafe_allow_html=True);
        st.markdown(f'<h3 style="color:#FFFFFF;">Today\'s Weather in <b>{st.session_state.city}</b></h3>', unsafe_allow_html=True)
        # Note the escape character \' for the apostrophe inside the f-string
        # ... (display code unchanged) ...
        if st.session_state.weather_error: st.error(f"Weather Error: {st.session_state.weather_error}")
        elif st.session_state.weather_data:
            weather = st.session_state.weather_data; w_col1, w_col2, w_col3 = st.columns(3);
            with w_col1:
                if weather.get('temperature') is not None: st.metric(label="Temp", value=f"{weather['temperature']}°C", delta=f"{weather.get('feels_like','')}°C Feels Like")
                if weather.get('icon'): st.image(f"http://openweathermap.org/img/wn/{weather['icon']}@2x.png", width=60, caption=weather.get('description',''))
                else: st.write(f"**Condition:** {weather.get('description','N/A')}")
            with w_col2:
                if weather.get('humidity') is not None: st.metric(label="Humidity", value=f"{weather['humidity']}%");
                if weather.get('pressure') is not None: st.metric(label="Pressure", value=f"{weather['pressure']} hPa")
            with w_col3:
                if weather.get('wind_speed') is not None: st.metric(label="Wind", value=f"{weather['wind_speed']} m/s")
                if weather.get('timestamp'): dt_object = datetime.datetime.fromtimestamp(weather['timestamp']); st.caption(f"Observed: {dt_object.strftime('%H:%M:%S')}")
                if weather.get('city_name') and weather.get('country'): st.caption(f"Location: {weather['city_name']}, {weather['country']}")
            analytical_note = generate_analytical_note(st.session_state.aqi_data, st.session_state.weather_data)
            if analytical_note: st.markdown(f'<div class="analytical-note">💡 **Analytic Note:** {analytical_note}</div>', unsafe_allow_html=True)
        elif fetch_success: st.info("Weather data loading...")
        else: st.info("Weather data unavailable.")
        st.markdown("</div>", unsafe_allow_html=True)
        # --- Forecast Table (#6) --- (Display unchanged)
        #st.markdown('<div class="data-container">', unsafe_allow_html=True);
        st.markdown(f'<h3 style="color:#FFFFFF;">Five Day Weather & AQI Forecast for <b>{st.session_state.city}</b></h3>', unsafe_allow_html=True)
        # ... (display code unchanged) ...
        if not fetch_success and st.session_state.coordinates_error: st.warning("Cannot fetch forecast (Location Error).")
        elif st.session_state.forecast_error: st.error(f"Forecast Error: {st.session_state.forecast_error}")
        elif st.session_state.forecast_data: display_forecast_table(st.session_state.forecast_data.get("weather"), st.session_state.forecast_data.get("aqi"))
        elif fetch_success: st.info("Forecast data loading...")
        else: st.info("Forecast data unavailable.")
        st.markdown("</div>", unsafe_allow_html=True)
    # --- World Map (#8) --- (Display unchanged)
    #st.markdown('<div class="data-container">', unsafe_allow_html=True);
    st.markdown('<h3 style="color:#FFFFFF;">World Live Air Pollution Map</h3>', unsafe_allow_html=True)
    # ... (display code unchanged) ...
    if not st.session_state.mapbox_token: st.warning("Mapbox Access Token needed in sidebar.")
    elif st.session_state.map_error: st.error(f"{st.session_state.map_error}")
    elif st.session_state.map_data is not None:
        map_center_lat = lat if lat else 23.8; map_center_lon = lon if lon else 90.4
        st.plotly_chart(create_world_map(st.session_state.map_data, st.session_state.mapbox_token, map_center_lat, map_center_lon), use_container_width=True)
    elif fetch_success: st.info("Map data loading...")
    else: st.info("Map data unavailable.")
    st.markdown("</div>", unsafe_allow_html=True)

else:
    st.info("📊 Please enter API keys, Mapbox Token, and a location in the sidebar, then click 'View Data' to load the dashboard.")

# -----------------------------------------------------------------------------
# Static Content --- UPDATED About Section ---
# -----------------------------------------------------------------------------
#st.markdown('<div class="glass-container"><div class="glass-card">', unsafe_allow_html=True)
st.header("About Air 30X")
st.markdown("""
Imagine a child in Dhaka struggling to breathe as smog chokes the city — **7 million lives are lost yearly to pollution** (WHO, 2021).

**Air 30X** was born to change that story, delivering **real-time air quality and weather insights** to protect families worldwide, starting in Bangladesh. With **AI and APIs** like **IQAir** and **OpenWeatherMap**, we're rewriting futures, one breath at a time, while our **Voice Call AI Agent** offers hope with **instant medical advice**.

🌍 Real-Time Insights
- AQI (Air Quality Index)
- Health recommendations
- Historical air quality graphs
- Most polluted nearby locations
- Today's weather & 7-day forecast
- Top 10 most polluted cities globally
- Live world air pollution map

**Note:** Data accuracy depends on API providers and local sensor networks.

💬 Life-Changing Advice
Our **Voice AI** gently guides you:  
_"Drink 2–3 liters of fresh water daily."_  
_"Limit outdoor activities when AQI >150."_

🌟 Big Impact
Supporting all **17 Sustainable Development Goals (SDGs)** and aiming to **cut 13%** of pollution-linked asthma cases (Anenberg et al., 2018).

🚀 Bright Future
Built with **Streamlit**, designed for **2.5 billion people** in polluted regions by **2030** (UNEP, 2024).

""", unsafe_allow_html=True)

#st.markdown('</div></div>', unsafe_allow_html=True)


# Removed openAQ mention, added note about OWM history limitation
# --- Developer Profile --- UPDATED ---
# ... (Previous code unchanged until the Developer Profile section)
#st.markdown('<div class="data-container">', unsafe_allow_html=True)

st.markdown('<h2 style="text-align: center; color: #FFFFFF;">AIR 13X Developer</h2>', unsafe_allow_html=True)

try:
    st.markdown('<div style="display:flex; justify-content:center;">', unsafe_allow_html=True)
    st.image(
        "Developer_MD_Mahbubur_Rahman_Photo_Covar.png"
        #width=800  # Set a fixed width that fits well in the container
    )
    st.markdown('</div>', unsafe_allow_html=True)
except Exception as e:
    st.error(f"Error loading profile image: {e}. Make sure 'Developer_MD_Mahbubur_Rahman_Photo_Covar.png' is in the correct path.")
st.markdown("</div>", unsafe_allow_html=True)

# ... (Rest of the code unchanged)

#st.markdown("</div>", unsafe_allow_html=True)

st.markdown('<h2 style="text-align: left; color: #FFFFFF;">FAQ</h2>', unsafe_allow_html=True)
faq_list = [ {"q": "What is the Air Quality Index (AQI)?", "a": "The Air Quality Index (AQI) is a system for communicating air pollution levels (0-500), indicating air cleanliness and health risks. Higher numbers mean worse quality. Values are grouped into six categories (Good to Hazardous)."}, {"q": "How does air quality affect my health?", "a": "Poor air quality can cause respiratory issues, trigger allergies, and worsen conditions like asthma or heart disease."}, {"q": "What pollutants does the app monitor?", "a": "Aims to track key pollutants like PM2.5, PM10, CO, NO2, SO2, and Ozone (O3). Data availability depends on API sources."}, {"q": "How often is air quality data updated?", "a": "Update frequency depends on the API source, often aiming for near real-time updates."}, {"q": "What does the Air Quality Index (AQI) mean?", "a": "AQI measures air pollution. Lower values (0-50) indicate safer air; higher values (100+) suggest levels harmful to health."}, {"q": "Can the app warn me about unhealthy air?", "a": "Future versions could incorporate alerts. This version focuses on displaying data."}, {"q": "How can I reduce health risks from poor air quality?", "a": "When pollution is high, stay indoors, use air purifiers, avoid strenuous outdoor activity, and wear masks (N95) if going out."}, {"q": "Is the app helpful for asthma patients?", "a": "Yes, by providing current/forecast data, it helps identify high pollution days or triggers, aiding activity planning."}, {"q": "Why should I check air quality daily?", "a": "Daily checks help understand exposure, make informed decisions about activities, and protect health."} ]
for item in faq_list:
    with st.expander(item["q"]):
        st.markdown(f"<p>{item['a']}</p>", unsafe_allow_html=True)
# -----------------------------------------------------------------------------
# Footer (remains the same)
# -----------------------------------------------------------------------------
st.markdown('<div class="footer">Copyright © 2025 MD Mahbubur Rahman | Project - Air 13x</div>', unsafe_allow_html=True)
