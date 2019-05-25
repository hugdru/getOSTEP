from urllib.request import urlopen
from urllib.parse import urlparse
from io import StringIO
from lxml import etree
import argparse
import shutil
import pprint
import sys
import re
import os

def main():
    args = get_args()
    tree = getAndParseHtml(args.url)
    table_header, table_body = get_table_header_and_body(tree.getroot())
    chapters_with_repetitions = get_chapters_with_repetitions(table_header)
    chapters_parts = get_chapters_parts(chapters_with_repetitions, table_body)
    show_chapters_parts(chapters_parts)
    get_pdfs(args.url, args.directory, chapters_with_repetitions, chapters_parts)

def get_args():
    default_url = 'http://pages.cs.wisc.edu/~remzi/OSTEP/'
    parser = argparse.ArgumentParser(description='Get all the pdfs from Operating Systems: Three Easy Pieces')
    parser.add_argument('-d', '--directory', type=str, dest="directory", required=True, help="The output directory")
    parser.add_argument('-u', '--url', type=str, dest="url", default=default_url, required=False, help="The url to the Operating Systems: Three Easy Pieces")
    return parser.parse_args()

def getAndParseHtml(url):
    with urlopen(url) as response:
        if response.status != 200:
            raise Exception(f'HTTP Get request to URL ${url} failed')
        content = response.read().decode('utf-8')

    return etree.parse(StringIO(content), etree.HTMLParser())


def get_table_header_and_body(root):
    tables = root.xpath('//table')
    table = tables[len(tables)-1]
    trows = table.xpath(".//tr")
    return trows[0], trows[1:]

def get_chapters_with_repetitions(table_header):
    bolds = table_header.xpath(".//b")
    headers = []
    for bold in bolds:
        text = bold.text
        if not text:
            if last_header:
                header = last_header
            else:
                raise Exception("First header has no text")
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
        tds = trow.xpath(".//td")

        if (len(tds) != len(headers)):
            raise Exception("Numbers of headers not the same as the number of columns")

        for index, td in enumerate(tds):
            header = headers[index]
            anchors = td.xpath(".//a")
            anchors_length = len(anchors)
            if (anchors_length == 1):
                parts[header].append(anchors[0].attrib["href"])
            elif anchors_length > 1:
                foundPdf = False
                for anchor in anchors:
                    href = anchor.attrib["href"]
                    if re.match(r"(?i).*.pdf$", href):
                        if not foundPdf:
                            foundPdf = True
                        else:
                            raise Exception("Was expecting only one pdf")
                        parts[header].append(href)
    return parts

def show_chapters_parts(parts):
    number_pdfs=0
    for key in parts:
        value = parts[key]
        number_pdfs += len(value)

    print(f"Found {number_pdfs} pdfs", file=sys.stderr)
    pp = pprint.PrettyPrinter(indent=2, stream=sys.stderr)
    pp.pprint(parts)


def get_pdfs(url, directory, chapters_with_repetitions, chapters_parts):

    chapters = ordered_unique(chapters_with_repetitions)

    os.makedirs(directory)

    part_identifier = 0
    for chapter in chapters:
        chapter_parts = chapters_parts[chapter]
        for chapter_part in chapter_parts:
            filename = f'{part_identifier:03d}:{chapter}:{chapter_part}'
            parsed_url = urlparse(chapter_part)
            if (parsed_url.netloc):
                download_url = chapter_part
            else:
                download_url = f'{url}{chapter_part}'

            download_file(download_url, f"{directory}/{filename}")

            part_identifier += 1

def download_file(url, save_path):
    with urlopen(url) as response, open(save_path, 'wb') as out_file:
        if response.status != 200:
            raise Exception(f'HTTP Get request to URL ${url} failed')
        shutil.copyfileobj(response, out_file)

def ordered_unique(chapters):
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
        print(etree.tostring(element, pretty_print=True, method="html"), file=sys.stderr)


if __name__ == "__main__":
    main()
