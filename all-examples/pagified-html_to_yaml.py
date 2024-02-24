import re
import sys
from collections import defaultdict
from more_itertools import peekable
import yaml
from yaml.representer import Representer
from add_page_numbers import reNUMERICEX as RE_NUMERIC_EX

RE_EX_SPLITTER = re.compile(r'(\[\d+\]\t)|([xvi]+\t)|([a-i]\.\t)|(\[A-I\]\t)|(Class [1-5]\t)|(A:|B:\t)')
RE_SPECIAL_CASE_LC_LETTER = re.compile(r'(\[\d+\]\t)|([xvi]+\t)')  # e.g. avoids 'g.' in 'dog.' on p. 67
RE_ROMAN_EX = re.compile(r'[xvi]+')
RE_LETTER_EX = re.compile(r'[a-i]\.')  # also handles the special case example labels
RE_SPECIAL_CASE = re.compile(r'(\[A-I\]\t)|(Class [1-5])|(A|B):')
RE_TABS = re.compile(r'^\t+$')
RE_START_OF_SENT_EX = re.compile(r'<em>(<[a-z_]+>)?[A-Z]')
RE_END_OF_SENT_EX = re.compile(r'\.</em>')
RE_INFO_LINE = re.compile(r'^(<small-caps>[a-zA-Z \-]+</small-caps>[.:])|[A-Z]|<strong>')
RE_END_TAG = re.compile(r'(\[[A-Za-z0-9 \-+=<>[\]]+]$)')
RE_EM_TAG = re.compile(r'<em>')
RE_X_EXPLANATION = re.compile(r'<em>X ?</em>')

yaml.add_representer(defaultdict, Representer.represent_dict)


def process_full_sentence_line(string_list):
    return [i.replace('\t', '').replace('<p>', '').replace('</p>\n', '') for i in string_list
            if i is not None and i != '' and not RE_TABS.search(i)]


def handle_page_50(examples_dict, key, sent):
    insert_sent(examples_dict, key, '[1]-1', None, None, None, '50', sent)
    insert_sent(examples_dict, key, '[1]-2', None, None, None, '50',
                '<strong>3rd sg present tense</strong>	<em>He <u>takes</u> her to school.</em>')
    insert_sent(examples_dict, key, '[1]-3', None, None, None, '50',
                '<strong>plain present tense</strong>	<em>They <u>take</u> her to school.</em>')
    insert_sent(examples_dict, key, '[1]-4', None, None, None, '50',
                '<strong>plain form</strong>	<em>I need to <u>take</u> her to school.</em>')
    insert_sent(examples_dict, key, '[1]-5', None, None, None, '50',
                '<strong>gerund-participle</strong>	<em>We are <u>taking</u> her to school.</em>')
    insert_sent(examples_dict, key, '[1]-6', None, None, None, '50', '<em>They have <u>taken</u> her to school.</em>')


