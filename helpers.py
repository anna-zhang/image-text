import requests
import os
from tqdm import tqdm
from bs4 import BeautifulSoup as bs
from urllib.parse import urljoin, urlparse

# Reference: https://github.com/x4nth055/pythoncode-tutorials/tree/master/web-scraping/download-images

def is_valid(url):
    # Check to make sure the url is valid
    parsed = urlparse(url)
    return bool(parsed.netloc) and bool(parsed.scheme)

def check_alt_text(text):
    alt_text = text.lower()
    # Check alt text
    if (alt_text == None):
        # Images with no alt text
        return "no_alt"
    elif (alt_text == ""):
        # Images with empty string as alt text (could be decorative image)
        return "possible_decorative"
    elif (alt_text.endswith(".jpg") or alt_text.endswith(".jpeg") or alt_text.endswith(".gif") or alt_text.endswith(".png") or alt_text.endswith(".svg") or alt_text.endswith(".webp")):
        # Images whose alt text ends with a file extension (flag warning)
        return "includes_extension"
    elif ((alt_text.find("image") > -1) or (alt_text.find("photo") > -1) or (alt_text.find("graphic") > -1) or (alt_text.find("photograph") > -1) or (alt_text.find("picture") > -1)):
        # Images whose alt text includes "image", "photo", "graphic", "photograph", "picture" (flag warning)
        return "includes_type"
    else:
        # No warnings detected
        return "OK"

def get_all_images(url):
    # Return all image URLS on that website url
    soup = bs(requests.get(url).content, "html.parser")
    images = []
    for img in tqdm(soup.find_all("img"), "Extracting images"):
        img_url = img.attrs.get("src")
        if not img_url:
            # if img does not contain src attribute, just skip
            continue
        # make the URL absolute by joining domain with the URL that is just extracted
        img_url = urljoin(url, img_url)
        # remove URLs like '/hsts-pixel.gif?c=3.2.5'
        try:
            pos = img_url.index("?")
            img_url = img_url[:pos]
        except ValueError:
            pass
        # finally, if the url is valid
        if is_valid(img_url):
            # check alt text
            img_alt = img.attrs.get("alt")
            print(check_alt_text(img_alt))
            if (check_alt_text(img_alt) != "OK"):
                # found potential issues with alt text
                image_details = {}
                image_details["url"] = img_url
                image_details["alt"] = img_alt
                images.append(image_details)
    return images

