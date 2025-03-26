import requests
from google_play_scraper import apps  # Updated to use `apps` instead of `search`
import pandas as pd
from google_play_scraper.exceptions import ExtraHTTPError


# Function to determine the price model for Google Play
def get_google_play_price_model(details):
    price = details.get("price", "")
    
    if isinstance(price, (int, float)):
        price = str(price)
    
    if isinstance(price, str) and "free" in price.lower():
        return "Free"
    elif price == "0" or price == "0.0":
        return "Free"
    else:
        return "Paid"


# Google Play Scraping
def scrape_google_play(keyword, max_results=500, country="US"):
    all_results = []
    start = 0  
    batch_size = 50 

    try:
        if not keyword:
            raise ValueError("Keyword cannot be empty")
        
        # Scraping in batches
        while len(all_results) < max_results:
            # Use the `apps()` method directly to get app details
            results = apps(keyword, lang="en", country=country, num=max_results)  # Fetch apps using keyword
            if not results:
                break
            
            all_results.extend(results)
            start += batch_size  
            
            if len(results) < batch_size:
                break  

    except ExtraHTTPError as e:
        print(f"Error occurred while scraping Google Play: {str(e)}")
        return []
    except ValueError as e:
        print(str(e))
        return []

    apps_data = []
    for app_info in all_results[:max_results]:
        app_id = app_info["appId"]
        try:
            details = apps(app_id, lang="en", country=country)  # Use apps() to fetch detailed app data
        except ExtraHTTPError as e:
            print(f"Error fetching details for app {app_id}: {str(e)}")
            continue  
        
        # Get price model
        price_model = get_google_play_price_model(details)
        
        # Dynamically set the country value if available
        country_available = country

        # Default "Mobile"
        app_type = "Mobile"

        # Check if the app is available on Chromebook or Android TV
        if "Chromebook" in details.get("genre", ""):
            app_type = "Mobile, Desktop (Chromebook)"
        elif "Android TV" in details.get("genre", ""):
            app_type = "Mobile, Android TV"
        
        description = details.get("description", "").replace('\n', '<br>')

        apps_data.append({
            "Name": details.get("title"),
            "Description": description,
            "Rating": details.get("score"),
            "Category": details.get("genre"),
            "Developer": details.get("developer"),
            "Release Date": details.get("released", "Not Available"),
            "Age Limit": details.get("contentRating", "Not Available"),
            "Country": country_available,
            "Platform": "Google Play",
            "Type": app_type,
            "Price Model": price_model,
            "URL": f"https://play.google.com/store/apps/details?id={app_id}"
        })

    return apps_data


# Function to determine the price model for App Store
def get_app_store_price_model(app_info):
    price = app_info.get("price", 0.0)
    if price == 0.0:
        return "Free"
    elif app_info.get("isInAppPurchaseEnabled", False):
        return "Freemium"
    else:
        return "Premium"


# App Store Scraping
def scrape_app_store(keyword, max_results=500, country="US"):
    all_results = []
    offset = 0

    try:
        if not keyword:
            raise ValueError("Keyword cannot be empty")
        
        while len(all_results) < max_results:
            url = f"https://itunes.apple.com/search?term={keyword}&entity=software&limit=50&offset={offset}&country={country}"
            response = requests.get(url)
            data = response.json()

            if "results" not in data or not data["results"]:
                break  # Exit if no results are found

            all_results.extend(data["results"])
            offset += 50

    except requests.exceptions.RequestException as e:
        print(f"Error occurred while scraping App Store: {str(e)}")
        return []
    except ValueError as e:
        print(str(e))
        return []

    apps_data = []
    for app_info in all_results[:max_results]:
        try:
            price_model = get_app_store_price_model(app_info)
            
            url = app_info.get("trackViewUrl", "")
            country_code = url.split("/")[3] if len(url.split("/")) > 3 else "US"  # Extract country code
            
            # Check for platform types in App Store
            if 'Mac' in app_info.get("kind", ""):
                app_type = "Desktop (macOS)"
            
            # Check if both iPhone and Mac are supported
            if 'iPhone' in app_info.get("supportedDevices", []) and 'Mac' in app_info.get("supportedDevices", []):
                app_type = "Mobile, Desktop (macOS)"
            
            description = app_info.get("description", "").replace('\n', '<br>')

            apps_data.append({
                "Name": app_info.get("trackName"),
                "Description": description,
                "Rating": app_info.get("averageUserRating"),
                "Category": app_info.get("primaryGenreName"),
                "Developer": app_info.get("artistName"),
                "Release Date": app_info.get("releaseDate"),
                "Age Limit": app_info.get("contentAdvisoryRating"),
                "Country": country_code, 
                "Platform": "App Store",
                "Type": app_type,
                "Price Model": price_model,
                "URL": app_info.get("trackViewUrl", "#")
            })
        
        except KeyError as e:
            print(f"Error processing app: {e}")
            continue  

    return apps_data


# Example: Search for "therapeutic AI" apps
keyword = "therapeutic AI"

# Scrape Google Play and App Store
google_play_apps = scrape_google_play(keyword, max_results=500)
app_store_apps = scrape_app_store(keyword, max_results=500)

# Combine both datasets
df_combined = pd.DataFrame(google_play_apps + app_store_apps)

# Sort the combined DataFrame alphabetically by 'Name'
df_combined_sorted = df_combined.sort_values(by="Name", ascending=True)

# Save to CSV (sorted)
df_combined_sorted.to_csv("therapeutic_ai_apps_combined_sorted.csv", index=False)

print("✅ Both Google Play and App Store data saved successfully (sorted by name)!")

# Analyzing the Data    -->  Load the sorted combined CSV file
df_combined_sorted = pd.read_csv("therapeutic_ai_apps_combined_sorted.csv")

# Distribution of Ratings
rating_distribution = df_combined_sorted['Rating'].value_counts()

# Count of Apps by Category
category_distribution = df_combined_sorted['Category'].value_counts()

# Display the analysis
print("\n✅ Rating distribution:")
print(rating_distribution)

print("\n✅ Category distribution:")
print(category_distribution)
