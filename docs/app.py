from flask import Flask, render_template, request, jsonify
import folium
import geopandas as gpd
import pandas as pd
import re

landlord_info = pd.read_pickle('landlord_info.pkl')

def standardize_address(address):
    """Standardizes an address for use in Google Maps."""
    address = re.sub(r'\s+', ' ', address).strip()
    unit_match = re.search(r"(?:Unit|#|Apt)\s*(\d+)", address, re.IGNORECASE)
    if unit_match:
        unit_num = unit_match.group(1)
        address = re.sub(r"(?:Unit|#|Apt)\s*\d+", f"Unit {unit_num}", address, flags=re.IGNORECASE)
    address = re.sub(r",\s*(MA|Massachusetts)", ", MA", address, flags=re.IGNORECASE)
    address = re.sub(r",\s*,", ",", address)
    return address

# Assuming you have 'gdf' (GeoDataFrame) already loaded

# Apply the function to the 'UNIT_ADDRESS' column
gdf['UNIT_ADDRESS_GMAPS'] = gdf['UNIT_ADDRESS'].apply(standardize_address)


# Widget and interaction code
address_options = gdf['UNIT_ADDRESS_GMAPS'].unique().tolist()
user_address_input = widgets.Combobox(
    placeholder='Enter a street address',
    options=address_options,
    description='Address:',
    ensure_options=True
)

def display_addresses_on_map(addresses):
    """Loads the given addresses on a Folium map with markers."""
    if addresses:
        center_location = gdf[gdf['UNIT_ADDRESS_GMAPS'] == addresses[0]]['geometry'].iloc[0]
        # Convert center_location to EPSG:4326 for Folium
        # Create a GeoSeries to apply to_crs
        center_location_geoseries = gpd.GeoSeries(center_location, crs=gdf.crs)  
        center_location_4326 = center_location_geoseries.to_crs("EPSG:4326").iloc[0]  # Get the Point
        m = folium.Map(location=[center_location_4326.y, center_location_4326.x], zoom_start=13)
    else:
        m = folium.Map(location=[42.3601, -71.0589], zoom_start=10)  # Default to Boston
    for address in addresses:
        geometry = gdf[gdf['UNIT_ADDRESS_GMAPS'] == address]['geometry'].iloc[0]
        # Convert geometry to EPSG:4326 for Folium
        # Create a GeoSeries to apply to_crs
        geometry_geoseries = gpd.GeoSeries(geometry, crs=gdf.crs) 
        geometry_4326 = geometry_geoseries.to_crs("EPSG:4326").iloc[0]  # Get the Point
        html = f"""
            <b>Address:</b> {address}<br>
        """
        iframe = folium.IFrame(html, width=200, height=50)
        popup = folium.Popup(iframe, max_width=2650)
        folium.Marker(
            location=[geometry_4326.y, geometry_4326.x],  # Use converted coordinates
            popup=popup,
            icon=folium.Icon(color='blue')
        ).add_to(m)
    display(m)

def find_matching_addresses(user_input_address):
    """
    Finds addresses with the same owner or owner address as the input address,
    displays the owner name, and loads them on a map.
    """
    standardized_user_input = standardize_address(user_input_address)
    matching_rows = gdf[gdf['UNIT_ADDRESS_GMAPS'] == standardized_user_input]

    if matching_rows.empty:
        print(f"No address found matching '{user_input_address}'.")
        return

    owner = matching_rows['OWNER'].iloc[0]
    owner_address = matching_rows['OWNER_ADDRESS'].iloc[0]
    owner_name = matching_rows['OWNER'].iloc[0] 

    # Define other_addresses here
    other_addresses = gdf[
        ((gdf['OWNER'] == owner) | (gdf['OWNER_ADDRESS'] == owner_address))
        & (gdf['UNIT_ADDRESS_GMAPS'] != standardized_user_input)
    ]['UNIT_ADDRESS_GMAPS'].unique()

    if len(other_addresses) > 0:
        print(f"Owner Name: {owner_name}")
        print(f"Addresses with same landlord as '{user_input_address}':")
        for address in other_addresses:
            print(address)
        display_addresses_on_map(other_addresses.tolist())
    else:
        print(f"No other addresses found associated with '{user_input_address}'.")

