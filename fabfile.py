import urllib
import functools
import datetime
import cookielib
import logging
from os.path import dirname, abspath, join
import getpass

import lxml.html
import requests
import fabric.decorators

import settings


# Logging config
logger = logging.getLogger('sws')
logger.setLevel(logging.DEBUG)

# create console handler and set level to debug
ch = logging.StreamHandler()
formatter = logging.Formatter('%(name)s %(levelname)s - %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)

# Scraper config.
PATH = dirname(abspath(__file__))

request_defaults = {
    #'proxies': {"http": "127.0.0.1:8888"},
    'cookies': cookielib.LWPCookieJar(join(PATH, 'cookies.lwp')),
    'headers': {
        'Accept': ('text/html,application/xhtml+xml,application/',
                   'xml;q=0.9,*/*;q=0.8'),
        'Accept-Encoding': 'gzip, deflate',
        'Accept-Language': 'en-us,en;q=0.5',
        'Connection': 'keep-alive',
        'Host': 'scraperwiki.com',
        'User-Agent': ('Mozilla/5.0 (X11; Ubuntu; Linux i686; rv:10.0.2) '
                       'Gecko/20100101 Firefox/10.0.2')
        },
    }

session = requests.Session(**request_defaults)


def blab(before, after=None):
    '''Log messages before/after running the decorated function.'''
    def wrapperwrapper(f):
        @functools.wraps(f)
        def wrapper(*args, **kw):
            logger.info(before)
            req = f(*args, **kw)
            if after:
                logger.info(after)
            return session.request(**req)
        return wrapper
    return wrapperwrapper


@blab('Connecting to scraperwiki.com...')
def _home():
    return {
        'method': 'GET',
        'url': 'https://scraperwiki.com/',
        }


@blab('Authenticating...')
def _login(home_page, user_or_email, password):

    # Get crsf token from homepage.
    doc = lxml.html.fromstring(home_page.text)
    csrf_token = doc.xpath('//*[@name="csrfmiddlewaretoken"]/@value')[0]

    return {
        'method': 'POST',
        'url': 'https://scraperwiki.com/login/',
        'headers': {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Referer': 'https://scraperwiki.com/',
            },
        'data': urllib.urlencode({
            'csrfmiddlewaretoken': csrf_token,
            'login': 'Log in',
            'password': password,
            'user_or_email': user_or_email
            }),
        }


@blab('Loading current scraper...')
def _load_scraper(scraper_name):
    return {
        'method': 'GET',
        'url': 'https://scraperwiki.com/scrapers/%s/edit/' % scraper_name,
        }


@blab('Pushing new scraper...')
def _post_scraper(scraper_detail, code):

    # Extract the various save parameters.
    doc = lxml.html.fromstring(scraper_detail.text)
    hidden = {}
    for e in doc.xpath('//input[contains(@type, "hidden")]'):
        if 'id' in e.attrib:
            hidden[e.attrib['id']] = e.attrib['value']

    title = hidden['short_name']

    return {
        'method': 'POST',
        'url': 'https://scraperwiki.com/handle_editor_save/',
        'headers': {
            'Content-Type': 'application/json; charset=UTF-8',
            'Pragma': 'no-cache',
            'Referer': 'https://scraperwiki.com/scrapers/%s/edit/' % title,
            'X-Csrftoken': scraper_detail.cookies['csrftoken'],
            'X-Requested-With': 'XMLHttpRequest',
            },
        'data': urllib.urlencode({
            'code': code,
            'commit_message': 'cccommit',
            'earliesteditor': datetime.datetime.now().strftime(
                                            "%a, %d %b %Y %H:%M:%S GMT"),
            'guid': hidden['scraper_guid'],
            'language': hidden['scraperlanguage'],
            'title': title,
            'wiki_type': hidden['id_wiki_type']
            })
        }


def _get_credentials(cache={}):
    try:
        return cache['creds']
    except KeyError:
        result = (
            settings.username or raw_input('scraperwiki username: '),
            settings.password or getpass.getpass('scraperwiki password: '))
        cache['creds'] = result
        return result


@fabric.decorators.task
def push(scrapername, path):
    home_page = _home()
    _login(home_page, *_get_credentials())
    scraper_detail = _load_scraper(scrapername)

    with open(path) as f:
        code = f.read()
    _post_scraper(scraper_detail, code)
