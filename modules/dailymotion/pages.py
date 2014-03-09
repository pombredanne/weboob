# -*- coding: utf-8 -*-

# Copyright(C) 2011  Romain Bignon
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

from weboob.tools.json import json
import datetime
import re
import urllib
import urlparse
import mechanize

from weboob.capabilities import NotAvailable
from weboob.capabilities.image import BaseImage
from weboob.tools.misc import html2text
from weboob.tools.browser import BasePage, BrokenPageError


from .video import DailymotionVideo


__all__ = ['IndexPage', 'VideoPage', 'KidsVideoPage']


class IndexPage(BasePage):
    def iter_videos(self):
        for div in self.parser.select(self.document.getroot(), 'div.dmpi_video_item'):
            _id = div.attrib.get('data-id', None)

            if _id is None:
                self.browser.logger.warning('Unable to find the ID of a video')
                continue

            video = DailymotionVideo(_id)
            video.title = unicode(self.parser.select(div, 'h3 a', 1).text).strip()
            video.author = unicode(self.parser.select(div, 'div.dmpi_user_login', 1).find('a').find('span').text).strip()
            video.description = html2text(self.parser.tostring(self.parser.select(div, 'div.dmpi_video_description', 1))).strip() or unicode()
            try:
                parts = self.parser.select(div, 'div.duration', 1).text.split(':')
            except BrokenPageError:
                # it's probably a live, np.
                video.duration = NotAvailable
            else:
                if len(parts) == 1:
                    seconds = parts[0]
                    hours = minutes = 0
                elif len(parts) == 2:
                    minutes, seconds = parts
                    hours = 0
                elif len(parts) == 3:
                    hours, minutes, seconds = parts
                else:
                    raise BrokenPageError('Unable to parse duration %r' % self.parser.select(div, 'div.duration', 1).text)
                video.duration = datetime.timedelta(hours=int(hours), minutes=int(minutes), seconds=int(seconds))
            url = unicode(self.parser.select(div, 'img.preview', 1).attrib['data-src'])
            # remove the useless anti-caching
            url = re.sub('\?\d+', '', url)
            video.thumbnail = BaseImage(url)
            video.thumbnail.url = video.thumbnail.id

            video.set_empty_fields(NotAvailable, ('url',))
            yield video

    def get_rate(self, div):
        m = re.match('width: *(\d+)px', div.attrib['style'])
        if m:
            return int(m.group(1))
        else:
            self.browser.logger.warning('Unable to parse rating: %s' % div.attrib['style'])
            return 0


class VideoPage(BasePage):
    def get_video(self, video=None):
        if video is None:
            video = DailymotionVideo(self.group_dict['id'])

        head = self.parser.select(self.document.getroot(), 'head', 1)

        video.title = unicode(self.parser.select(head, 'meta[property="og:title"]', 1).get("content")).strip()
        video.author = unicode(self.parser.select(head, 'meta[name="author"]', 1).get("content")).strip()

        url = unicode(self.parser.select(head, 'meta[property="og:image"]', 1).get("content")).strip()
        # remove the useless anti-caching
        url = re.sub('\?\d+', '', url)
        video.thumbnail = BaseImage(url)
        video.thumbnail.url = video.thumbnail.id

        try:
            parts = self.parser.select(head, 'meta[property="video:duration"]', 1).get("content").strip().split(':')
        except BrokenPageError:
            # it's probably a live, np.
            video.duration = NotAvailable
        else:
            if len(parts) == 1:
                seconds = parts[0]
                hours = minutes = 0
            elif len(parts) == 2:
                minutes, seconds = parts
                hours = 0
            elif len(parts) == 3:
                hours, minutes, seconds = parts
            else:
                raise BrokenPageError('Unable to parse duration %r' % parts)
            video.duration = datetime.timedelta(hours=int(hours), minutes=int(minutes), seconds=int(seconds))

        try:
            video.description = html2text(self.parser.select(head, 'meta[property="og:description"]', 1).get("content")).strip() or unicode()
        except BrokenPageError:
            video.description = u''

        embed_page = self.browser.readurl('http://www.dailymotion.com/embed/video/%s' % video.id)

        m = re.search('var info = ({.*?}),[^{"]', embed_page)
        if not m:
            raise BrokenPageError('Unable to find information about video')

        info = json.loads(m.group(1))
        for key in ['stream_h264_hd1080_url','stream_h264_hd_url',
                    'stream_h264_hq_url','stream_h264_url',
                    'stream_h264_ld_url']:
            if info.get(key):#key in info and info[key]:
                max_quality = key
                break
        else:
            raise BrokenPageError(u'Unable to extract video URL')

        video.url = info[max_quality]

        video.set_empty_fields(NotAvailable)

        return video