def on_button_clicked(b):
    user_address = user_address_input.value
    find_matching_addresses(user_address)

button = widgets.Button(description="Search")
button.on_click(on_button_clicked)

# Display the widgets
display(user_address_input, button)

# --- Flask App Setup ---
app = Flask(__name__)


@app.route('/')
def index():
    """Renders the HTML template for the address search form."""
    address_options = gdf['UNIT_ADDRESS_GMAPS'].unique().tolist()
    return render_template('index.html', address_options=address_options)


@app.route('/map', methods=['POST'])
def show_map():
    """Handles address search and returns the map HTML."""
    user_address = request.form.get('address')
    
    # Get matching addresses using find_matching_addresses function
    other_addresses = find_matching_addresses_for_web(user_address)

    # Create and return the Folium map as HTML
    m = display_addresses_on_map_for_web(other_addresses)
    return m._repr_html_()  # Return map's HTML


def find_matching_addresses_for_web(user_input_address):
    """
    Finds addresses with the same owner or owner address as the input address
    for the web application. 
    """
    standardized_user_input = standardize_address(user_input_address)
    matching_rows = gdf[gdf['UNIT_ADDRESS_GMAPS'] == standardized_user_input]

    if matching_rows.empty:
        # Handle case where no address is found (e.g., return an error message)
        return []  # Or a suitable error response

    owner = matching_rows['OWNER'].iloc[0]
    owner_address = matching_rows['OWNER_ADDRESS'].iloc[0]

    # Find other addresses with the same owner or owner address
    other_addresses = gdf[
        ((gdf['OWNER'] == owner) | (gdf['OWNER_ADDRESS'] == owner_address))
        & (gdf['UNIT_ADDRESS_GMAPS'] != standardized_user_input)
    ]['UNIT_ADDRESS_GMAPS'].unique().tolist()

    return other_addresses


def display_addresses_on_map_for_web(addresses):
    """
    Loads the given addresses on a Folium map for the web application.
    """
    if addresses:
        center_location = gdf[gdf['UNIT_ADDRESS_GMAPS'] == addresses[0]]['geometry'].iloc[0]
        # Convert center_location to EPSG:4326 for Folium
        # Create a GeoSeries to apply to_crs
        center_location_geoseries = gpd.GeoSeries(center_location, crs=gdf.crs)  
        center_location_4326 = center_location_geoseries.to_crs("EPSG:4326").iloc[0]  # Get the Point
        m = folium.Map(location=[center_location_4326.y, center_location_4326.x], zoom_start=13)

        for address in addresses:
            geometry = gdf[gdf['UNIT_ADDRESS_GMAPS'] == address]['geometry'].iloc[0]
            # Convert geometry to EPSG:4326 for Folium
            # Create a GeoSeries to apply to_crs
            geometry_geoseries = gpd.GeoSeries(geometry, crs=gdf.crs) 
            geometry_4326 = geometry_geoseries.to_crs("EPSG:4326").iloc[0]  # Get the Point
            html = f"""
                <b>Address:</b> {address}<br>
            """
            iframe = folium.IFrame(html, width=200, height=50)
            popup = folium.Popup(iframe, max_width=2650)
            folium.Marker(
                location=[geometry_4326.y, geometry_4326.x],  # Use converted coordinates
                popup=popup,
                icon=folium.Icon(color='blue')
            ).add_to(m)
    else:
        # Default to Boston if no addresses are provided
        m = folium.Map(location=[42.3601, -71.0589], zoom_start=10) 
    return m  # Return the Folium map object


if __name__ == '__main__':
    app.run(debug=True)
