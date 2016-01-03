import json
import logging
import os
import re
import time
import random
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
    else:
        js = req.json()
        out = {'extract': js['extract'], 'title': js['title']}
        thumbnail = js.get('thumbnail')
        if thumbnail is not None:
            out['thumbnail'] = thumbnail['source']
        return out


def get_image(img_url, client):
    req = requests.get(img_url, stream=True)
    try:
        req.raise_for_status()
    except requests.exceptions.HTTPError as e:
        logging.exception(e.message)
    else:
        with open('image', 'wb') as img_file:
            for chunk in req:
                img_file.write(chunk)
        with open('image', 'rb') as img_file:
            try:
                resp = client.upload_media(media=img_file)
            except Exception as e:
                logging.exception(e.message)
            else:
                return resp['media_id']
        os.remove('image')


def clean_title(title):
    return re.sub(r' \(.*?\)', '', title)


def assemble_text_tweet(summary):
    s = "*extremely {title} voice*\nI'm {desc}"
    title = clean_title(summary['title'])
    match = re.match(r'.*?\bis (.*?\.)', summary['extract'])
    if match is not None:
        return {'status': s.format(title=title, desc=match.group(1))}


def assemble_img_tweet(summary, client):
    s = "*extremely {title} voice*\nit me\n"
    media_id = get_image(summary['thumbnail'], client)
    if media_id is not None:
        title = clean_title(summary['title'])
        return {'status': s.format(title=title), 'media_ids': [media_id]} 


def tweets(client):
    for url in rand_urls():
        summary = get_summary(url)
        if summary is not None:
            thumb = summary.get('thumbnail')
            try:
                if thumb is not None and random.random() > 0.0:
                    t = assemble_img_tweet(summary, client)
                else:
                    t = assemble_text_tweet(summary)
            except Exception as e:
                logging.exception(e.message)
            else:
                if t is not None and len(t['status']) <= 140:
                    yield t


def get_client(cfg_path):
    with open(cfg_path) as cfg_fil:
        cfg = json.load(cfg_fil)
    return Twython(app_key=cfg['consumer_key'],
                   app_secret=cfg['consumer_secret'],
                   oauth_token=cfg['token'],
                   oauth_token_secret=cfg['secret'])


if __name__ == '__main__':
    # logging.basicConfig(filename='extremely_voice.log', level=logging.WARNING)
    logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
    path = sys.argv[1]
    dry = len(sys.argv) > 2 and sys.argv[2] == 'dry'
    client = get_client(path)
    for tweet in tweets(client):
        if not dry:
            try:
                client.update_status(**tweet)
            except Exception as e:
                logging.exception(e.message)
            else:
                time.sleep(1800)
        else:
            print tweet
            break

