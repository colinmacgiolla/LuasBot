#!/bin/python3


import requests, unicodedata
import os
from bs4 import BeautifulSoup
from mastodon import Mastodon


DEBUG = True


def main():
    
    global DEBUG
    
    URL = "https://luas.ie/travel-updates/"
    page = requests.get(URL)
    
    soup = BeautifulSoup(page.content, "html.parser")
    results = soup.find_all("div", class_="page-content")
  
    data = results[0].text.split("\n")
    
    # timestamp = next(datefinder.find_dates(results[0].text))
    timestamp = data[5]
    
    luas_update = []
    for line in data:
        if "Red" in line or "Green" in line:
            luas_update.append( unicodedata.normalize("NFKD", line) )

    toot = ["Luas update at: %s.\n\n" % timestamp]
    #print(f"Luas update at {timestamp}\n")

    for line in luas_update:
        for sentence in line.split("."):
            if "Green" in sentence or "lift" in sentence:
                #print("\n")
                toot.append("\n")
            if "Kind Regards" in sentence:
                break
            #print(f"{sentence.strip()}. ", end="")
            toot.append(f"{sentence.strip()}. ")
    
    if not DEBUG:
        # Avoid spamming people subscribing to tags while I'm testing
        toot.append("\n\n")
        toot.append("#Luas #Dublin #MastaDaoine")
            
    #print("\n")
    
    mastodon = Mastodon(
        access_token=os.environ.get('secret.mastodon_token'),
        api_base_url="https://botsin.space/"
    )
    mastodon.status_post(''.join(toot) )
    
    
    return None



if __name__ == "__main__":
   main()