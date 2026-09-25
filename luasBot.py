#!/bin/python3


import requests, unicodedata
import os, time, datetime
from bs4 import BeautifulSoup
from mastodon import Mastodon
import logging
from copy import deepcopy
import re
import cloudscraper

DEBUG = False
POST = True

def file_age(filepath):
    '''Return the age of a file in seconds'''
    return time.time() - os.path.getmtime(filepath)


def split_long_lines(strings, max_length=450):
    result = []
    temp = ""

    for string in strings:
        if len(string) + len(temp) < max_length:
            temp = temp + string
        else:
            sentences = re.split(r'(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\?|\!)\s', string)
            for sentence in sentences:
                if len(sentence) + len(temp) < max_length:
                    temp = temp + ' ' + sentence
                else:
                    result.append(deepcopy(temp))
                    temp = deepcopy(sentence)
    if len(temp) > 0:
        result.append(deepcopy(temp))

    return result


def extract_update(element):
    '''Return (timestamp, sentences) from a page element or CMS HTML fragment,
    or (None, []) if no update text is found.'''
    text = element.get_text("\n", strip=True)
    lines = []
    for line in text.split("\n"):
        line = re.sub(r"\s+", " ", unicodedata.normalize("NFKD", line)).strip()
        if line:
            lines.append(line)

    joined = " ".join(lines)
    timestamp = None
    date_match = re.search(
        r"\d{1,2}[.:]\d{2}\s?(?:am|pm),?\s+\w{3,9}\.?\s+\d{1,2}(?:st|nd|rd|th)?,?\s+\w{3,9}\.?\s+\d{4}",
        joined, re.I)
    if date_match:
        timestamp = date_match.group(0)

    sentences = []
    for line in lines:
        if "kind regards" in line.lower():
            break
        if not re.search(r"red line|green line|lift|escalator", line, re.I):
            continue
        for sentence in re.split(r"(?<=[.!?])\s+", line):
            sentence = sentence.strip()
            if not sentence:
                continue
            if "kind regards" in sentence.lower():
                break
            if timestamp and sentence == timestamp:
                continue
            sentences.append(sentence)

    return timestamp, sentences


def find_update_container(soup):
    '''Locate the smallest page element containing the travel update text.'''
    marker = soup.find(string=re.compile(r"(red|green) line services", re.I))
    if marker is None:
        return None
    node = marker.parent
    while node is not None and getattr(node, "name", None) \
            and node.name not in ("body", "[document]", "html"):
        text = node.get_text(" ", strip=True)
        if re.search(r"red line", text, re.I) and re.search(r"green line", text, re.I):
            return node
        node = node.parent
    return None


def get_update_soup(scraper):
    '''Fetch the travel update, preferring the structured page data over HTML.'''
    JSON_URL = "https://www.luas.ie/page-data/travel-update/page-data.json"
    try:
        page = scraper.get(JSON_URL, timeout=30)
        if page.status_code == 200:
            modules = page.json()["result"]["data"]["datoCmsPage"]["content"]
            for module in modules:
                content = module.get("content")
                if content and re.search(r"red line|green line|lift|escalator", content, re.I):
                    logging.info("Got update from page data JSON")
                    return BeautifulSoup(content, "html.parser")
    except (ValueError, KeyError) as e:
        logging.warning("Could not use page data JSON (%s), falling back to HTML", e)
    except Exception as e:
        logging.warning("Could not fetch page data JSON (%s), falling back to HTML", e)

    URL = "https://www.luas.ie/travel-update/"
    page = scraper.get(URL, timeout=30)
    if page.status_code != 200:
        logging.error("Unexpected HTTP status %s fetching %s", page.status_code, URL)
        return None
    soup = BeautifulSoup(page.content, "html.parser")
    container = find_update_container(soup)
    if container is None:
        logging.warning("Could not locate update container in page HTML")
        return None
    logging.info("Got update from page HTML")
    return container


def main():

    global DEBUG, POST

    if DEBUG:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)
    logging.basicConfig(
        format='%(asctime)s - %(levelname)s - %(name)s - %(message)s'
        )
    logging.basicConfig(filename='app.log', filemode='w', level=logging.DEBUG)


    logging.info("Scraping luas.ie website")
    scraper = cloudscraper.create_scraper(browser={'browser': 'firefox','platform': 'linux'})
    try:
        update_soup = get_update_soup(scraper)
    except Exception as e:
        logging.error(e)
        return -1
    if update_soup is None:
        logging.error("No Luas update found - page structure may have changed")
        return -1

    timestamp, luas_update = extract_update(update_soup)
    if not luas_update:
        logging.error("No Luas update found - page structure may have changed")
        return -1

    if not timestamp:
        timestamp = datetime.datetime.now().strftime("%H:%M %a %d %b %Y")
    logging.info("Timestamp for post is: %s" % timestamp)

    header = ["Luas update at: %s.\n" % timestamp, "\n"]
    toot = []

    for line in luas_update:
        toot.append(f"{line} \n")

    if not DEBUG:
        toot.append("\n")
        toot.append("#Luas #Dublin\n")

    logging.debug("Toot prepared: \n%s" % toot)

    # Normalise newlines, etc.
    with open("temp_file", "w") as f:
        f.writelines(toot)
    with open("temp_file", "r", encoding="utf-8") as f:
        toot = f.readlines()
    os.remove("temp_file")


    if os.path.exists("toot.text"):
        with open("toot.text", "r") as f:
            old_toot = f.readlines()
            if old_toot == toot:
                if (file_age("toot.text") > 86400
                    and datetime.datetime.now().hour == 9
                    and datetime.datetime.now().minute < 10
                ):
                    logging.info("No update, but doing daily post")
                else:
                    logging.info("No update found")
                    if not DEBUG:
                        return


    with open("toot.text", "w") as f:
        f.writelines(toot)

    toot[:0] = header

    # Quick fix to handle updates with more than 500 characters
    if sum(len(i) for i in toot) > 500:
        long_output = split_long_lines(toot)


    if POST:
        logging.info("Posting to Mastodon")
        mastodon = Mastodon(
            access_token=os.environ.get('mastodon_token'),
            api_base_url="https://mastodon.ie/"
        )
        try:
            if 'long_output' in locals():
                response = mastodon.status_post(''.join(long_output[0]))
                # Each subsequent reply, is a reply to the previous toot
                for entry in long_output[1:]:
                    if len(entry) > 1:
                        response = mastodon.status_post(''.join(entry),in_reply_to_id=response['id'])

            else:
                mastodon.status_post(''.join(toot) )
        except Exception as e:
            logging.error(e)
            return -1


    return None


if __name__ == "__main__":
   main()
