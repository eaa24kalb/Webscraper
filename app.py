from flask import Flask, render_template, request, redirect, url_for
import pandas as pd
import requests
from google_play_scraper import app as google_play_app
from google_play_scraper.exceptions import ExtraHTTPError

app = Flask(__name__)

# Function to determine the price model for Google Play
def get_google_play_price_model(details):
    price = details.get("price", "")
    
    if isinstance(price, (int, float)):
        price = str(price)  # Convert to string if it's an integer or float
    
    if isinstance(price, str) and "free" in price.lower():
        return "Free"
    elif price == "0" or price == "0.0":
        return "Free"  # Explicitly handle the case where the price is 0
    else:
        return "Paid"


# Google Play Scraping Function with error handling
def scrape_google_play(keyword, max_results=500, country="US", device_type="mobile"):
    if not keyword:
        print("Keyword cannot be empty.")
        return []

    all_results = []
    try:
        results = search(keyword, lang="en", country=country)
        all_results.extend(results[:max_results])

        apps_data = []
        for app_info in all_results:
            app_id = app_info["appId"]
            try:
                details = google_play_app(app_id) 
            except ExtraHTTPError as e:
                print(f"Error fetching details for app {app_id}: {e}")
                continue  # Skip if there's an error fetching details for this app
            
            price_model = get_google_play_price_model(details)
            app_type = "Mobile"

            if device_type == "desktop":
                app_type_parts = []
                if "Chromebook" in details.get("genre", ""):
                    app_type_parts.append("Mobile, Chromebook")
                if "Android TV" in details.get("genre", ""):
                    app_type_parts.append("Mobile, Android TV")

                if app_type_parts:
                    app_type = ", ".join(app_type_parts)
                else:
                    continue

            elif device_type == "mobile" and not ("Chromebook" in details.get("genre", "") or "Android TV" in details.get("genre", "")):
                continue

            country_available = country  
            description = details.get("description", "").replace('\n', '<br>')

            apps_data.append({
                "Name": details.get("title"),
                "Description": description,
                "Rating": details.get("score", "No Rating"),
                "Category": details.get("genre", "Unknown"),
                "Developer": details.get("developer", "Unknown"),
                "Release Date": details.get("released", "Not Available"),
                "Age Limit": details.get("contentRating", "Not Available"),
                "Country": country_available if country_available else "Not Detected",
                "Price Model": price_model,
                "URL": f"https://play.google.com/store/apps/details?id={app_id}",
                "Platform": "Google Play",
                "Type": app_type
            })
        
        return apps_data
    except ExtraHTTPError as e:
        print(f"Error occurred while scraping Google Play: {e}")
        return []


# App Store Scraping Function with error handling
def scrape_app_store(keyword, max_results=500, country="US", device_type="mobile"):
    if not keyword:
        print("Keyword cannot be empty.")
        return []

    url = f"https://itunes.apple.com/search?term={keyword}&entity=software&limit={max_results}&country={country}"
    
    try:
        response = requests.get(url)
        data = response.json()

        apps_data = []
        for app_info in data.get("results", []):
            price_model = "Free" if app_info.get("price", 0.0) == 0.0 else "Freemium"
            app_type = "Mobile"

            if device_type == "desktop":
                app_type_parts = []
                if 'macOS' in app_info.get("kind", ""):
                    app_type_parts.append("Mobile, Desktop (macOS)")
                if 'iOS' in app_info.get("kind", ""):
                    app_type_parts.append("Mobile")

                if app_type_parts:
                    app_type = ", ".join(app_type_parts)
                else:
                    continue
            elif device_type == "mobile" and 'macOS' in app_info.get("kind", ""):
                continue

            url = app_info.get("trackViewUrl", "")
            country_code = url.split("/")[3] if len(url.split("/")) > 3 else "US"

            description = app_info.get("description", "").replace('\n', '<br>')

            apps_data.append({
                "Name": app_info.get("trackName"),
                "Description": description,
                "Rating": app_info.get("averageUserRating", "No Rating"),
                "Category": app_info.get("primaryGenreName", "Unknown"),
                "Developer": app_info.get("artistName", "Unknown"),
                "Release Date": app_info.get("releaseDate", "Not Available"),
                "Age Limit": app_info.get("contentAdvisoryRating", "Not Available"),
                "Country": country_code if country_code else "Not Detected",
                "Price Model": price_model,
                "URL": app_info.get("trackViewUrl", "#"),
                "Platform": "App Store",
                "Type": app_type
            })

        return apps_data
    except requests.exceptions.RequestException as e:
        print(f"Error occurred while scraping the App Store: {e}")
        return []


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/search', methods=['POST'])
def search_apps():
    keyword = request.form.get('keyword')
    platform = request.form.get('platform')
    device_type = request.form.get('device_type')

    google_play_apps, app_store_apps = [], []

    # Scraping data based on platform and device type
    if platform == 'google_play':
        google_play_apps = scrape_google_play(keyword, max_results=500, device_type=device_type)
    elif platform == 'app_store':
        app_store_apps = scrape_app_store(keyword, max_results=500, device_type=device_type)

    # Combine the results
    all_apps = google_play_apps + app_store_apps

    # Convert to DataFrame and sort by "Name"
    df_combined = pd.DataFrame(all_apps)
    df_combined_sorted = df_combined.sort_values(by="Name", ascending=True)

    print("Combined Data:", df_combined_sorted.to_dict(orient='records'))  # Debugging log

    # Return sorted apps to the results page
    return render_template('results.html', apps=df_combined_sorted.to_dict(orient='records'))


if __name__ == '__main__':
    app.run(debug=True, port=5003)
