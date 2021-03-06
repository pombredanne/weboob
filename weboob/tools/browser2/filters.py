# -*- coding: utf-8 -*-

# Copyright(C) 2014 Romain Bignon
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

from __future__ import absolute_import

from decimal import Decimal
import re


class Filter(object):
    """
    Class used to filter on a HTML element given as call parameter to return
    matching elements.

    Filters can be chained, so the parameter supplied to constructor can be
    either a xpath selector string, or an other filter called before.

    >>> from lxml.html import etree
    >>> f = CleanDecimal(CleanText('//p'))
    >>> f(etree.fromstring('<html><body><p>blah: <span>229,90</span></p></body></html>'))
    Decimal('229.90')
    """

    def __init__(self, selector=None):
        self.selector = selector

    def __call__(self, item):
        if isinstance(self.selector, basestring):
            value = item.xpath(self.selector)
        elif callable(self.selector):
            value = self.selector(item)
        else:
            value = self.selector

        return self.filter(value)

    def filter(self, value):
        """
        This method have to be overrided by children classes.
        """
        return value

class Env(Filter):
    """
    Filter to get environment value of the item.

    It is used for example to get page parameters, or when there is a parse()
    method on ItemElement.
    """
    def __init__(self, name):
        self.name = name

    def __call__(self, item):
        return item.env[self.name]

class TableCell(Filter):
    """
    Used with TableElement, it get the cell value from its name.

    For example:

        class table(TableElement):
            head_xpath = '//table/thead/th'
            item_xpath = '//table/tbody/tr'
            columns = {'date':  u'Date',
                       'label': [u'Name', 'Label'],
                      }

            class item(ItemElement):
                klass = Object
                obj_date = Date(TableCell('date'))
                obj_label = CleanText(TableCell('label'))
    """

    def __init__(self, *names):
        self.names = names

    def __call__(self, item):
        for name in self.names:
            idx = item.parent.get_colnum(name)
            if idx is not None:
                return item.xpath('./td[%s]' % (idx + 1))
        raise KeyError('Unable to find column %s' % ' or '.join(self.names))

class CleanText(Filter):
    """
    Get a cleaned text from an element.

    It replaces all tabs and multiple spaces to one space and strip the result
    string.
    """
    def filter(self, txt):
        if isinstance(txt, (tuple,list)):
            txt = ' '.join(map(self.clean, txt))

        return self.clean(txt)

    @classmethod
    def clean(self, txt):
        if not isinstance(txt, basestring):
            txt = [t.strip() for t in txt.itertext()]
            txt = u' '.join(txt)                 # 'foo   bar'
        txt = re.sub(u'[\s\xa0\t]+', u' ', txt)   # 'foo bar'
        return txt.strip()

class CleanDecimal(CleanText):
    """
    Get a cleaned Decimal value from an element.
    """
    def filter(self, text):
        text = super(CleanDecimal, self).filter(text)
        text = text.replace('.','').replace(',','.')
        return Decimal(re.sub(u'[^\d\-\.]', '', text))

class Link(Filter):
    """
    Get the link uri of an element.

    If the <a> tag is not found, an exception IndexError is raised.
    """
    def filter(self, el):
        return el[0].attrib.get('href', '')
