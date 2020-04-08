from resources.lib.ui import control
from resources.lib.ui import utils
from resources.lib.ui.SourcesList import SourcesList
from resources.lib.ui.router import on_param, route, router_process
from resources.lib.AnimepaheBrowser import AnimepaheBrowser
from resources.lib.AniListBrowser import AniListBrowser
from resources.lib.WatchlistIntegration import set_browser, add_watchlist
import urlparse

AB_LIST = ["none"] + [chr(i) for i in range(ord("a"), ord("z")+1)]
AB_LIST_NAMING = ["No Letter"] + [chr(i) for i in range(ord("A"), ord("Z")+1)]

HISTORY_KEY = "addon.history"
LASTWATCHED_KEY = "addon.last_watched"
LASTWATCHED_NAME_KEY = "%s.name" % LASTWATCHED_KEY
LASTWATCHED_URL_KEY = "%s.url" % LASTWATCHED_KEY
LASTWATCHED_IMAGE_KEY = "%s.image" % LASTWATCHED_KEY
HISTORY_DELIM = ";"

MENU_ITEMS = [
    (control.lang(30005), "latest", ''),
    (control.lang(30006), "anichart_popular", ''),
    (control.lang(30004), "anilist_genres", ''),
    (control.lang(30008), "search_history", ''),
    (control.lang(30009), "settings", ''),
]

_BROWSER = AnimepaheBrowser()

def _add_last_watched():
    if not control.getSetting(LASTWATCHED_URL_KEY):
        return

    MENU_ITEMS.insert(0, (
        "%s[I]%s[/I]" % (control.lang(30000),
                         control.getSetting(LASTWATCHED_NAME_KEY)),
        control.getSetting(LASTWATCHED_URL_KEY),
        control.getSetting(LASTWATCHED_IMAGE_KEY)
    ))

def __set_last_watched(url, is_dubbed, name, image):
    control.setSetting(LASTWATCHED_URL_KEY, 'animes/%s/%s' %(url, "dub" if is_dubbed else "sub"))
    control.setSetting(LASTWATCHED_NAME_KEY, '%s %s' %(name, "(Dub)" if is_dubbed else "(Sub)"))
    control.setSetting(LASTWATCHED_IMAGE_KEY, image)

def sortResultsByRes(fetched_urls):
    prefereResSetting = utils.parse_resolution_of_source(control.getSetting('prefres'))

    filtered_urls = filter(lambda x: utils.parse_resolution_of_source(x[0]) <=
                           prefereResSetting, fetched_urls)

    if not filtered_urls:
        return sorted(fetched_urls)

    return sorted(filtered_urls, key=lambda x:
                  utils.parse_resolution_of_source(x[0]),
                  reverse=True)

def get_animes_contentType(seasons=None):
    contentType = control.getSetting("contenttype.episodes")
    if seasons and seasons[0]['is_dir']:
        contentType = control.getSetting("contenttype.seasons")

    return contentType

#Will be called at handle_player
def on_percent():
    return int(control.getSetting('watchlist.percent'))

#Will be called when player is stopped in the middle of the episode
def on_stopped():
    return control.yesno_dialog(control.lang(30200), control.lang(30201), control.lang(30202))

#Will be called on genre page
def genre_dialog(genre_display_list):
    return control.multiselect_dialog(control.lang(30004), genre_display_list)

@route('settings')
def SETTINGS(payload, params):
    return control.settingsMenu();

@route('clear_cache')
def CLEAR_CACHE(payload, params):
    return control.clear_cache();

@route('clear_settings')
def CLEAR_SETTINGS(payload, params):
    dialog = control.yesno_dialog(control.lang(30300), control.lang(30301))
    return control.clear_settings(dialog);

@route('animes/*')
def ANIMES_PAGE(payload, params):
    return control.draw_items(_BROWSER.get_anime_episodes(payload))

@route('animes_page/*')
def ANIMES_PAGES(payload, params):
    anime_id, page = payload.rsplit("/", 1)
    return control.draw_items(_BROWSER.get_anime_episodes(anime_id, int(page)))

@route('latest')
def LATEST(payload, params):
    return control.draw_items(_BROWSER.get_latest())

@route('latest/*')
def LATEST_PAGES(payload, params):
    return control.draw_items(_BROWSER.get_latest(int(payload)))

@route('anichart_popular')
def ANICHART_POPULAR(payload, params):
    return control.draw_items(AniListBrowser().get_popular())

@route('anichart_popular/*')
def ANICHART_POPULAR_PAGES(payload, params):
    return control.draw_items(AniListBrowser().get_popular(int(payload)))

@route('anilist_genres')
def ANILIST_GENRES(payload, params):
    return control.draw_items(AniListBrowser().get_genres(genre_dialog))

@route('anilist_genres/*')
def ANILIST_GENRES_PAGES(payload, params):
    genres, tags, page = payload.split("/")[-3:]
    return control.draw_items(AniListBrowser().get_genres_page(genres, tags, int(page)))

@route('search_history')
def SEARCH_HISTORY(payload, params):
    history = control.getSetting(HISTORY_KEY)
    history_array = history.split(HISTORY_DELIM)
    if history != "" and "Yes" in control.getSetting('searchhistory') :
        return control.draw_items(_BROWSER.search_history(history_array))
    else :
        return SEARCH(payload,params)

@route('clear_history')
def CLEAR_HISTORY(payload, params):
    control.setSetting(HISTORY_KEY, "")
    return LIST_MENU(payload, params)

@route('search')
def SEARCH(payload, params):
    query = control.keyboard(control.lang(30008))
    if not query:
        return False

    # TODO: Better logic here, maybe move functionatly into router?
    if "Yes" in control.getSetting('searchhistory') :
        history = control.getSetting(HISTORY_KEY)
        if history != "" :
            query = query+HISTORY_DELIM
        history=query+history
        while history.count(HISTORY_DELIM) > 6 :
            history=history.rsplit(HISTORY_DELIM, 1)[0]
        control.setSetting(HISTORY_KEY, history)

    return control.draw_items(_BROWSER.search_site(query))

@route('search/*')
def SEARCH_PAGES(payload, params):
    query, page = payload.rsplit("/", 1)
    return control.draw_items(_BROWSER.search_site(query, int(page)))

@route('play/*')
def PLAY(payload, params):
    ep_id = payload
    sources = _BROWSER.get_episode_sources(ep_id, params['session'])
    autoplay = True if 'true' in control.getSetting('autoplay') else False

    s = SourcesList(sorted(sources.items()), autoplay, sortResultsByRes, {
        'title': control.lang(30100),
        'processing': control.lang(30101),
        'choose': control.lang(30102),
        'notfound': control.lang(30103),
    })

    control.play_source(s.get_video_link())

@route('')
def LIST_MENU(payload, params):
    return control.draw_items(
        [utils.allocate_item(name, url, True, image) for name, url, image in MENU_ITEMS],
        contentType=control.getSetting("contenttype.menu"),
    )

set_browser(_BROWSER)
add_watchlist(MENU_ITEMS)
router_process(control.get_plugin_url(), control.get_plugin_params())
