# apps/accounts/constants.py
"""
Constants for user accounts including country and region mappings
"""

# List of supported countries
COUNTRIES = [
    ('nepal', 'Nepal'),
    ('india', 'India'),
    ('bangladesh', 'Bangladesh'),
    ('sri_lanka', 'Sri Lanka'),
    ('pakistan', 'Pakistan'),
    ('bhutan', 'Bhutan'),
    ('maldives', 'Maldives'),
    ('myanmar', 'Myanmar'),
    ('thailand', 'Thailand'),
    ('indonesia', 'Indonesia'),
    ('malaysia', 'Malaysia'),
    ('singapore', 'Singapore'),
    ('philippines', 'Philippines'),
    ('vietnam', 'Vietnam'),
    ('cambodia', 'Cambodia'),
    ('laos', 'Laos'),
    ('south_korea', 'South Korea'),
    ('japan', 'Japan'),
    ('china', 'China'),
    ('hong_kong', 'Hong Kong'),
    ('taiwan', 'Taiwan'),
    ('uae', 'United Arab Emirates'),
    ('saudi_arabia', 'Saudi Arabia'),
    ('qatar', 'Qatar'),
    ('kuwait', 'Kuwait'),
    ('oman', 'Oman'),
    ('bahrain', 'Bahrain'),
    ('uk', 'United Kingdom'),
    ('usa', 'United States'),
    ('canada', 'Canada'),
    ('australia', 'Australia'),
    ('new_zealand', 'New Zealand'),
    ('other', 'Other'),
]

# Country to region mapping for SubAdmin assignment
COUNTRY_TO_REGION = {
    # Nepal
    'nepal': 'Kathmandu Valley',

    # India - major regions
    'india': 'Delhi NCR',

    # Bangladesh
    'bangladesh': 'Dhaka',

    # International/Other
    'sri_lanka': 'International',
    'pakistan': 'International',
    'bhutan': 'International',
    'maldives': 'International',
    'myanmar': 'International',
    'thailand': 'International',
    'indonesia': 'International',
    'malaysia': 'International',
    'singapore': 'International',
    'philippines': 'International',
    'vietnam': 'International',
    'cambodia': 'International',
    'laos': 'International',
    'south_korea': 'International',
    'japan': 'International',
    'china': 'International',
    'hong_kong': 'International',
    'taiwan': 'International',
    'uae': 'International',
    'saudi_arabia': 'International',
    'qatar': 'International',
    'kuwait': 'International',
    'oman': 'International',
    'bahrain': 'International',
    'uk': 'International',
    'usa': 'International',
    'canada': 'International',
    'australia': 'International',
    'new_zealand': 'International',
    'other': 'International',
}

# City to region mapping (for more granular assignments)
CITY_TO_REGION = {
    # Nepal
    'Kathmandu': 'Kathmandu Valley',
    'Lalitpur': 'Kathmandu Valley',
    'Bhaktapur': 'Kathmandu Valley',
    'Pokhara': 'Pokhara',
    'Chitwan': 'Chitwan',
    'Biratnagar': 'Eastern Nepal',
    'Dharan': 'Eastern Nepal',
    'Butwal': 'Western Nepal',
    'Hetauda': 'Chitwan',
    'Janakpur': 'Eastern Nepal',

    # India
    'Delhi': 'Delhi NCR',
    'Mumbai': 'Mumbai Metropolitan',
    'Bangalore': 'Bangalore',
    'Chennai': 'Chennai',
    'Kolkata': 'Kolkata',
    'Hyderabad': 'Bangalore',
    'Pune': 'Mumbai Metropolitan',
    'Ahmedabad': 'Mumbai Metropolitan',
    'Surat': 'Mumbai Metropolitan',
    'Jaipur': 'Delhi NCR',

    # Bangladesh
    'Dhaka': 'Dhaka',
    'Chattogram': 'Dhaka',
    'Sylhet': 'Dhaka',
    'Khulna': 'Dhaka',
    'Rajshahi': 'Dhaka',
}

def get_region_for_user(country, city=None):
    """
    Determine the appropriate region for a user based on their country and city.
    NOTE: This function now returns the country directly for SubAdmin assignment.
    Region is no longer used - everything is country-based.
    """
    # Return the country directly - SubAdmins are assigned by country, not region
    return country if country else 'other'
