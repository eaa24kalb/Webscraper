from flask import Flask, render_template, request, redirect, url_for
import pandas as pd
import requests
from google_play_scraper import search, app as google_play_app
from google_play_scraper.exceptions import ExtraHTTPError

app = Flask(__name__)

# Function to determine the price model for Google Play
def get_google_play_price_model(details):
    price = details.get("price", "")
    
    # Check if the price is an integer or float and convert it to string
    if isinstance(price, (int, float)):
        price = str(price)  # Convert to string if it's an integer or float
    
    # Check for free apps or zero-price
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
        # Scrape results in batches
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
            
            # Get price model
            price_model = get_google_play_price_model(details)
            
            # Default "Mobile", check if its available on other platforms
            app_type = "Mobile"
            if device_type == "desktop":
                # Only add apps that mention Chromebook or Android TV for desktop
                if "Chromebook" in details.get("genre", "") or "Android TV" in details.get("genre", ""):
                    app_type = "Mobile, Chromebook" if "Chromebook" in details.get("genre", "") else app_type
                    app_type = "Mobile, Android TV" if "Android TV" in details.get("genre", "") else app_type
                else:
                    continue  # Skip if the app is not for desktop
            elif device_type == "mobile" and not ("Chromebook" in details.get("genre", "") or "Android TV" in details.get("genre", "")):
                continue  # Skip non-mobile apps if 'mobile' device type is selected

            country_available = country  # Default to the passed country

            # Prepare the description to make it more readable
            description = details.get("description", "").replace('\n', '<br>')

            apps_data.append({
                "Name": details.get("title"),
                "Description": description,
                "Rating": details.get("score"),
                "Category": details.get("genre"),
                "Developer": details.get("developer"),
                "Release Date": details.get("released"),
                "Age Limit": details.get("contentRating"),
                "Country": country_available if country_available else "Not Detected",  # Ensure country is set or use fallback
                "Price Model": price_model,
                "URL": f"https://play.google.com/store/apps/details?id={app_id}",
                "Platform": "Google Play",
                "Type": app_type
            })
        
        return apps_data

    except ExtraHTTPError as e:
        print(f"Error occurred while scraping Google Play: {e}")
        return []


# Function to determine the price model for App Store
def get_app_store_price_model(app_info):
    price = app_info.get("price", 0.0)
    if price == 0.0:
        return "Free"
    elif app_info.get("isInAppPurchaseEnabled", False):
        return "Freemium"

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
            # Get the price model for the App Store app
            price_model = get_app_store_price_model(app_info)

            # Default "Mobile", check if its available on other platforms
            app_type = "Mobile" 
            if device_type == "desktop":
                # Only add macOS apps for desktop
                if 'macOS' in app_info.get("kind", ""):
                    app_type = "Desktop (macOS)"
                else:
                    continue  # Skip if the app is not for desktop
            elif device_type == "mobile" and 'macOS' in app_info.get("kind", ""):
                continue  # Skip macOS apps if 'mobile' device type is selected

            url = app_info.get("trackViewUrl", "")
            country_code = url.split("/")[3] if len(url.split("/")) > 3 else "US"  # Extract country code

            # Prepare description with paragraphs
            description = app_info.get("description", "").replace('\n', '<br>')

            apps_data.append({
                "Name": app_info.get("trackName"),
                "Description": description,
                "Rating": app_info.get("averageUserRating"),
                "Category": app_info.get("primaryGenreName"),
                "Developer": app_info.get("artistName"),
                "Release Date": app_info.get("releaseDate"),
                "Age Limit": app_info.get("contentAdvisoryRating"),
                "Country": country_code if country_code else "Not Detected",  # Ensure country is set or use fallback
                "Price Model": price_model,
                "URL": app_info.get("trackViewUrl"),
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
    keyword = request.form.get('keyword')  # Get the keyword from the form
    platform = request.form.get('platform')  # Get the selected platform
    device_type = request.form.get('device_type')  # Get the selected device type (mobile or desktop)

    # Scrape based on the selected platform and device type
    if platform == 'google_play':
        google_play_apps = scrape_google_play(keyword, max_results=500, device_type=device_type)
        app_store_apps = []  # No App Store results
    elif platform == 'app_store':
        google_play_apps = []  # No Google Play results
        app_store_apps = scrape_app_store(keyword, max_results=500, device_type=device_type)

    # Combine both datasets
    df_combined = pd.DataFrame(google_play_apps + app_store_apps)
    
    # Debugging: Print the data being passed to the template
    print("Combined Data:", df_combined.to_dict(orient='records'))

    return render_template('results.html', apps=df_combined.to_dict(orient='records'))


if __name__ == '__main__':
    app.run(debug=True, port=5003)
