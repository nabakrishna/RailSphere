# import requests, logging
# from flask import current_app

# log = logging.getLogger("irctc_tracker.rail_api")


# def _headers():
#     return {
#         "X-RapidAPI-Key":  current_app.config["RAPIDAPI_KEY"],
#         "X-RapidAPI-Host": current_app.config["RAPIDAPI_HOST"],
#         "Content-Type":    "application/json",
#     }


# def get_seat_availability(train_number: str, date: str, seat_class: str,
#                           from_stn: str, to_stn: str) -> dict:
#     """
#     Calls the Indian Railway IRCTC RapidAPI for seat availability.
#     Returns dict: {success, seats, raw_response, error}
#     date format expected: DD-MM-YYYY  →  converted to YYYYMMDD for the API.
#     """
#     # Convert DD-MM-YYYY → YYYY-MM-DD  (what /api/v1/checkSeatAvailability expects)
#     try:
#         d, m, y = date.split("-")
#         api_date = f"{y}-{m}-{d}"  #--- changes--------
#         # api_date = f"{y}{m}{d}"
#     except ValueError:
#         return {"success": False, "error": "Invalid date format"}

#     # url    = f"{current_app.config['RAPIDAPI_BASE']}/api/v1/checkSeatAvailability"  --- changes---------
#     url = f"{current_app.config['RAPIDAPI_BASE']}/api/v2/checkSeatAvailability"

#     params = {
#         "classType":       seat_class,
#         "fromStationCode": from_stn.upper(),
#         "toStationCode":   to_stn.upper(),
#         "date":            api_date,   #--chnages--       # correct param name for v1
#         # "dateOfJourney": api_date, 
#         "trainNo":         train_number,
#         "quota":           "GN",
#     }

#     try:
#         resp = requests.get(url, headers=_headers(), params=params, timeout=15)
#         resp.raise_for_status()
#         data = resp.json()
#     except requests.Timeout:
#         return {"success": False, "error": "API request timed out"}
#     except requests.RequestException as exc:
#         return {"success": False, "error": str(exc)}

#     if not data.get("status"):
#         log.warning("Task API raw response: %s", data) #-- chnages----
#         return {"success": False, "error": data.get("message", "Unknown API error"), "raw": data}

#     # Parse availability from the response
#     seats = _parse_seats(data)
#     return {"success": True, "seats": seats, "raw": data}


# def _parse_seats(data: dict) -> int:
#     """
#     Extract integer seat count from the /api/v1/checkSeatAvailability response.
#     Response shape: {"data": [{"seat_avl": 42, "seat_avl_text": "AVAILABLE", ...}]}
#     Falls back to -1 if unavailable/WL/RAC/unknown.
#     """
#     try:
#         # entries = data.get("data", []) --changes---
#         entries = data.get("body", [])
#         if not isinstance(entries, list) or not entries:
#             return -1
#         first = entries[0]
#         seats_avl  = first.get("seat_avl", -1)
#         status_txt = (first.get("seat_avl_text") or "").strip().upper()
#         if status_txt == "AVAILABLE":
#             return int(seats_avl) if seats_avl != -1 else 0
#         if status_txt.startswith("WL") or status_txt.startswith("RAC"):
#             return 0
#         return -1
#     except Exception:
#         return -1


# def search_train(train_number: str) -> dict:
#     """Fetch basic train info by number."""
#     url = f"{current_app.config['RAPIDAPI_BASE']}/api/v1/searchTrain"
#     try:
#         resp = requests.get(url, headers=_headers(),
#                             params={"query": train_number}, timeout=10)
#         resp.raise_for_status()
#         data = resp.json()
#         if data.get("status") and data.get("data"):
#             body = data["data"]
#             if isinstance(body, list):
#                 body = body[0]
#             return {
#                 "success":    True,
#                 "train_name": body.get("train_name") or body.get("trainName", ""),
#                 "raw":        data,
#             }
#     except Exception as exc:
#         log.warning("search_train error: %s", exc)
#     return {"success": False, "train_name": ""}


