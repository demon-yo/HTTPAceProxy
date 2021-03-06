# -*- coding: utf-8 -*-
'''
Allfon.tv Playlist Downloader Plugin
http://ip:port/allfon
'''
import logging, re
from urlparse import parse_qs
import requests
import time
from PluginInterface import AceProxyPlugin
from PlaylistGenerator import PlaylistGenerator
import config.allfon as config

class Allfon(AceProxyPlugin):

    # ttvplaylist handler is obsolete
    handlers = ('allfon',)

    logger = logging.getLogger('plugin_allfon')
    playlist = None
    playlisttime = None

    def __init__(self, AceConfig, AceStuff): pass

    def downloadPlaylist(self):
        headers = {'User-Agent': 'Magic Browser', 'Accept-Encoding': 'gzip,deflate', 'Connection': 'close'}
        proxies = {}; timeout = 5
        if config.useproxy: proxies = config.proxies; timeout = 30
        try:
            Allfon.playlist = requests.get(config.url, headers=headers, proxies=proxies, timeout=timeout).text.encode('UTF-8')
            Allfon.logger.debug('AllFon playlist %s downloaded !' % config.url)
            Allfon.playlisttime = int(time.time())
        except requests.exceptions.ConnectionError:
            Allfon.logger.error("Can't download AllFonTV playlist!")
            return False
        else: return True

    def handle(self, connection, headers_only=False):

        hostport = connection.headers['Host']
        if headers_only:
            connection.send_response(200)
            connection.send_header('Content-Type', 'application/x-mpegurl')
            connection.send_header('Connection', 'close')
            connection.end_headers()
            return

        # 15 minutes cache
        if not Allfon.playlist or (int(time.time()) - Allfon.playlisttime > 15 * 60):
            if not self.downloadPlaylist(): connection.dieWithError(); return

        add_ts = True if connection.path.endswith('/ts') else False
        playlistgen = PlaylistGenerator(m3uchanneltemplate=config.m3uchanneltemplate)

        pattern = re.compile(r',(?P<name>\S.+)[\r\n].+[\r\n].+[\r\n](?P<url>[^\r\n]+)?')
        for match in pattern.finditer(Allfon.playlist, re.MULTILINE): playlistgen.addItem(match.groupdict())

        Allfon.logger.info('AllFon playlist created')
        params = parse_qs(connection.query)
        fmt = params['fmt'][0] if 'fmt' in params else None
        header = '#EXTM3U url-tvg="%s" tvg-shift=%d deinterlace=1 m3uautoload=1 cache=1000\n' %(config.tvgurl, config.tvgshift)

        exported = playlistgen.exportm3u(hostport, header=header, add_ts=add_ts, fmt=fmt)

        connection.send_response(200)
        connection.send_header('Content-Type', 'audio/mpegurl; charset=utf-8')
        connection.send_header('Content-Length', str(len(exported)))
        connection.send_header('Connection', 'close')
        connection.end_headers()

        connection.wfile.write(exported)
