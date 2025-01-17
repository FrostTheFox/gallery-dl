# -*- coding: utf-8 -*-

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation.

"""Extractors for https://lensdump.com/"""

from .common import GalleryExtractor, Extractor, Message
from .. import text, util

BASE_PATTERN = r"(?:https?://)?lensdump\.com"


class LensdumpBase():
    """Base class for lensdump extractors"""
    category = "lensdump"
    root = "https://lensdump.com"

    def nodes(self, page=None):
        if page is None:
            page = self.request(self.url).text

        # go through all pages starting from the oldest
        page_url = text.urljoin(self.root, text.extr(
            text.extr(page, ' id="list-most-oldest-link"', '>'),
            'href="', '"'))
        while page_url is not None:
            if page_url == self.url:
                current_page = page
            else:
                current_page = self.request(page_url).text

            for node in text.extract_iter(
                    current_page, ' class="list-item ', '>'):
                yield node

            # find url of next page
            page_url = text.extr(
                text.extr(current_page, ' data-pagination="next"', '>'),
                'href="', '"')
            if page_url is not None and len(page_url) > 0:
                page_url = text.urljoin(self.root, page_url)
            else:
                page_url = None


class LensdumpAlbumExtractor(LensdumpBase, GalleryExtractor):
    subcategory = "album"
    pattern = BASE_PATTERN + r"/(?:((?!\w+/albums|a/|i/)\w+)|a/(\w+))"
    test = (
        ("https://lensdump.com/a/1IhJr", {
            "url": "7428cc906e7b291c778d446a11c602b81ba72840",
            "keyword": {
                "extension": "png",
                "name": str,
                "num": int,
                "title": str,
                "url": str,
                "width": int,
            },
        }),
    )

    def __init__(self, match):
        GalleryExtractor.__init__(self, match, match.string)
        self.gallery_id = match.group(1) or match.group(2)

    def metadata(self, page):
        return {
            "gallery_id": self.gallery_id,
            "title": text.unescape(text.extr(
                page, 'property="og:title" content="', '"').strip())
        }

    def images(self, page):
        for node in self.nodes(page):
            # get urls and filenames of images in current page
            json_data = util.json_loads(text.unquote(
                text.extr(node, 'data-object="', '"')))
            image_id = json_data.get('name')
            image_url = json_data.get('url')
            image_title = json_data.get('title')
            if image_title is not None:
                image_title = text.unescape(image_title)
            yield (image_url, {
                'id': image_id,
                'url': image_url,
                'title': image_title,
                'name': json_data.get('filename'),
                'filename': image_id,
                'extension': json_data.get('extension'),
                'height': text.parse_int(json_data.get('height')),
                'width': text.parse_int(json_data.get('width')),
            })


class LensdumpAlbumsExtractor(LensdumpBase, Extractor):
    """Extractor for album list from lensdump.com"""
    subcategory = "albums"
    pattern = BASE_PATTERN + r"/\w+/albums"
    test = ("https://lensdump.com/vstar925/albums",)

    def items(self):
        for node in self.nodes():
            album_url = text.urljoin(self.root, text.extr(
                node, 'data-url-short="', '"'))
            yield Message.Queue, album_url, {
                "_extractor": LensdumpAlbumExtractor}


class LensdumpImageExtractor(LensdumpBase, Extractor):
    """Extractor for individual images on lensdump.com"""
    subcategory = "image"
    filename_fmt = "{category}_{id}{title:?_//}.{extension}"
    directory_fmt = ("{category}",)
    archive_fmt = "{id}"
    pattern = BASE_PATTERN + r"/i/(\w+)"
    test = (
        ("https://lensdump.com/i/tyoAyM", {
            "pattern": r"https://i\d\.lensdump\.com/i/tyoAyM\.webp",
            "url": "ae9933f5f3bd9497bfc34e3e70a0fbef6c562d38",
            "content": "1aa749ed2c0cf679ec8e1df60068edaf3875de46",
            "keyword": {
                "date": "dt:2022-08-01 08:24:28",
                "extension": "webp",
                "filename": "tyoAyM",
                "height": 400,
                "id": "tyoAyM",
                "title": "MYOBI clovis bookcaseset",
                "url": "https://i2.lensdump.com/i/tyoAyM.webp",
                "width": 620,
            },
        }),
    )

    def __init__(self, match):
        Extractor.__init__(self, match)
        self.key = match.group(1)

    def items(self):
        url = "{}/i/{}".format(self.root, self.key)
        extr = text.extract_from(self.request(url).text)

        data = {
            "id"    : self.key,
            "title" : text.unescape(extr(
                'property="og:title" content="', '"')),
            "url"   : extr(
                'property="og:image" content="', '"'),
            "width" : text.parse_int(extr(
                'property="image:width" content="', '"')),
            "height": text.parse_int(extr(
                'property="image:height" content="', '"')),
            "date"  : text.parse_datetime(extr(
                '<span title="', '"'), "%Y-%m-%d %H:%M:%S"),
        }

        text.nameext_from_url(data["url"], data)
        yield Message.Directory, data
        yield Message.Url, data["url"], data