# def get_station_suggestions(query: str) -> list[dict]:
#     """Autocomplete station search."""
#     url = f"{current_app.config['RAPIDAPI_BASE']}/api/v1/searchStation"
#     try:
#         resp = requests.get(url, headers=_headers(),
#                             params={"query": query}, timeout=8)
#         resp.raise_for_status()
#         data = resp.json()
#         if data.get("status") and data.get("data"):
#             return [
#                 {"name": s.get("station_name", ""), "code": s.get("station_code", "")}
#                 for s in (data["data"] if isinstance(data["data"], list) else [])
#             ][:10]
#     except Exception:
#         pass
#     return []



#-------------------------------------new-----------------------------------------------------

import requests, logging
from flask import current_app

log = logging.getLogger("irctc_tracker.rail_api")


def _headers():
    return {
        "X-RapidAPI-Key":  current_app.config["RAPIDAPI_KEY"],
        "X-RapidAPI-Host": current_app.config["RAPIDAPI_HOST"],
        "Content-Type":    "application/json",
    }


def get_seat_availability(train_number: str, date: str, seat_class: str,
                         from_stn: str, to_stn: str) -> dict:
    """
    Calls the Indian Railway IRCTC RapidAPI for seat availability.
    Returns dict: {success, seats, raw_response, error}
    date format expected: DD-MM-YYYY  →  converted to YYYY-MM-DD for the API v2.
    """
    # Rule 1: Convert DD-MM-YYYY → YYYY-MM-DD
    try:
        d, m, y = date.split("-")
        api_date = f"{y}-{m}-{d}"  
    except ValueError:
        return {"success": False, "error": "Invalid date format"}

    # Rule 2: Updated Endpoint to /api/v2/checkSeatAvailability
    url = f"{current_app.config['RAPIDAPI_BASE']}/api/v2/checkSeatAvailability"

    # Rule 3: Use "date" instead of "dateOfJourney"
    params = {
        "classType":       seat_class,
        "fromStationCode": from_stn.upper(),
        "toStationCode":   to_stn.upper(),
        "date":            api_date,         
        "trainNo":         train_number,
        "quota":           "GN",
    }

    try:
        resp = requests.get(url, headers=_headers(), params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
    except requests.Timeout:
        return {"success": False, "error": "API request timed out"}
    except requests.RequestException as exc:
        return {"success": False, "error": str(exc)}

    if not data.get("status"):
        log.warning("Task API raw response: %s", data) 
        return {"success": False, "error": data.get("message", "Unknown API error"), "raw": data}

    # Parse availability from the response
    seats = _parse_seats(data)
    return {"success": True, "seats": seats, "raw": data}


def _parse_seats(data: dict) -> int:
    """
    Extract integer seat count from the /api/v2/checkSeatAvailability response.
    Response shape updated as per rules.
    """
    try:
        # Rule 4: Parse response key using data.get("body", [])
        entries = data.get("body", [])
        if not isinstance(entries, list) or not entries:
            return -1
            
        first = entries[0]
        
        # Rule 5: Parse fields using seat_avl and seat_avl_text keys combined
        seats_avl  = first.get("seat_avl", -1)
        status_txt = (first.get("seat_avl_text") or "").strip().upper()
        
        if status_txt == "AVAILABLE":
            return int(seats_avl) if seats_avl != -1 else 0
        if status_txt.startswith("WL") or status_txt.startswith("RAC"):
            return 0
        return -1
    except Exception:
        return -1


# Rule 6: The search_train() function has been completely deleted (lines 83-102)


def get_station_suggestions(query: str) -> list[dict]:
    """Autocomplete station search."""
    # Rule 7: Updated Station endpoint to /api/v1/searchStation
    url = f"{current_app.config['RAPIDAPI_BASE']}/api/v1/searchStation"
    try:
        # Rule 8: Station param is "query": query
        resp = requests.get(url, headers=_headers(),
                            params={"query": query}, timeout=8)
        resp.raise_for_status()
        data = resp.json()
        
        # Rule 9: Station response parses data.get("data") 
        # and keys are station_name / station_code
        if data.get("status") and data.get("data"):
            stations_list = data["data"] if isinstance(data["data"], list) else []
            return [
                {
                    "name": s.get("station_name", ""), 
                    "code": s.get("station_code", "")
                }
                for s in stations_list
            ][:10]
    except Exception:
        pass
    return []