class KidsVideoPage(BasePage):

    CONTROLLER_PAGE = 'http://kids.dailymotion.com/controller/Page_Kids_KidsUserHome?%s'

    def get_video(self, video=None):
        if video is None:
            video = DailymotionVideo(self.group_dict['id'])

        # The player html code with all the required information is loaded
        # after the main page using javascript and a special XmlHttpRequest
        # we emulate this behaviour
        from_request = self.group_dict['from']

        query = urllib.urlencode({
            'from_request': from_request,
            'request': '/video/%s?get_video=1' % video.id
            })

        request = mechanize.Request(KidsVideoPage.CONTROLLER_PAGE % query)
        # This header is mandatory to have the correct answer from dailymotion
        request.add_header('X-Requested-With', 'XMLHttpRequest')
        player_html = self.browser.readurl(request)

        try:
            m = re.search('<param name="flashvars" value="(?P<flashvars>.*?)"', player_html)
            flashvars = urlparse.parse_qs(m.group('flashvars'))
            info = json.loads(flashvars['sequence'][0])

            # The video parameters seem to be always located at the same place
            # in the structure: ['sequence'][0]['layerList'][0]['sequenceList']
            #   [0]['layerList'][0]['param']['extraParams'])
            #
            # but to be more tolerant to future changes in the structure, we
            # prefer to look for the parameters everywhere in the structure

            def find_video_params(data):
                if isinstance(data, dict):
                    if 'param' in data and 'extraParams' in data['param']:
                        return data['param']['extraParams']
                    data = data.values()

                if not isinstance(data, list):
                    return None

                for item in data:
                    ret = find_video_params(item)
                    if ret:
                        return ret

                return None

            params = find_video_params(info['sequence'])

            video.title = unicode(params['videoTitle'])
            video.author = unicode(params['videoOwnerLogin'])
            video.description = unicode(params['videoDescription'])
            video.thumbnail = BaseImage(params['videoPreviewURL'])
            video.thumbnail.url = unicode(params['videoPreviewURL'])
            video.duration = datetime.timedelta(seconds=params['mediaDuration'])

        except:
            # If anything goes wrong, we prefer to at least give empty values
            # this will allow video download to work even if we don't have the
            # metadata
            video.title = u''
            video.description = u''
            video.author = u''
            video.thumbnail = None
            video.duration = NotAvailable

        embed_page = self.browser.readurl('http://www.dailymotion.com/embed/video/%s' % video.id)

        m = re.search('var info = ({.*?}),[^{"]', embed_page)
        if not m:
            raise BrokenPageError('Unable to find information about video')

        info = json.loads(m.group(1))
        for key in ['stream_h264_hd1080_url', 'stream_h264_hd_url',
                    'stream_h264_hq_url', 'stream_h264_url',
                    'stream_h264_ld_url']:
            if info.get(key):  # key in info and info[key]:
                max_quality = key
                break
        else:
            raise BrokenPageError(u'Unable to extract video URL')

        video.url = unicode(info[max_quality])

        video.set_empty_fields(NotAvailable)

        return video
