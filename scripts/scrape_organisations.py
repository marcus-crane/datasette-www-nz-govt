import os

from bs4 import BeautifulSoup
import requests
from slugify import slugify
from sqlite_utils import Database

GOVT_ORG_DIRECTORY_URL = "https://www.govt.nz/organisations/"

db = Database("nz_government_v1.db", recreate=True)

db["organisations"].create({
    "id": str,
    "name": str,
    "name_secondary": str,
    "freephone": str,
    "phone": str,
    "email": str,
    "website": str,
    "contact_page": str,
    "last_modified": str,
    "address_physical_extended": str,
    "address_physical_street": str,
    "address_physical_locality": str,
    "address_physical_postcode": str,
    "address_physical_country": str,
    "address_postal_extended": str,
    "address_postal_street": str,
    "address_postal_locality": str,
    "address_postal_postcode": str,
    "address_postal_country": str,
    "sector": str,
    "parent_id": str,
}, pk="id", if_not_exists=True)

db["roles"].create({
    "id": str,
    "name": str,
}, pk="id", if_not_exists=True)

db["people"].create({
    "id": str,
    "honorific": str,
    "name": str,
    "is_minister": bool,
}, pk="id", if_not_exists=True)

# Could be migrated to a container in the pipeline but I had trouble getting this to work so for now,
# I'll just be hosting some infrastructure in the background to use instead
browserless_api_token = os.environ.get("BROWSERLESS_API_TOKEN", False)
if not browserless_api_token:
    print("Please set BROWSERLESS_API_TOKEN env var")
    os.exit(1)

scrape_url = os.environ.get("BROWSERLESS_URL", False)
if not scrape_url:
    print("Please set BROWSERLESS_URL env var")
    os.exit(1)

scrape_params = {"token": browserless_api_token, "stealth": True}

r = requests.post(scrape_url, params=scrape_params, json={"url": GOVT_ORG_DIRECTORY_URL})
soup = BeautifulSoup(r.text, "html.parser")
links = soup.find_all("a", class_="ga-track-org-filter-topic")
unique_links = list(set([link.attrs['href'] for link in links]))

unique_links.sort()

def parse_address(soup, header):
    address_header_el = soup.find("dt", class_="address-type", string=header)
    address_extended = ""
    address_street = ""
    address_locality = ""
    address_postcode = ""
    address_country = ""
    if address_header_el is not None:
        address_el = address_header_el.next_sibling.next_sibling

        address_extended_bits = address_el.find_all("span", class_="extended_address")
        if address_extended_bits is not None:
            # Some organisations have more than one extended address so we just collapse them down.
            # They aren't currently used for anything programmatic (ie; geocoding)
            address_extended = ' '.join([x.get_text(strip=True) for x in address_extended_bits])
        address_street_bits = address_el.find("span", class_="street-address")
        if address_street_bits is not None:
            address_street = ' '.join([x.get_text(strip=True) for x in address_street_bits])
        address_locality_bits = address_el.find("span", class_="locality")
        if address_locality_bits is not None:
            address_locality = ' '.join([x.get_text(strip=True) for x in address_locality_bits])
        address_postcode_bits = address_el.find("span", class_="postal-code")
        if address_postcode_bits is not None:
            address_postcode = ' '.join([x.get_text(strip=True) for x in address_postcode_bits])
        address_country_bits = address_el.find("span", class_="country-name")
        if address_country_bits is not None:
            address_country = ' '.join([x.get_text(strip=True) for x in address_country_bits])

    return {
        'extended': address_extended,
        'street': address_street,
        'locality': address_locality,
        'postcode': address_postcode,
        'country': address_country
    }

for link in unique_links[0:5]:
    print(f"-- {link}")
    url = f"https://www.govt.nz/{link}"
    r = requests.post(scrape_url, params=scrape_params, json={"url": url})
    soup = BeautifulSoup(r.text, 'html.parser')

    _id = link.replace("organisations/", "").replace("/", "")

    name = soup.find('h1', id='toplink').get_text(strip=True)

    name_secondary_el = soup.find('p', class_='preferred-secondary-name')
    name_secondary = None
    if name_secondary_el is not None:
        name_secondary = name_secondary_el.get_text(strip=True)

    freephone_el = soup.find('a', attrs={'data-type': 'Freephone'})
    freephone = None
    if freephone_el is not None:
        freephone = freephone_el.get_text(strip=True).replace(' ', '')

    phone_el = soup.find('a', attrs={'data-type': 'Phone'})
    phone = None
    if phone_el is not None:
        phone = phone_el.get_text(strip=True).replace(' ', '')

    email_el = soup.find('a', attrs={'data-type': 'email'})
    email = None
    if email_el is not None:
        email = email_el.get_text(strip=True)

    website_el = soup.find('a', class_='org-contact-card__link--website')
    website = None
    if website_el is not None:
        website = website_el.attrs['href']

    contact_page_el = soup.find('a', attrs={'data-type': 'contactpage'})
    contact_page = None
    if contact_page_el is not None:
        contact_page = contact_page_el.attrs['href']
    
    physical_address = parse_address(soup, header="Street address:")
    postal_address = parse_address(soup, header="Postal address:")
    
    last_modified = soup.find("div", class_="PageLastUpdatedPageFeature").time.attrs['datetime']

    sector_el = soup.find("div", class_="org-sector")
    sector = None
    if sector_el:
        sector = sector_el.h2.next_sibling.strip()
    
    parent_id = None
    parent_org_el = soup.find("a", id="parent-org")
    if parent_org_el is not None:
        parent_id = parent_org_el.attrs['href'].replace("organisations/", "").replace("/", "")

    org = db["organisations"].upsert({
        "id": _id,
        "name": name,
        "name_secondary": name_secondary,
        "freephone": freephone,
        "phone": phone,
        "email": email,
        "website": website,
        "contact_page": contact_page,
        "last_modified": last_modified,
        "address_physical_extended": physical_address['extended'],
        "address_physical_street": physical_address['street'],
        "address_physical_locality": physical_address['locality'],
        "address_physical_postcode": physical_address['postcode'],
        "address_physical_country": physical_address['country'],
        "address_postal_extended": postal_address['extended'],
        "address_postal_street": postal_address['street'],
        "address_postal_locality": postal_address['locality'],
        "address_postal_postcode": postal_address['postcode'],
        "address_postal_country": postal_address['country'],
        "sector": sector,
        "parent_id": parent_id
    }, pk="id")
    
    people_list = soup.find_all("li", class_="org-role-person")
    for person in people_list:
        name_el = person.find("p", class_="person-name")
        _person_id = slugify(name_el.get_text(strip=True))
        name = name_el.span.get_text(strip=True)
        honorific = None
        is_minister = 'org-role-person--minister' in person.attrs['class']
        # Honorifics don't have a specific element to grab onto
        if len(name_el.contents) == 2:
            honorific = name_el.contents[0].get_text(strip=True)

        db["people"].upsert({
            "id": _person_id,
            "honorific": honorific,
            "name": name,
            "is_minister": is_minister
        }, pk="id").m2m("organisations", lookup={"id": _id})

        role_list = person.find_all("p", class_="person-role")
        for role in role_list:
            # HOTFIX: At least one role can be empty
            if role:
                db["roles"].upsert({
                    "id": slugify(role.get_text(strip=True)),
                    "name": role.get_text(strip=True)
                }, pk="id").m2m("people", lookup={"id": _person_id}).m2m("organisations", lookup={"id": _id})