# -*- coding: utf-8 -*-

# Copyright(C) 2010-2011 Noé Rubinstein
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

from weboob.tools.capabilities.gallery.genericcomicreader import GenericComicReaderBackend, DisplayPage


__all__ = ['MangareaderBackend']


class MangareaderBackend(GenericComicReaderBackend):
    NAME = 'mangareader'
    DESCRIPTION = 'MangaReader manga reading website'
    DOMAIN = 'www.mangareader.net'
    BROWSER_PARAMS = dict(
        img_src_xpath="//img[@id='img']/@src",
        page_list_xpath="//select[@id='pageMenu']/option/@value")
    ID_REGEXP = r'[^/]+/[^/]+'
    URL_REGEXP = r'.+mangareader.net/(%s).+' % ID_REGEXP
    ID_TO_URL = 'http://www.mangareader.net/%s'
    PAGES = {r'http://.+\.mangareader.net/.+': DisplayPage}  # oh well
