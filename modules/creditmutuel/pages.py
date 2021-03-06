# -*- coding: utf-8 -*-

# Copyright(C) 2010-2012 Julien Veyssier
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


from urlparse import urlparse, parse_qs
from decimal import Decimal
import re
from dateutil.relativedelta import relativedelta

from weboob.tools.browser2.page import HTMLPage, method, ListElement, ItemElement, SkipItem, FormNotFound, TableElement
from weboob.tools.browser2.filters import Filter, Env, CleanText, CleanDecimal, Link, TableCell
from weboob.tools.browser import  BrowserIncorrectPassword
from weboob.capabilities import NotAvailable
from weboob.capabilities.bank import Account
from weboob.tools.capabilities.bank.transactions import FrenchTransaction
from weboob.tools.date import parse_french_date


class LoggedPage(object):
    logged = True


class LoginPage(HTMLPage):
    def login(self, login, passwd):
        form = self.get_form(nr=0)
        form['_cm_user'] = login
        form['_cm_pwd'] = passwd
        form.submit()


class LoginErrorPage(HTMLPage):
    pass


class ChangePasswordPage(LoggedPage, HTMLPage):
    def on_load(self):
        raise BrowserIncorrectPassword('Please change your password')

class VerifCodePage(LoggedPage, HTMLPage):
    def on_load(self):
        raise BrowserIncorrectPassword('Unable to login: website asks a code from a card')


class TransfertPage(LoggedPage, HTMLPage):
    pass


class AccountsPage(LoggedPage, HTMLPage):
    TYPES = {'C/C':             Account.TYPE_CHECKING,
             'Livret':          Account.TYPE_SAVINGS,
             'Pret':            Account.TYPE_LOAN,
             'Compte Courant':  Account.TYPE_CHECKING,
             'Compte Cheque':   Account.TYPE_CHECKING,
             'Compte Epargne':  Account.TYPE_SAVINGS,
            }

    @method
    class iter_accounts(ListElement):
        item_xpath = '//tr'
        flush_at_end = True

        class item(ItemElement):
            klass = Account

            def __filter__(self, el):
                if len(el.xpath('./td')) < 2:
                    return False

                first_td = el.xpath('./td')[0]
                return ((first_td.attrib.get('class', '') == 'i g' or first_td.attrib.get('class', '') == 'p g')
                        and first_td.find('a') is not None)

            class Label(Filter):
                def filter(self, text):
                    return text.lstrip(' 0123456789').title()

            obj_id = Env('id')
            obj_label = Label(CleanText('./td[1]/a'))
            obj_balance = CleanDecimal('./td[2] | ./td[3]')
            obj_coming = Env('coming')
            obj_balance = Env('balance')
            obj_currency = FrenchTransaction.Currency('./td[2] | ./td[3]')
            obj__link_id = Link('./td[1]/a')
            obj__card_links = []

            def obj_type(self):
                for pattern, actype in AccountsPage.TYPES.iteritems():
                    if self.obj.label.startswith(pattern):
                        return actype

            def parse(self, el):
                link = el.xpath('./td[1]/a')[0].get('href', '')
                if link.startswith('POR_SyntheseLst'):
                    raise SkipItem()

                url = urlparse(link)
                p = parse_qs(url.query)
                if not 'rib' in p:
                    raise SkipItem()

                balance = CleanDecimal('./td[2] | ./td[3]')(self)
                id = p['rib'][0]

                # Handle cards
                if id in self.parent.objects:
                    account = self.parent.objects[id]
                    if not account.coming:
                        account.coming = Decimal('0.0')
                    account.coming += balance
                    account._card_links.append(link)
                    raise SkipItem()

                self.env['id'] = id

                # Handle real balances
                page = self.page.browser.open(link)
                coming = page.find_amount(u"Opérations à venir")
                accounting = page.find_amount(u"Solde comptable")

                if accounting is not None and accounting + (coming or Decimal('0')) != balance:
                    self.logger.warning('%s + %s != %s' % (accounting, coming, balance))

                if accounting is not None:
                    balance = accounting

                self.env['balance'] = balance
                self.env['coming'] = coming or NotAvailable


class Transaction(FrenchTransaction):
    PATTERNS = [(re.compile('^VIR(EMENT)? (?P<text>.*)'), FrenchTransaction.TYPE_TRANSFER),
                (re.compile('^PRLV (?P<text>.*)'),        FrenchTransaction.TYPE_ORDER),
                (re.compile('^(?P<text>.*) CARTE \d+ PAIEMENT CB\s+(?P<dd>\d{2})(?P<mm>\d{2}) ?(.*)$'),
                                                          FrenchTransaction.TYPE_CARD),
                (re.compile('^RETRAIT DAB (?P<dd>\d{2})(?P<mm>\d{2}) (?P<text>.*) CARTE [\*\d]+'),
                                                          FrenchTransaction.TYPE_WITHDRAWAL),
                (re.compile('^CHEQUE( (?P<text>.*))?$'),  FrenchTransaction.TYPE_CHECK),
                (re.compile('^(F )?COTIS\.? (?P<text>.*)'),FrenchTransaction.TYPE_BANK),
                (re.compile('^(REMISE|REM CHQ) (?P<text>.*)'),FrenchTransaction.TYPE_DEPOSIT),
               ]

    _is_coming = False


