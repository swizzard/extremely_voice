import json
import logging
import re
import time
import sys

import requests
from twython import Twython


def rand_urls():
    rand_url = 'https://en.wikipedia.org/wiki/Special:Random'
    rest_root = 'http://rest.wikimedia.org/en.wikipedia.org/v1/page/summary/{}'
    while True:
        req = requests.head(rand_url, allow_redirects=True)
        topic = req.url.split('/')[-1]
        yield rest_root.format(topic)


def get_summary(url):
    req = requests.get(url)
    try:
        req.raise_for_status()
    except requests.exceptions.HTTPError as e:
        logging.exception(e.message)
        pass
    else:
        return {k:v for k,v in req.json().iteritems() if k in
                ('extract', 'title')}


def assemble_tweet(summary):
    s = "*extremely {title} voice*\nI'm {desc}"
    clean_title = re.sub(r' \(.*?\)', '', summary['title'])
    match = re.match(r'.*?is (.*?\.)', summary['extract'])
    if match is not None:
        return s.format(title=clean_title, desc=match.group(1))


def tweets():
    for url in rand_urls():
        try:
            t = assemble_tweet(get_summary(url))
        except Exception as e:
            logging.exception(e.message)
        else:
            if t is not None and len(t) <= 140:
                yield t


def get_client(cfg_path):
    with open(cfg_path) as cfg_fil:
        cfg = json.load(cfg_fil)
    return Twython(app_key=cfg['consumer_key'],
                   app_secret=cfg['consumer_secret'],
                   oauth_token=cfg['token'],
                   oauth_token_secret=cfg['secret'])


if __name__ == '__main__':
    logging.basicConfig(filename='extremely_voice.log', level=logging.DEBUG)
    path = sys.argv[1]
    client = get_client(path)
    for tweet in tweets():
        try:
            client.update_status(status=tweet)
        except Exception as e:
            logging.exception(e.message)
        else:
            time.sleep(1800)

