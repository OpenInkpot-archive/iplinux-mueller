#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Conversion of Mueller dictionaries to the DICT format
#
# (c) 2006 Mikhail Gusarov <dottedmag@dottedmag.net>
# Based on Andrew Comech <comech@math.sunysb.edu> work.
#
# GPLv2
#

import re, sys, textwrap

# -- Transcription conversion --

#
# Mapping Mueller's transcription characters to IPA alphabet.
#
letters = {
    '\x41' : u'\N{LATIN SMALL LETTER ALPHA}', # A
    '\x44' : u'\N{LATIN SMALL LETTER ETH}', # D
    '\x45' : u'e', #E
    '\x49' : u'\N{LATIN LETTER SMALL CAPITAL I}', # I
    '\x4E' : u'\N{LATIN SMALL LETTER ENG}', # N
    '\x51' : u'\N{LATIN SMALL LETTER AE}', # Q
    '\x53' : u'\N{LATIN SMALL LETTER ESH}', # S
    '\x54' : u'\N{GREEK SMALL LETTER THETA}', # T
    '\x5A' : u'\N{LATIN SMALL LETTER EZH}', # Z
    '\x65' : u'\N{LATIN SMALL LETTER OPEN E}', # e
    '\x75' : u'\N{LATIN SMALL LETTER UPSILON}', # u
    '\x8D' : u'\N{LATIN SMALL LETTER REVERSED E}',
    '\xAB' : u'\N{LATIN SMALL LETTER REVERSED OPEN E}',
    '\xC3' : u'\N{LATIN SMALL LETTER TURNED V}',
    '\xC7' : u'\N{SOUTH EAST ARROW}',
    '\xC8' : u'\N{NORTH EAST ARROW}',
    '\xF9' : u':',
}
 
def transcription_to_ipa(s):
    """Converts Mueller's transcription (bytestring) to the IPA one (Unicode)"""
    return u''.join(map(lambda c: letters.get(c, c), s))

# -- Parsing the single word

line_re = re.compile('^(.*?)  (.*)')
transcription_re = re.compile('\[(.*?)\]')

def parse_line(s):
    """Given string from dictionary returns pair (word, article).

    word is the word defined (Unicode string). Article is the source
    article as Unicode string, with transcription converted to IPA"""

    res = re.match(line_re, s)
    if not res:
        raise RuntimeError("Malformed line %s" % s.encode("UTF-8"))

    (word, article) = res.groups()

    # Splits article to the parts, converting transcription to Unicode
    article_parts = []

    last_processed = 0
    for r in re.finditer(transcription_re, article):
        if r.start() > last_processed:
            article_parts.append(article[last_processed:r.start()].decode("KOI8-R"))
        article_parts.append(transcription_to_ipa(article[r.start():r.end()]))
        last_processed = r.end()

    if last_processed != len(article):
        article_parts.append(article[last_processed:len(article)].decode("KOI8-R"))

    return word.decode("KOI8-R"), u"".join(article_parts)

# -- Formatting single text block with indentation

TEXT_WIDTH = 75
INDENT_WIDTH = 3

# list-name -> (head of list regexp, maximum length)
list_types = { 'r': (re.compile('_[IV]{1,3}'), 4),
               'd': (re.compile('\d{1,2}\.'), 3),
               'n': (re.compile('\d{1,2}>'), 3),
               'a': (re.compile(u'[а-я]>'), 3) }

def format_block(s, indentation, header, header_width):
    s = s.strip()
    header = header

    first_line = ((INDENT_WIDTH*indentation) * u' ') + header.ljust(header_width)
    other_lines = (INDENT_WIDTH*indentation + header_width) * u' '

    w = textwrap.TextWrapper(width = TEXT_WIDTH,
                             initial_indent = first_line,
                             subsequent_indent = other_lines)

    return u"\n".join(w.wrap(s))

# -- Converting the word into DICT-formed article

def convert_line(s):
    """Given the line from dictionary, format the article with newlines
    and indentation, convert everything to UTF-8, and wrap to page
    width"""

    (word, article) = parse_line(s)

    # Find all list heads occurences
    list_heads = []
    for list_name, (list_re, list_header_width) in list_types.iteritems():
        for i in re.finditer(list_re, article):
            head = i.group()
            if head.endswith(u'>'):
                head = head[:-1] + u')'
            list_heads.append((i.start(), i.end(), list_name, head))

    list_heads.sort(lambda x, y: cmp(x[0], y[0]))

    # Figure out the lists indentation
    list_levels = {}
    level = 0
    for list_head in list_heads:
        if not list_levels.has_key(list_head[2]):
           list_levels[list_head[2]] = level
           level += 1

    # Indent and encode each text block
    result = []
    if len(list_heads) == 0:
        result.append(format_block(article, 0, '', 0))
    else:
        if list_heads[0][0] > 0:
            result.append(format_block(article[0:list_heads[0][0]], 0, '', 0))
        for i in xrange(0, len(list_heads)-1):
            list_type = list_heads[i][2]
            result.append(format_block(article[list_heads[i][1]:list_heads[i+1][0]],
                                       list_levels[list_type],
                                       list_heads[i][3], list_types[list_type][1]))
        list_type = list_heads[-1][2]
        result.append(format_block(article[list_heads[-1][1]:len(s)],
                                   list_levels[list_type],
                                   list_heads[-1][3], list_types[list_type][1]))

    return word, result

def convert_dictionary():
    previous_letter = ''
    copyright_line = 1
    sys.stderr.write('Converting dictionary: ')
    for s in sys.stdin:
        if s[0].isalpha() and previous_letter != s[0].lower():
            previous_letter = s[0].lower()
            sys.stderr.write(s[0].lower())
        if s.startswith(" (C)") and copyright_line:
            copyright_line = 0
            sys.stdout.write("%h 00-database-info\n%d\n")
            sys.stdout.write("\n".join(textwrap.wrap(s, 75)))
        if s.startswith(" (C)"):
            continue
        (word, article_lines) = convert_line(s)
        sys.stdout.write("%h " + word.encode("UTF-8") + "\n%d\n")
        for l in article_lines:
            sys.stdout.write("   ")
            sys.stdout.write(l.encode("UTF-8"))
            sys.stdout.write("\n")
    sys.stderr.write('\ndone\n')

if __name__ == '__main__':
    convert_dictionary()
