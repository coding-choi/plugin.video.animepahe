import re
import urllib
import urlparse
import utils
import http
import json
import time
import requests
from bs4 import BeautifulSoup

_EMBED_EXTRACTORS = {}

def load_video_from_url(in_url):
    found_extractor = None

    for extractor in _EMBED_EXTRACTORS.keys():
        if in_url.startswith(extractor):
            found_extractor = _EMBED_EXTRACTORS[extractor]
            break

    if found_extractor is None:
        print "[*E*] No extractor found for %s" % in_url
        return None

    try:
        if found_extractor['preloader'] is not None:
            print "Modifying Url: %s" % in_url
            in_url = found_extractor['preloader'](in_url)

        if 'kwik' in in_url:
            return found_extractor['parser'](in_url)

        print "Probing source: %s" % in_url
        reqObj = http.send_request(in_url)
        return found_extractor['parser'](http.raw_url(reqObj.url),
                                         reqObj.text,
                                         http.get_referer(in_url))
    except http.URLError:
        return None # Dead link, Skip result
    except:
        raise

    return None

def __check_video_list(refer_url, vidlist, add_referer=False,
                       ignore_cookie=False):
    nlist = []
    for item in vidlist:
        try:
            item_url = item[1]
            if add_referer:
                item_url = http.add_referer_url(item_url, refer_url)

            temp_req = http.head_request(item_url)
            if temp_req.status_code != 200:
                print "[*] Skiping Invalid Url: %s - status = %d" % (item[1],
                                                             temp_req.status_code)
                continue # Skip Item.

            out_url = temp_req.url
            if ignore_cookie:
                out_url = http.strip_cookie_url(out_url)

            nlist.append((item[0], out_url))
        except Exception, e:
            # Just don't add source.
            pass

    return nlist

def __extract_kwik(url):
    s = requests.session()
    download_url = url  

    headers = {
        'referer': download_url,
        }

    source_parts_re = re.compile(r'action=\"([^"]+)\".*value=\"([^"]+)\".*Click Here to Download',
                                           re.DOTALL)

    kwik_text = s.get(download_url, headers=headers).text
    post_url,token = source_parts_re.search(kwik_text).group(1,2)
            
    stream_url = s.post(post_url,
                              headers = headers,
                              data = {'_token': token},
                              allow_redirects = False).headers['Location']

    results = [('', stream_url)]
    return results

def __register_extractor(urls, function, url_preloader=None):
    if type(urls) is not list:
        urls = [urls]

    for url in urls:
        _EMBED_EXTRACTORS[url] = {
            "preloader": url_preloader,
            "parser": function,
        }

def __ignore_extractor(url, content, referer=None):
    return None

def __relative_url(original_url, new_url):
    if new_url.startswith("http://") or new_url.startswith("https://"):
        return new_url

    if new_url.startswith("//"):
        return "http:%s" % new_url
    else:
        return urlparse.urljoin(original_url, new_url)

def __extractor_factory(regex, double_ref=False, match=0, debug=False):
    compiled_regex = re.compile(regex, re.DOTALL)

    def f(url, content, referer=None):
        if debug:
            print url
            print content
            print compiled_regex.findall(content)
            raise

        try:
            regex_url = compiled_regex.findall(content)[match]
            regex_url = __relative_url(url, regex_url)
            if double_ref:
                video_url = utils.head_request(http.add_referer_url(regex_url, url)).url
            else:
                video_url = __relative_url(regex_url, regex_url)
            return video_url
        except Exception, e:
            print "[*E*] Failed to load link: %s: %s" % (url, e)
            return None
    return f

__register_extractor(["https://kwik.cx/e/"],
                     __extract_kwik,
                     lambda x: x.replace('/e/', '/f/'))
