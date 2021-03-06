# -*- coding: utf-8 -*-

# Copyright(C) 2013      Bezleputh
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


from weboob.tools.backend import BaseBackend
from weboob.capabilities.calendar import ICapCalendarEvent, CATEGORIES

from .browser import HybrideBrowser
from .calendar import HybrideCalendarEvent

__all__ = ['HybrideBackend']


class HybrideBackend(BaseBackend, ICapCalendarEvent):
    NAME = 'hybride'
    DESCRIPTION = u'hybride website'
    MAINTAINER = u'Bezleputh'
    EMAIL = 'carton_ben@yahoo.fr'
    LICENSE = 'AGPLv3+'
    VERSION = '0.i'
    ASSOCIATED_CATEGORIES = [CATEGORIES.CINE]
    BROWSER = HybrideBrowser

    def search_events(self, query):
        if self.has_matching_categories(query):
            with self.browser:
                return self.browser.list_events(query.start_date,
                                                query.end_date,
                                                query.city,
                                                query.categories)

    def list_events(self, date_from, date_to=None):
        with self.browser:
            return self.browser.list_events(date_from, date_to)

    def get_event(self, _id):
        with self.browser:
            return self.browser.get_event(_id)

    def fill_obj(self, event, fields):
        with self.browser:
            return self.browser.get_event(event.id, event)

    OBJECTS = {HybrideCalendarEvent: fill_obj}