def main(pagified_path, yamlified):
    autodict = lambda: defaultdict(autodict)  # handles generating a nested dictionary
    examples_dict = autodict()
    skip_next = False
    count = 0
    num_ex = None
    roman_num = None
    letter_label = None
    special_label = None
    page = None
    sent = ''
    keys = []
    with open(pagified_path, 'r', encoding="utf-8") as pagified:
        p = peekable(pagified.readlines()[1:])  # skip first line - list of docx files
        for line in p:
            if skip_next:
                print("skipping", line)
                skip_next = False
                continue

            if re.search('<em><small-caps>to', line) is not None:  # formatting change for parsing
                line = line.replace('<em><small-caps>', '<small-caps><em>')

            string_list = process_full_sentence_line(re.split(RE_EX_SPLITTER, line))
            page = re.search(r'[0-9?_]+', string_list[0]).group()

            if page == '52' or page == '67':  # special cases for multiple sentences in a line
                if re.match('<p>!67| 	ii', line) is not None:  # special case on p. 67
                    line = "<p>#67| 	ii		<small-caps>postposing</small-caps>	<em>He'd left in the car all the " \
                           "papers relating to the case.</em>	<em>He'd left all the papers relating to the case in " \
                           "the car.</em></p> "
                    # print("special case p. 67; skipping next line")
                    skip_next = True
                string_list = process_full_sentence_line(re.split(RE_SPECIAL_CASE_LC_LETTER, line))

            print(page, line, string_list, '\n')

            for string in string_list[1:]:
                if RE_NUMERIC_EX.match(string) is not None:  # labels like '[1]'
                    num_ex = string
                    key = 'ex' + str(count)  # FIXME this causes labels in the yaml to jump ahead like ex58 -> ex62
                    count += 1
                    roman_num = None
                    letter_label = None
                    special_label = None
                elif RE_ROMAN_EX.match(string) is not None:  # labels like 'i'
                    roman_num = string
                    letter_label = None
                elif RE_LETTER_EX.match(string) is not None:  # labels like 'a.'
                    letter_label = string
                elif RE_SPECIAL_CASE.match(string) is not None:  # labels like [A], Class 1, A:, B:
                    special_label = string
                else:  # handle the text on the line
                    if string_list[0][0:1] == '#' and RE_EM_TAG.search(string) is not None:  # line with complete sentence and italics
                        if RE_INFO_LINE.match(string):  # appears to be an info line
                            print(line, file=sys.stderr)
                            print(string, file=sys.stderr)
                            continue

                        if RE_X_EXPLANATION.match(string):  # lines like '<em>X </em>entails <em>Y</em>'
                            print(line, file=sys.stderr)
                            continue

                        examples_dict[key]['page'] = page
                        sent = string
                        sent = re.sub(r'([a-z]\.)([A-Z])', r'\1 \2', sent)
                        sent = re.sub(RE_END_TAG, r'\t\1', sent)
                        # print(sent)
                        if p.peek('____')[3:4] == '@':  # the current line has a full sentence, but the next line completes some partial sentence
                            # check if this appears to be an incomplete start of a sentence
                            if re.search(RE_START_OF_SENT_EX, sent) is not None and re.search(RE_END_OF_SENT_EX, sent) is None:  # this is the partial sentence on the line
                                split = re.split(r'@[0-9]+\| |\t|<p>|</p>\n',p.peek())  # removing extra tags
                                split = list(filter(None, split))
                                split = split[0].replace('<em>', ' ')  # extract string & remove italic marker for joining
                                # '#' prefix implies one of the sentences is complete, so there is only one string in split
                                sent = split.join(sent.rsplit('</em>', 1))
                                skip_next = True  # the next line is already processed, so we skip it
                        sent = sent.replace('. </em>', '.</em>')
                        sent = re.sub(r'<sup>\s*([*#%?!])\s*</sup><em>', r'\1<em>', sent)

                        # handle special cases
                        if page == '50' and num_ex == '[1]':
                            num_ex = '[1]-1'
                            sent = sent.replace('<small-caps>primary</small-caps>(', '')
                            handle_page_50(examples_dict, key, sent)
                            continue

                        insert_sent(examples_dict, key, num_ex, roman_num, letter_label, special_label, page, sent)

                    elif string_list[0][0:1] == '!' and re.search(r'<em>', string) is not None:
                        print(string)
                        sent = string
                        sent = re.sub(r'([a-z]\.)([A-Z])', r'\1 \2', sent)
                        # sent = re.sub(r'\[[a-z]+\]$', r'\t\1', sent)
                        if p.peek('____')[3:4] == '@' or p.peek('_______')[3:7] == '#???':
                            # check if this appears to be an incomplete start of a sentence
                            if re.search(RE_START_OF_SENT_EX, sent) is not None:
                                print("appears to be incomplete sentence")
                                split = re.split(r'@[0-9]+\| |\t|<p>|</p>\n', p.peek())
                                split = list(filter(None, split))
                                print(split)

                                if letter_label == 'a.':
                                    split = split[0]
                                    if split[0][0] != '[':
                                        split = split.replace('<em>', ' ')
                                    sent = split.join(sent.rsplit('</em>', 1))
                                elif letter_label == 'b.':
                                    split = ' ' + split[1]
                                    sent = split.join(sent.rsplit('</em>', 1))
                                else:  # appears to be single multi-line sentence
                                    split = split[0]
                                    if split[0][0] == '[':
                                        split = ' ' + split
                                    else:
                                        # replace extra <em> with space, remove double space if necessary
                                        split = split.replace('<em>', ' ').replace('  ', ' ')
                                    sent = split.join(sent.rsplit('</em>', 1))
                                skip_next = True
                                sent = re.sub(r'(\[[A-Za-z0-9 \-\+\=]+\]$)', r'\t\1', sent)
                                sent = sent.replace('. </em>', '.</em>')
                                examples_dict[key]['page'] = page
                                insert_sent(examples_dict, key, num_ex, roman_num, letter_label, special_label, page,
                                            sent)
                        else: # non-sentence
                            print(line, file=sys.stderr)
                    else:  # '!' lines without any italics
                        print(line, file=sys.stderr)

    with open(yamlified, 'w', encoding="utf-8") as yamlified:
        yaml.dump(examples_dict, yamlified, default_style='"', width=float("inf"), sort_keys=False)


def insert_sent(examples_dict, key, num_ex, roman_num, letter, special, page, sent):
    sent = sent.replace('`', '\'')

    k = [key, 'p' + page, num_ex]
    if roman_num is not None:
        k.append(roman_num)
    if letter is not None:
        letter = letter.replace('.','')
        k.append(letter)
    if special is not None:
        special = special.replace(':','')
        k.append(special)
    with open('keys', 'a', encoding='utf-8') as keys:
        flat_key = "_".join(k)
        keys.write(flat_key + '\n')

    if roman_num is None:
        if letter is None:
            if special is None:
                # num_ex
                examples_dict[key][num_ex] = [flat_key, sent]
            else:
                # numex, special
                examples_dict[key][num_ex][special] = [flat_key, sent]
        elif special is None:
            # numex, letter
            examples_dict[key][num_ex][letter] = [flat_key, sent]
        else:
            # numex, letter, special
            if letter not in examples_dict[key][num_ex]:
                examples_dict[key][num_ex][letter] = {}
            examples_dict[key][num_ex][letter][special] = [flat_key, sent]
    else:
        if letter is None:
            if special is None:
                # numex, roman_num
                examples_dict[key][num_ex][roman_num] = [flat_key, sent]
            else:
                # numex, roman_num, special
                if roman_num not in examples_dict[key][num_ex]:
                    examples_dict[key][num_ex][roman_num] = {}
                examples_dict[key][num_ex][roman_num][special] = [flat_key, sent]
        else:
            if roman_num not in examples_dict[key][num_ex]:
                examples_dict[key][num_ex][roman_num] = {}
            if special is None:
                # numex, roman_num, letter
                examples_dict[key][num_ex][roman_num][letter] = [flat_key, sent]
            else:
                # numex, roman_num, letter, special
                if letter not in examples_dict[key][num_ex]:
                    examples_dict[key][num_ex][letter] = {}
                examples_dict[key][num_ex][roman_num][letter][special] = [flat_key, sent]


if __name__ == '__main__':
    pagified_path = 'cge01-02Ex.html'  # change to desired input path
    yamlified_path = 'cge01-02Ex.yaml'  # change to desired output path
    main(pagified_path, yamlified_path)
