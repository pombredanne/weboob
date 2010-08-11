# -*- coding: utf-8 -*-

# Copyright(C) 2010  Christophe Benz
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.


__all__ = ['IBaseCap', 'NotLoaded', 'LoadingError']


class NotLoadedMeta(type):
    def __str__(self):
        return unicode(self).decode('utf-8')

    def __unicode__(self):
        return u'Not loaded'


class NotLoaded(object):
    __metaclass__ = NotLoadedMeta


class LoadingErrorMeta(type):
    def __str__(self):
        return unicode(self).decode('utf-8')

    def __unicode__(self):
        return u'Loading error'


class LoadingError(object):
    __metaclass__ = LoadingErrorMeta


class IBaseCap(object):
    pass