class Pagination(object):
    def next_page(self):
        try:
            form = self.page.get_form('//form[@id="paginationForm"]')
        except FormNotFound:
            return

        text = CleanText.clean(form.el)
        m = re.search(u'(\d+) / (\d+)', text or '', flags=re.MULTILINE)
        if not m:
            return

        cur = int(m.group(1))
        last = int(m.group(2))

        if cur == last:
            return

        form['page'] = str(cur + 1)
        return form.request


class OperationsPage(LoggedPage, HTMLPage):
    @method
    class get_history(Pagination, TableElement):
        head_xpath = '//table[@class="liste"]//thead//tr/th'
        item_xpath = '//table[@class="liste"]//tbody/tr'

        columns = {'date':  u'Date',
                   'vdate': u'Valeur',
                   'raw':   u'Opération',
                   'debit': u'Débit',
                   'credit': u'Crédit',
                  }

        class item(ItemElement):
            klass = Transaction

            __filter__ = lambda el: len(el.xpath('./td')) >= 4 and len(el.xpath('./td[@class="i g" or @class="p g" or contains(@class, "_c1 c _c1")]')) > 0

            class OwnRaw(Filter):
                def __call__(self, item):
                    parts = [txt.strip() for txt in item.el.xpath('./td[last()-2]')[0].itertext() if len(txt.strip()) > 0]

                    # To simplify categorization of CB, reverse order of parts to separate
                    # location and institution.
                    if parts[0].startswith('PAIEMENT CB'):
                        parts.reverse()

                    return u' '.join(parts)

            obj_raw = Transaction.Raw(OwnRaw())
            obj_date = Transaction.Date(TableCell('date'))
            obj_vdate = Transaction.Date(TableCell('vdate', 'date'))
            obj_amount = Transaction.Amount(TableCell('credit'), TableCell('debit'))

    def find_amount(self, title):
        try:
            td = self.doc.xpath(u'//th[contains(text(), "%s")]/../td' % title)[0]
        except IndexError:
            return None
        else:
            return Decimal(FrenchTransaction.clean_amount(td.text))

    def get_coming_link(self):
        try:
            a = self.doc.xpath(u'//a[contains(text(), "Opérations à venir")]')[0]
        except IndexError:
            return None
        else:
            return a.attrib['href']


class ComingPage(OperationsPage, LoggedPage):
    @method
    class get_history(Pagination, ListElement):
        item_xpath = '//table[@class="liste"]/tbody/tr'

        class item(ItemElement):
            klass = Transaction
            __filter__ = lambda el: len(el.xpath('./td')) >= 3

            obj_date = Transaction.Date('./td[1]')
            obj_raw = Transaction.Raw('./td[2]')
            obj_amount = Transaction.Amount('./td[last()]')
            obj__is_coming = True


class CardPage(OperationsPage, LoggedPage):
    @method
    class get_history(Pagination, ListElement):
        class list_cards(ListElement):
            item_xpath = '//table[@class="liste"]/tbody/tr/td/a'

            class item(ItemElement):
                def __iter__(self):
                    card_link = self.el.get('href')
                    history_url = '%s/%s/fr/banque/%s' % (self.browser.BASEURL, self.browser.currentSubBank, card_link)
                    page = self.browser.location(history_url)

                    for op in page.get_history():
                        yield op

        class list_history(ListElement):
            item_xpath = '//table[@class="liste"]/tbody/tr'

            def parse(self, el):
                label = CleanText('//div[contains(@class, "lister")]//p[@class="c"]')(el)
                label = re.findall('(\d+ [^ ]+ \d+)', label)[-1]
                # use the trick of relativedelta to get the last day of month.
                self.env['debit_date'] = parse_french_date(label) + relativedelta(day=31)

            class item(ItemElement):
                klass = Transaction
                __filter__ = lambda el: len(el.xpath('./td')) >= 4

                obj_raw = Transaction.Raw('./td[last()-2] | ./td[last()-1]')
                obj_type = Transaction.TYPE_CARD
                obj_date = Env('debit_date')
                obj_rdate = Transaction.Date('./td[1]')
                obj_vdate = Transaction.Date('./td[1]')
                obj_amount = Transaction.Amount('./td[last()]')


class NoOperationsPage(OperationsPage, LoggedPage):
    def get_history(self):
        return iter([])
