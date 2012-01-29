# -*- coding: utf-8 -*-

# Copyright(C) 2011 Romain Bignon
#
# This file is part of weboob.
#
# weboob is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# weboob is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with weboob. If not, see <http://www.gnu.org/licenses/>.


import urllib

from weboob.tools.browser import BaseBrowser
from weboob.tools.browser.decorators import id2url

from .pages.index import IndexPage
from .pages.video import VideoPage
from .video import NolifeTVVideo


__all__ = ['NolifeTVBrowser']


class NolifeTVBrowser(BaseBrowser):
    DOMAIN = 'online.nolife-tv.com'
    ENCODING = None
    PAGES = {r'http://online.nolife-tv.com/index.php\??': IndexPage,
             r'http://online.nolife-tv.com/': IndexPage,
             r'http://online.nolife-tv.com/index.php\?id=(?P<id>.+)': VideoPage}

    @id2url(NolifeTVVideo.id2url)
    def get_video(self, url, video=None):
        self.location(url)
        assert self.is_on_page(VideoPage), 'Should be on video page.'
        return self.page.get_video(video)

    def iter_search_results(self, pattern):
        if not pattern:
            self.home()
        else:
            self.location('/index.php?', 'search=%s' % urllib.quote_plus(pattern.encode('utf-8')))
        assert self.is_on_page(IndexPage)
        return self.page.iter_videos()