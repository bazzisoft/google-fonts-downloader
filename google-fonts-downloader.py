#!/usr/bin/env python3
"""
Download google font files and CSS for self-hosting.

Requires the python ``requests`` library.
"""
import argparse
import re
import sys
import zipfile

import requests

GOOGLE_FONTS_API = 'https://fonts.googleapis.com/css'
WOFF_USER_AGENT = 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:27.0) Gecko/20100101 Firefox/27.0'
WOFF2_USER_AGENT = 'Mozilla/5.0 (Windows NT 6.3; rv:39.0) Gecko/20100101 Firefox/39.0'

FONT_URL_RE = re.compile(r'src: url\((.*?)\).*?\n')

FONT_FORMATS = [
    {'format': 'woff', 'agent': WOFF_USER_AGENT},
    {'format': 'woff2', 'agent': WOFF2_USER_AGENT},
]


def parse_args():
    parser = argparse.ArgumentParser(description='Download google fonts files for self-hosting.')
    parser.add_argument('-o', '--output', required=True,
                        help='ZIP file with font contents to write.')
    parser.add_argument('-f', '--family', required=True,
                        help='Font family to download.')
    parser.add_argument('-i', '--italic', action='store_true',
                        help='Download italic font variations.')
    parser.add_argument('-w', '--weight', nargs='+', default=['400'],
                        help='Font weights to download (100-900), default 400 (regular)')
    parser.add_argument('-s', '--subset', nargs='+', default=['latin', 'latin-ext'],
                        help='Character subsets (e.g. latin, latin-ext, greek, cyrillic, etc)')
    return parser.parse_args()


def get_base_filename(family, subsets):
    return '{}-{}'.format(family.lower().replace(' ', '_'), '_'.join(subsets))


def download_font_files(family, weights, subsets, italic=False):
    if italic:
        italic_weights = [w + 'i' for w in weights]
        weights = [val for pair in zip(weights, italic_weights) for val in pair]

    base_filename = get_base_filename(family, subsets)
    css = []
    files = {}

    for weight in weights:
        font_format_filenames = []
        for font_format in FONT_FORMATS:
            # Grab CSS for this font weight & style
            r = requests.get(GOOGLE_FONTS_API, headers={'User-Agent': font_format['agent']},
                             params={'family': '{}:{}'.format(family, weight),
                                     'subset': ','.join(subsets)})
            r.raise_for_status()
            print(r.url, file=sys.stderr)
            css_part = r.text

            # Grab font WOFF/WOFF2 file for this font weight & style
            url_matches = list(FONT_URL_RE.finditer(r.text))
            if len(url_matches) != 1:
                raise RuntimeError('Failed to query google fonts for URL: {}'.format(r.url))
            font_url = url_matches[0].group(1)
            r = requests.get(font_url, headers={'User-Agent': font_format['agent']})
            r.raise_for_status()
            print(r.url, file=sys.stderr)

            filename = '{}-{}.{}'.format(
                base_filename,
                weight + 'talic' if weight.endswith('i') else weight,
                font_url.rsplit('.', maxsplit=1)[1])
            files[filename] = r.content
            font_format_filenames.append((font_format, filename))

        # Create one CSS snippet for all font formats
        sources = ["url('{}') format('{}')".format(f[1], f[0]['format'])
                   for f in reversed(font_format_filenames)]
        new_src = 'src: {};\n'.format(',\n       '.join(sources))
        css.append(FONT_URL_RE.sub(new_src, css_part))


    files[base_filename + '.css'] = '\n'.join(css).encode('utf-8')
    return files


def create_zip(output, dirname, files):
    with zipfile.ZipFile(output, 'w') as zipf:
        for filename, contents in files.items():
            zipf.writestr('{}/{}'.format(dirname, filename), contents)


def main():
    options = parse_args()
    files = download_font_files(options.family, options.weight, options.subset, options.italic)
    create_zip(options.output, get_base_filename(options.family, options.subset), files)


if __name__ == '__main__':
    main()
