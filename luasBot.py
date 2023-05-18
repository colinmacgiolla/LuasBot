#!/bin/python3


import requests, unicodedata
import os
from bs4 import BeautifulSoup
from mastodon import Mastodon
import logging

DEBUG = False
POST = True

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
    URL = "https://luas.ie/travel-updates/"
    try:
        page = requests.get(URL)
    except Exception as e:
        logging.error(e)
        return -1

    soup = BeautifulSoup(page.content, "html.parser")
    results = soup.find_all("div", class_="page-content")

    data = results[0].text.split("\n")

    logging.debug("Extracted the following data:\n%s" % data)
    # timestamp = next(datefinder.find_dates(results[0].text))
    timestamp = data[5]
    logging.info("Timestamp from post is: %s" % timestamp)

    luas_update = []
    for line in data:
        if "Red" in line or "Green" in line:
            luas_update.append( unicodedata.normalize("NFKD", line) )

    header = ["Luas update at: %s.\n" % timestamp, "\n"]
    toot = []
    
    for line in luas_update:
        for sentence in line.split("."):
            if "Kind Regards" in sentence:
                break

            if "Green" in sentence or "lift" in sentence:
                temp = toot[-1]
                toot[-1] = temp+"\n"

            toot.append(f"{sentence.strip()}.")

    if not DEBUG:
        # Avoid spamming people subscribing to tags while I'm testing
        toot.append("\n")
        toot.append("\n")
        toot.append("#Luas #Dublin #MastoDaoine")

    logging.debug("Toot prepared: \n%s" % toot)


    if os.path.exists("toot.text"):
        with open("toot.text", "r") as f:
            old_toot = f.readlines()
            if old_toot == toot:
                logging.info("No update found")
                return

    with open("toot.text", "w") as f:
        f.writelines(toot)
        
    toot[:0] = header

    if POST:
        logging.info("Posting to Mastodon")
        mastodon = Mastodon(
            access_token=os.environ.get('mastodon_token'),
            api_base_url="https://botsin.space/"
        )
        try:
            mastodon.status_post(''.join(toot) )
        except Exception as e:
            logging.error(e)
            return -1


    return None


if __name__ == "__main__":
   main()
