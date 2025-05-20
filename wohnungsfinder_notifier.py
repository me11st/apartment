# file: wohnungsfinder_notifier.py

import requests
from bs4 import BeautifulSoup
import json
import os
import smtplib
import ssl
from email.message import EmailMessage
import webbrowser
import time

# -------------------- Configuration --------------------

SEARCH_CRITERIA = {
    "location": "Berlin",       # Adjust as needed
    "max_price": 700,          # Maximum rent in Euros
    "max_rooms": 2,             # number of rooms
    "wbs_required": True       # Set to True if WBS is required
}

SEEN_LISTINGS_FILE = "seen_listings.json"
CHECK_INTERVAL = 1800  # In seconds (e.g., 3600 seconds = 1 hour)

EMAIL_SETTINGS = {
    "sender_email": os.environ.get("SENDER_EMAIL"),
    "receiver_email": os.environ.get("RECEIVER_EMAIL"),
    "smtp_server": "smtp.gmail.com",  # adjust as needed
    "smtp_port": 587,  # adjust as needed
    "username": os.environ.get("SMTP_USERNAME"),
    "password": os.environ.get("SMTP_PASSWORD")
}

# -------------------- Functions --------------------

def load_seen_listings():
    if os.path.exists(SEEN_LISTINGS_FILE):
        with open(SEEN_LISTINGS_FILE, "r") as file:
            return set(json.load(file))
    return set()

def save_seen_listings(seen_listings):
    with open(SEEN_LISTINGS_FILE, "w") as file:
        json.dump(list(seen_listings), file)

def fetch_listings():
    url = "https://inberlinwohnen.de/wohnungsfinder/"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")
    listings = []

    for item in soup.select(".listing-item"):
        title = item.select_one(".title").get_text(strip=True)
        price_text = item.select_one(".price").get_text(strip=True).replace("€", "").replace(",", ".")
        price = float(price_text) if price_text else 0.0
        location = item.select_one(".location").get_text(strip=True)
        rooms_text = item.select_one(".rooms").get_text(strip=True).replace(",", ".")
        rooms = float(rooms_text) if rooms_text else 0.0
        wbs = "WBS" in item.get_text()
        link = item.select_one("a")["href"]

        listings.append({
            "title": title,
            "price": price,
            "location": location,
            "rooms": rooms,
            "wbs": wbs,
            "link": link
        })

    return listings

def filter_listings(listings):
    filtered = []
    for listing in listings:
        if (SEARCH_CRITERIA["location"].lower() in listing["location"].lower() and
            listing["price"] <= SEARCH_CRITERIA["max_price"] and
            listing["rooms"] >= SEARCH_CRITERIA["max_rooms"] and
            (listing["wbs"] == SEARCH_CRITERIA["wbs_required"] or not SEARCH_CRITERIA["wbs_required"])):
            filtered.append(listing)
    return filtered

def send_email(new_listings):
    if not new_listings:
        return

    message = EmailMessage()
    message["Subject"] = "Neue Wohnungsangebote gefunden"
    message["From"] = EMAIL_SETTINGS["sender_email"]
    message["To"] = EMAIL_SETTINGS["receiver_email"]

    content = "Folgende neue Wohnungen entsprechen Ihren Kriterien:\n\n"
    for listing in new_listings:
        content += f"{listing['title']}\n"
        content += f"Preis: {listing['price']} €\n"
        content += f"Ort: {listing['location']}\n"
        content += f"Zimmer: {listing['rooms']}\n"
        content += f"WBS erforderlich: {'Ja' if listing['wbs'] else 'Nein'}\n"
        content += f"Link: {listing['link']}\n\n"

    message.set_content(content)

    context = ssl.create_default_context()
    with smtplib.SMTP(EMAIL_SETTINGS["smtp_server"], EMAIL_SETTINGS["smtp_port"]) as server:
        server.starttls(context=context)
        server.login(EMAIL_SETTINGS["username"], EMAIL_SETTINGS["password"])
        server.send_message(message)

def open_listings_in_browser(listings):
    for listing in listings:
        webbrowser.open(listing["link"])
        time.sleep(2)  # Pause between opening tabs

# -------------------- Main Loop --------------------

def main():
    seen_listings = load_seen_listings()

    while True:
        print("Überprüfe neue Wohnungsangebote...")
        listings = fetch_listings()
        filtered = filter_listings(listings)

        new_listings = [listing for listing in filtered if listing["link"] not in seen_listings]

        if new_listings:
            print(f"{len(new_listings)} neue passende Wohnungen gefunden.")
            send_email(new_listings)
            open_listings_in_browser(new_listings)
            for listing in new_listings:
                seen_listings.add(listing["link"])
            save_seen_listings(seen_listings)
        else:
            print("Keine neuen passenden Wohnungen gefunden.")

        print(f"Warte {CHECK_INTERVAL} Sekunden bis zur nächsten Überprüfung.")
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
