#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import re
import os
import json
import unicodedata
import getopt
import codecs


def get_ocr(img_fn, lang, trim_worse_lines=False):
    tmp_file_base = '/tmp/amisOcrGuess'
    tmp_file = tmp_file_base + ".txt"

    cmd = 'tesseract "%s"  "%s" -l %s > /dev/null 2>&1' % (img_fn, tmp_file_base, lang)
    os.system(cmd)
    with open(tmp_file, 'r') as content_file:
        ocr = content_file.read().decode('utf-8')
        lines = ocr.splitlines(False)
        lines = [line.strip() for line in lines]
        lines = filter(None, lines)
        if trim_worse_lines:
            ocr = get_best_line(lines)
        else:
            ocr = '\n'.join(lines)

    return ocr


def get_ocr_guess(img_fn, trim_worse_lines=False):
    ret = {
        'img': img_fn,
        'eng': get_ocr(img_fn, 'eng', trim_worse_lines),
        'cht': get_ocr(img_fn, 'chi_tra', trim_worse_lines)
    }
    return ret


def get_char_category(char):
    '''
        returns the category of the character
        'ne': 'non-english'
        'e': 'english'
        'n': 'number'
        'o': 'others'
    '''
    raw_cate = unicodedata.category(char)
    dic = {
        'Lo': 'ne',  # Letter, other
        'Lu': 'e',  # Letter, uppercase
        'Ll': 'e',  # Letter, lowercase
        'Nd': 'n',  # Number, decimal digit
    }
    cate = dic.get(raw_cate, 'o')
    return cate


def get_score(line):
    if not line:
        return 0

    N = len(line)
    types = [get_char_category(s) for s in line]
    letter_count = [t in ['ne', 'e'] for t in types].count(True)
    type_change_count = [types[i] != types[i + 1] for i in range(len(types) - 1)].count(True)
    letter_rate = 1.0 * letter_count / N
    change_rate = 1.0 * type_change_count / (N - 1) if N > 1 else 0
    score = letter_rate * (1 - change_rate)
    return score


def get_best_line(lines):
    if not lines:
        return ''

    lines_info = []
    for line in lines:
        score = get_score(line)
        lines_info.append({
            'text': line,
            'score': score
        })
    ranking = sorted(lines_info, key=lambda d: d['score'], reverse=True)
    return ranking[0]['text']


def set_output_encoding(encoding='utf-8'):
    '''When piping to the terminal, python knows the encoding needed, and
       sets it automatically. But when piping to another program (for example,
       | less), python can not check the output encoding. In that case, it
       is None. What I am doing here is to catch this situation for both
       stdout and stderr and force the encoding'''
    current = sys.stdout.encoding
    if current is None:
        sys.stdout = codecs.getwriter(encoding)(sys.stdout)
    current = sys.stderr.encoding
    if current is None:
        sys.stderr = codecs.getwriter(encoding)(sys.stderr)


def print_stderr(msg):
    sys.stderr.write(msg + "\n")
    sys.stderr.flush()


if __name__ == '__main__':
    help_msg = '''usage: ocr_guess.py [ -t ] [ -p ] [ -v ] img1 [img2 ...]
       -t: If the OCR result contains multiple lines, pick the most possibly correct line, and trim the rest.
       -p: Output the json with pretty format.
       -v: Verbose mode (using stderr).
        '''

    if len(sys.argv) < 2:
        sys.exit(help_msg)

    options = {}
    try:
        opts, args = getopt.getopt(sys.argv[1:], "tpv", ["help"])
        img_list = args

        for opt, arg in opts:
            if opt in ['--help']:
                sys.exit(help_msg)
            elif opt in ['-t']:
                options['trim_worse_lines'] = True
            elif opt in ['-p']:
                options['pretty_json'] = True
            elif opt in ['-v']:
                options['verbose'] = True

    except getopt.GetoptError:
        sys.exit(help)

    set_output_encoding()
    result = []
    verbose = options.get('verbose', False)
    for img_fn in img_list:
        if verbose:
            print_stderr(img_fn)
        ocr = get_ocr_guess(img_fn, options.get('trim_worse_lines', False))
        eng = ocr['eng']
        cht = ocr['cht']
        result.append(ocr)

    json_args = {}
    if options.get('pretty_json', False):
        json_args.update(dict(
            indent=4,
            separators=(',', ': '),
            sort_keys=True
        ))

    print json.dumps(result, ensure_ascii=False, **json_args)
