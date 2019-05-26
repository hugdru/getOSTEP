import argparse
import os
import pprint
import re
import shutil
import sys
from io import StringIO
from urllib.parse import urlparse
from urllib.request import urlopen

import lxml.etree


def main():
    args = get_args()
    latest_errdata_version = get_latest_errdata_version(args)
    decide_if_download_book(latest_errdata_version, args)


def get_latest_errdata_version(args):
    errdata_url = args.errdata_url
    tree = get_and_parse_html(errdata_url)
    ul = get_exactly_one(tree.xpath('//ul'), 'Expecting exactly one unordered list in errdata')
    top_li = get_exactly_one(ul.xpath('./li[1]'), 'Expecting exactly on top li in errdata')
    return unwrap(top_li)


def decide_if_download_book(latest_errdata_version, args):
    errdata_version_filepath = f'{args.directory}/{args.errdata_filename}'

    errdata_version_exists = os.path.isfile(errdata_version_filepath)

    to_download = False
    only_overwrites = False

    if errdata_version_exists and not args.force:
        with open(errdata_version_filepath, 'rt', encoding='utf-8') as file:
            current_errdata_version = file.read()
        if current_errdata_version == latest_errdata_version:
            print("Skipping you already have the latest version", file=sys.stderr)
        else:
            print("Downloading your version is old", file=sys.stderr)
            to_download = True
            only_overwrites = True
    else:
        to_download = True

    if to_download:
        download_book(args, only_overwrites)
        output_errdata_version(errdata_version_filepath, latest_errdata_version)


def output_errdata_version(errdata_version_filepath, latest_errdata):
    with open(errdata_version_filepath, 'wt', encoding='utf-8') as file:
        file.write(latest_errdata)


def download_book(args, only_overwrites=False):
    tree = get_and_parse_html(args.url)
    table_header, table_body = get_table_header_and_body(tree.getroot())
    chapters_with_repetitions = get_chapters_with_repetitions(table_header)
    chapters_parts = get_chapters_parts(chapters_with_repetitions, table_body)
    show_chapters_parts(chapters_parts)
    get_pdfs(args.url, args.directory, chapters_with_repetitions, chapters_parts, only_overwrites)


def get_exactly_one(array, msg):
    if len(array) != 1:
        raise Exception(msg)
    return array[0]


def unwrap(root):
    string_builder = []

    def unwrap_aux(element):
        for node in element.xpath('child::node()'):
            if isinstance(node, lxml.etree._ElementUnicodeResult):
                text = node.strip()
                if text:
                    string_builder.append(text)
            elif isinstance(node, lxml.etree._Element):
                unwrap_aux(node)

    unwrap_aux(root)

    return ' '.join(string_builder)


def get_args():
    default_url = 'http://pages.cs.wisc.edu/~remzi/OSTEP/'
    default_errdata_url = 'http://pages.cs.wisc.edu/~remzi/OSTEP/combined.html'
    default_errdata_filename = ".current_errdata_version"

    parser = argparse.ArgumentParser(description='Get all the pdfs from Operating Systems: Three Easy Pieces')
    parser.add_argument('-d', '--directory', type=str, dest='directory', required=True, help='The output directory')
    parser.add_argument('-u', '--url', type=str, dest='url', default=default_url, required=False,
                        help='The url to OSTEP')
    parser.add_argument('-e', '--errdata-url', type=str, dest='errdata_url', default=default_errdata_url,
                        required=False, help='The url to the errdata of OSTEP')
    parser.add_argument('-f', '--force', dest='force', default=False, required=False, action='store_true',
                        help='Force the download')
    parser.add_argument('-l', '--errdata-filename', type=str, dest="errdata_filename", default=default_errdata_filename,
                        required=False, help="The errdata filename to check if you already have the latest version")

    return parser.parse_args()


def get_and_parse_html(url):
    with urlopen(url) as response:
        if response.status != 200:
            raise Exception(f'HTTP Get request to URL ${url} failed')
        content = response.read().decode('utf-8')

    return lxml.etree.parse(StringIO(content), lxml.etree.HTMLParser())


def get_table_header_and_body(root):
    tables = root.xpath('//table')
    table = tables[len(tables) - 1]
    trows = table.xpath('.//tr')
    return trows[0], trows[1:]


def get_chapters_with_repetitions(table_header):
    bolds = table_header.xpath('.//b')
    headers = []
    for bold in bolds:
        text = bold.text
        if not text:
            if last_header:
                header = last_header
            else:
                raise Exception('First header has no text')
        else:
            header = text.strip()
        headers.append(header)
        last_header = header
    return headers


def get_chapters_parts(headers, trows):
    parts = {}
    for header in headers:
        parts[header] = []

    for trow in trows:
        tds = trow.xpath('.//td')

        if len(tds) != len(headers):
            raise Exception('Numbers of headers not the same as the number of columns')

        for index, td in enumerate(tds):
            header = headers[index]
            anchors = td.xpath('.//a')
            anchors_length = len(anchors)
            if anchors_length == 1:
                parts[header].append(anchors[0].attrib['href'])
            elif anchors_length > 1:
                found_pdf = False
                for anchor in anchors:
                    href = anchor.attrib['href']
                    if re.match(r'(?i).*.pdf$', href):
                        if not found_pdf:
                            found_pdf = True
                        else:
                            raise Exception('Expecting only one pdf')
                        parts[header].append(href)
    return parts


def show_chapters_parts(parts):
    number_pdfs = 0
    for key in parts:
        value = parts[key]
        number_pdfs += len(value)

    print(f'Found {number_pdfs} pdfs', file=sys.stderr)
    pp = pprint.PrettyPrinter(indent=2, stream=sys.stderr)
    pp.pprint(parts)


def get_pdfs(url, directory, chapters_with_repetitions, chapters_parts, only_overwrites):
    chapters = get_ordered_unique(chapters_with_repetitions)

    os.makedirs(directory, exist_ok=True)

    part_identifier = 0
    for chapter in chapters:
        chapter_parts = chapters_parts[chapter]
        for chapter_part in chapter_parts:
            filename = f'{part_identifier:03d}:{chapter}:{chapter_part}'
            parsed_url = urlparse(chapter_part)
            if parsed_url.netloc:
                download_url = chapter_part
            else:
                download_url = f'{url}{chapter_part}'

            save_path = f'{directory}/{filename}'
            if only_overwrites and not os.path.isfile(save_path):
                raise Exception(f'Author added new files or you remove one please remove book folder')

            download_file(download_url, save_path)

            part_identifier += 1


def download_file(url, save_path):
    with urlopen(url) as response, open(save_path, 'wb') as out_file:
        if response.status != 200:
            raise Exception(f'HTTP Get request to URL ${url} failed')
        shutil.copyfileobj(response, out_file)


def get_ordered_unique(chapters):
    unordered_unique = set()
    ordered_unique = []
    for chapter in chapters:
        if chapter in unordered_unique:
            continue
        unordered_unique.add(chapter)
        ordered_unique.append(chapter)
    return ordered_unique


def print_elements(elements):
    if not isinstance(elements, list):
        elements = [elements]

    for element in elements:
        print(lxml.etree.tostring(element, pretty_print=True, method='html'), file=sys.stderr)


if __name__ == '__main__':
    main()
