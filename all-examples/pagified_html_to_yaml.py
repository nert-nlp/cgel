import re
import sys
from collections import defaultdict
from more_itertools import peekable
import yaml
from yaml.representer import Representer
from add_page_numbers import reNUMERICEX as RE_NUMERIC_EX, reSENTTERMINAL as RE_SENT_TERMINAL

RE_EX_SPLITTER = re.compile(r'(\[\d+\]\t)|([xvi]+\t)|((?<!\w)[a-i]\.\t)|(\[[A-Z]\]\t)|(Class [1-5]\t)')
RE_ROMAN_EX = re.compile(r'[xvi]+(?!\.)')
RE_LETTER_EX = re.compile(r'(?<!\w)[a-i]\.')  # also handles the special case example labels
RE_SPECIAL_CASE = re.compile(r'(\[[A-Z]\])|(Class [1-5])')
RE_ALL_TABS = re.compile(r'^\t+$')
RE_MULT_TABS = re.compile(r'\t{2,}')
RE_START_OF_SENT_EX = re.compile(r'<em>(<[a-z_]+>)?[A-Za-z]')
RE_END_OF_SENT_EX = re.compile(r'\.</em>')
RE_INFO_LINE = re.compile(r'^(<small-caps>[a-zA-Z \-]+</small-caps>[.:])|<strong>')
RE_END_TAG = re.compile(r'(\[[A-Za-z0-9 \-+=<>\[\]]+]$)')
RE_EM_TAG = re.compile(r'<em>')
RE_X_EXPLANATION = re.compile(r'<em>X ?</em>')

yaml.add_representer(defaultdict, Representer.represent_dict)

def mk_double_quote(dumper, data):
    """If string contains ' and has to be quoted, use double quotes rather than '' escaping"""
    if "'" in data and (':' in data or (not data[0].isalnum() and data[0]!='<')):
        return dumper.represent_scalar('tag:yaml.org,2002:str', data, style='"')
    else:
        return dumper.represent_scalar('tag:yaml.org,2002:str', data, style='')

yaml.add_representer(str, mk_double_quote)

def process_full_sentence_line(string_list):
    x = [RE_MULT_TABS.sub('\t', i.replace('<p>', '').replace('</p>\n', '')).strip() for i in string_list
            if i is not None and i != '' and not RE_ALL_TABS.search(i)]
    assert not any('\t\t' in y for y in x),x
    return x


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
                #print("skipping", line)
                skip_next = False
                continue

            line = re.sub(r'<a id="[^"]*"></a>', '', line) # hidden bookmarks are created by Word for some reason

            line = line.replace('</em>\t(\t<em>', ' ').replace('</em>\t(\t[', '</em> [')  # second part of sentence in curly braces
            line = line.replace('\t)', '\t').replace('(\t', '\t')  # at the beginning/end of a sentence to indicate a grouping with large curly braces
            line = line.replace('\t</em>)', '</em>\t').replace('(<em>\t', '\t<em>')
            line = line.replace('\t</small-caps>', '</small-caps>\t')
            line = line.replace(' </small-caps>', '</small-caps> ')
            line = line.replace('<em>\t', '\t<em>').replace('<em>\t', '\t<em>').replace('<em>\t', '\t<em>')
            line = line.replace('\t</em>', '</em>\t').replace('\t</em>', '</em>\t')
            line = line.replace('</u><em><u>', '<em>').replace('</u></em><u>', '</em>')
            line = line.replace('<em> ', ' <em>').replace('<em> ', ' <em>').replace('<em> ', ' <em>')    # twice for "<em>  " etc.
            line = line.replace(' </em>', '</em> ').replace(' </em>', '</em> ').replace(' </em>', '</em> ') # twice for "  </em>" etc.
            line = line.replace('<em></em>', '').replace('</em> <em>', ' ')
            line = line.replace(' (=[', '\t(=[')    # cross-reference to a previous example (=[10])
            line = line.replace('subjectauxiliary', 'subject–auxiliary')
            line = re.sub(r'\b([AB]:)\s+', r'\1 ', line)   # dialogue interlocutors (usually both turns on the same line, but not always)
            if '#41' in line:
                print(line)

            if re.search('<em><small-caps>to', line) is not None:  # formatting change for parsing
                line = line.replace('<em><small-caps>', '<small-caps><em>')

            # b., c., etc. must not come immediately after a bracketed number
            assert not re.search(r'^[^\|]+\|\s+\[[0-9]+\]\s+[b-i]\.', line),line

            if page == '302' and num_ex == '[21]':
                line = line.replace('ii\tb.', 'ii\ta.') # numbering error in PDF
            
            if page == '889' and num_ex == '[59]':
                # single/multi-variable echo questions: two B: responses
                line = line.replace('B:', 'B1:', 1) # replace 1st temporarily
                line = line.replace('\tB:', ' /')  # replace 2nd
                line = line.replace('B1:', 'B:')    # restore 1st

            # b., c., etc. must not come immediately after a roman numeral
            assert not re.search(r'^[^\|]+\|\s+[ivx]+\s+[b-i]\.', line),line

            assert not re.search(r'^<p>#.*\t[b-g]\s', line),line
            
            # two consecutive tags must not be the same
            assert not (m := re.search(r'(</?[A-Za-z-]+>)[^<]+\1', line)),(m.group(0),line)

            # workaround: add_page_numbers.py now applies "#" more liberally, but the code in the loop below
            # relies on "!" being used for any line without a sentence terminal for processing subsequent
            # continuation lines ("@"). So restore "!" for these cases.
            if line.startswith('<p>#') and p.peek(default='').startswith('<p>@'):
                mainpart = '\t'.join(line.split('\t')[3:]).strip()
                mainpart = mainpart.replace('   ','\t').replace('</p>','').replace('</em>','').replace('</u>','').replace('</double-u>','')
                mainpart = re.sub(r'(^|\t)[a-z]\.\t', '\t\t', mainpart)
                if not RE_SENT_TERMINAL.search(mainpart):
                    line = '<p>!' + line[4:]

            if '!67| 	ii\t' in line:
                line = "<p>#67| 	ii		<small-caps>postposing</small-caps>	<em>He gave to charity all the " \
                           "money she had left him.</em>	<em>He gave all the money " \
                           "she had left him to charity.</em>"
                # print("special case p. 67; skipping next line")
                skip_next = True
            if '#109| [51]		i		A. <em>Ought we to invite them both?</em>	B. <em>Yes,' in line:
                line = line.replace('A.', 'A:').replace('B.', 'B:') # dialogue interlocutors usually followed by colon
            if '#589| [50]			<small-caps>precedes</small-caps>?		<small-caps>adjacent</small-caps>?' in line:
                # contains "?" (sentence terminal) so add_page_numbers doesn't recognize it as header row
                line = line.replace('#589|','!589|')
            if '<em>' not in line and '<small-caps>' in line and line.startswith('<p>#'):
                line = '<p>!' + line[3:]
            if '#934| [31]				<small-caps>1st inclusive' in line:
                line = '<p>!' + line[3:]
            if '#1516| [19]				<small-caps>the fused-head construction</small-caps>' in line:
                line = '<p>!' + line[3:]
            if '#1516| [20]				<small-caps>the pro-nominal</small-caps>' in line:
                line = '<p>!' + line[3:]
            if '#1524| [15]				<small-caps>primary forms of</small-caps>' in line:
                line = '<p>!' + line[3:]
            if '#1524| [16]				<small-caps>secondary forms of</small-caps>' in line:
                line = '<p>!' + line[3:]
            if '#1529| [37]				<small-caps>ellipsis or pro-form</small-caps>' in line:
                line = '<p>!' + line[3:]

            # some examples starting with 2-word phrases
            ADD_THESE = [
                '!340| 	i	a.	*<em>these <u>equipment</u>',
                '!388| [49]		i	a.	<em>either parent</em>',
                '!529| 	ii		<em>the <u>rich</u>',
                '!933| [28]		i		<em>Be warned!</em>',
                '!1040| 	ii		<em>the curtain</em>',
                '!1041| 	iii		<em>problems</em> [<em><u>to which</u> he already knows',
                '!1043| 	ii		<em>the student</em>',
                '!1328| 	ii	a.	<em>the <u>civic</u>, <u>school</u>,'
            ]
            for this in ADD_THESE:
                if this in line:
                    line = line[:line.index('!')] + '#' + line[line.index('!')+1:]
                    break

            string_list = process_full_sentence_line(re.split(RE_EX_SPLITTER, line))
            page = re.search(r'[0-9?_]+', string_list[0]).group()

            
            for string in string_list[1:]:
                assert '\t\t' not in string
                if RE_NUMERIC_EX.match(string) is not None:  # labels like '[1]'
                    num_ex = string
                    key = f'ex{len(examples_dict)+1:05}'
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
                    if (page=='1169' and num_ex=='[26]'):
                        continue    # lexical list
                    elif (page=='1232' and num_ex=='[29]'):
                        continue    # lexical list

                    if string_list[0][0:1] == '#' and (True or RE_EM_TAG.search(string) is not None):  # line with italics
                        if RE_INFO_LINE.match(string):  # appears to be an info line
                            #print(line, file=sys.stderr)
                            #print(string, file=sys.stderr)
                            continue

                        if RE_X_EXPLANATION.match(string):  # lines like '<em>X </em>entails <em>Y</em>'
                            #print(line, file=sys.stderr)
                            continue

                        if page == '53' and num_ex == '[2]':
                            continue    # this is a visual example with a special layout. ignore
                        elif page == '215':
                            continue
                        elif page == '216' and num_ex == '[2]':
                            continue    # same
                        elif page in ('579','580'):
                            continue    # same
                        elif page == '277' and num_ex == '[16]':
                            continue    # small caps roman numerals and VP templates
                        elif page == '286' and num_ex == '[44]':
                            continue    # small caps roman numerals and VP templates
                        elif page == '246' and num_ex == '[2]':
                           continue    # contains special metalinguistic markers
                        elif (page == '492' and num_ex == '[25]') or (page == '499' and num_ex == '[50]'):
                            continue    # complicated layout with curly braces, skip for now
                        elif page == '122' and num_ex == '[17]':
                            continue    # this is a discussion of sentence entailments
                        elif (page=='480' and num_ex=='[66]') or (page=='481' and num_ex=='[67]'):
                            continue    # genitive phrases with phonetic transcription
                        elif (page=='940' and num_ex=='[44]'):
                            continue    # question formulae, not complete constituents
                        elif (page=='1002' and num_ex=='[23]'):
                            continue    # a lexical list
                        elif (page=='1231' and num_ex in ('[24]', '[25]')):
                            continue    # lexical lists

                        #if page=='543'

                        examples_dict[key]['page'] = page
                        sent = string
                        sent = re.sub(r'([a-z]\.)([A-Z])', r'\1 \2', sent)
                        #sent = re.sub(RE_END_TAG, r'\t\1', sent)
                        assert '\t\t' not in sent,sent
                        assert '???' not in sent,sent
                        
                        # print(sent)
                        if p.peek('____')[3:4] == '@':  # the current line has a full sentence, but the next line completes some partial sentence
                            # check if this appears to be an incomplete start of a sentence
                            line2 = p.peek()
                            line2 = re.sub(r'<a id="[^"]*"></a>', '', line2)
                            if re.search(r'\|\s*B:\s+', line2):
                                sent += ' ' + line2[line2.index('|')+1:].strip().replace('B:\t', 'B: ').replace('</p>','')
                                skip_next = True
                            elif re.search(RE_START_OF_SENT_EX, sent) is not None and re.search(RE_END_OF_SENT_EX, sent) is None:  # this is the partial sentence on the line
                                split = re.split(r'@[0-9]+\| |\t|<p>|</p>\n',line2)  # removing extra tags
                                split = list(filter(None, split))
                                split = split[0].replace('<em>', ' ', 1)  # extract string & remove italic marker for joining
                                # '#' prefix implies one of the sentences is complete, so there is only one string in split
                                # ^ no longer true after updates to add_page_numbers.py so we have a workaround above
                                sent = split.join(sent.rsplit('</em>', 1))
                                skip_next = True  # the next line is already processed, so we skip it
                        sent = sent.replace('. </em>', '.</em>').replace('? </em>', '?</em>')
                        sent = re.sub(r'<sup>\s*([*#%?!])\s*</sup>(\[?)(<em>|<u>|<double-u>|sg|pl)', r'\1\2\3', sent)
                        assert '\t\t' not in sent,sent
                        assert '???' not in sent,sent
                        assert '<sup>?</sup>' not in sent,sent

                        # handle special cases
                        if page == '50' and num_ex == '[1]':
                            num_ex = '[1]-1'
                            sent = sent.replace('<small-caps>primary</small-caps>(', '')
                            handle_page_50(examples_dict, key, sent)
                            continue

                        insert_sent(examples_dict, key, num_ex, roman_num, letter_label, special_label, page, sent)

                    elif string_list[0][0:1] == '!' and re.search(r'<em>', string) is not None:
                        
                        #print(string)
                        sent = string
                        sent = re.sub(r'([a-z]\.)([A-Z])', r'\1 \2', sent)
                        # sent = re.sub(r'\[[a-z]+\]$', r'\t\1', sent)
                        if p.peek('____')[3:4] == '@' or p.peek('_______')[3:7] == '#???':
                            # check if this appears to be an incomplete start of a sentence
                            if re.search(RE_START_OF_SENT_EX, sent) is not None:
                                
                                #print("appears to be incomplete sentence")
                                parts = re.split(r'@[0-9]+\| |\t|<p>|</p>\n', p.peek())
                                parts = list(filter(None, parts))

                                assert letter_label in (None,'a.','b.') or re.search(r'^[a-z]\.', letter_label) is not None,(letter_label,page,num_ex) # continuation of a. column, b. column, or full-width column
                                split = parts[1 if letter_label=='b.' else 0]

                                if 'B:' in split and ((page=='714' and 'twice a week' in split) or (page=='890' and 'finally solved what?' in split)):
                                    split = split.replace('B: <em>', 'B: <em><em>').replace('B:<em> ', 'B: <em><em>')  # hack to ensure correct <em> isn't removed from B: part

                                split = ' ' + re.sub(r'(?<![\[/<>])\s*<em>(?![\.!\?])', ' ', split).lstrip()
                                firstTag = (split.split('<', 1) + [''])[1]  # part of continuation column beginning with tag name
                                if '<em>' in sent and (split.lstrip().startswith(('[', '(')) or firstTag.startswith('double-u')):
                                    # in the continuation, italics are implied by <double-u> instead of <em>; need to end the <em> from the first part
                                    split = '</em>' + split

                                if sent.startswith(('[<em>','*[<em>','#[<em>','%[<em>','?[<em>','![<em>')) and sent.endswith('</em>]'):
                                    # fully bracketed first line of a multiline sentence
                                    sent += '<em>' + split
                                else:   # insert `split` into `sent` before last '</em>'
                                    sent = split.join(sent.rsplit('</em>', 1))

                                skip_next = True
                                assert '<em>]' not in sent,(sent,string)
                                assert '] .<' not in sent and '[ of' not in sent,(page,sent)
                                sent = re.sub(r'(\[[A-Za-z0-9 \-\+\=]+\]$)', r'\t\1', sent)
                                sent = sent.replace('. </em>', '.</em>').replace('? </em>', '?</em>')
                                sent = re.sub(r'<sup>\s*([*#%?!])\s*</sup><em>', r'\1<em>', sent)
                                assert '<sup>?</sup>' not in sent,sent

                                examples_dict[key]['page'] = page
                                insert_sent(examples_dict, key, num_ex, roman_num, letter_label, special_label, page,
                                            sent)
                        else: # non-sentence
                            pass #print(line, file=sys.stderr)
                    else:  # '!' lines without any italics
                        pass #print(line, file=sys.stderr)

    with open(yamlified, 'w', encoding="utf-8") as yamlified:
        yaml.dump(examples_dict, yamlified, #default_style='"', 
                  width=float("inf"), sort_keys=False)


def insert_sent(examples_dict, key, num_ex, roman_num, letter, special, page, sent):
    sent = sent.replace('Ph. D.', 'Ph.D.')
    sent = sent.replace('`', '\'')
    sent = sent.replace('≡', '')    # on p. 359 this is used as a semantic relation between examples
    sent = sent.replace(' </u> ', '</u> ')
    assert '<p>' not in sent
    assert '</p>' not in sent,sent
    assert '???' not in sent,sent
    assert '<em></em>' not in sent,sent
    assert '] .<' not in sent and '[ of' not in sent,(page,sent)
    
    sent = sent.replace(']  </em>[', ']<em> </em>[')
    if sent.endswith('</em>].') or sent.endswith('</em>).'):
        sent = sent[:-1] + '<em>.</em>'

    # two consecutive tags must not be the same
    assert not (m := re.search(r'(</?[A-Za-z-]+>)[^<]+\1', sent)),(page,m.group(0),sent)

    # a case of hyphenation
    if page == '319' and 'ma-' in sent:
        sent = sent.replace('ma-</u> <u>jor', 'major')

    if page == '130' and num_ex == '[16]':  # Chronicles of history layout with "YEAR\tEVENT"
        sent = sent.replace('1434\t', '1434: ').replace('1435\t', '1435: ').replace('1438\t', '1438: ')
        assert 'Cosimo' in sent,sent

    k = [key, 'p' + page, num_ex]
    if roman_num is not None:
        k.append(roman_num)
    if letter is not None:
        letter = letter.replace('.','')
        k.append(letter)
    if special is not None:
        special = special.replace(':','')
        k.append(special)
    with open('keys', 'a', encoding='utf-8') as keys:   # TODO: do we need this external log of keys?
        flat_key = "_".join(k)
        keys.write(flat_key + '\n')

    #contents = [flat_key, sent]
    contents = [flat_key] + list(filter(lambda x: x!='', map(str.strip, re.split(r'\t|   ', sent))))   # \t separates columns. a few examples e.g. Ch. 3 pp. 131 & 135 have 3-space separators

    assert '<em>' not in contents,contents
    assert '</em>' not in contents,contents

    #if flat_key=='ex01011_p540_[34]_iii_a':
    # if page=='540' and num_ex=='[34]':
    #    print(contents)
    if len(contents)>2: # sequence is: exampleID preTag* main+ postTag*
        section = 'pre'
        for i,part in enumerate(contents):
            if i==0: continue   # example ID
            elif part.startswith(('<small-caps>','<strong>')):
                assert section=='pre',(part,contents)
                contents[i] = '<preTag>' + part + '</preTag>'
            elif section=='pre' and i==1 and (page,num_ex) in {('108','[48]'), ('108','[49]'), ('994','[3]')}:
                contents[i] = '<preTag>' + part + '</preTag>'    # no formatting markup for pre-tag
            elif section=='pre' and 1<=i<=2 and page=='1323' and num_ex=='[3]':
                contents[i] = '<preTag><em>' + part.replace('<em>','') + '</em></preTag>'
            elif section=='pre':
                section = 'main'    # first of possibly multiple main sentence columns
                if page=='1323' and num_ex=='[3]':
                    part = '<em>' + part
                    contents[i] = part
                assert re.search(r'^([AB]: )?[*!?#%]?\[?\(?(<em>|<double-u>)', part) or part in ('[not possible]','[No antecedent]'),contents
                if part.endswith('</em>.'):
                    contents[i] = part[:-6] + '.</em>'
                elif part.endswith('</em>...'):
                    contents[i] = part[:-8] + '...</em>'
                elif not part.endswith(('</em>',']',')')) and part!='A:':  # italics continue on the next column
                    if '<em>' in part and '</em>' in part and part.rindex('<em>') < part.rindex('</em>'):
                        assert part.endswith((']', '].', ')', ').')),(flat_key,part,contents)
                    elif part!='[not possible]' and not part.startswith(('A: ','B: ')):
                        contents[i] = part + '</em>'
            elif section in ('main','post') and part.startswith(('[', '(=')) and not part.startswith(('[<em><u>What</u> a waste of time</em>] ','[<em><u>These two</u></em>]', "[<em><u>That</u></em>]<em>'s not true.", "[<em><u>Those</u> who broke the law</em>]")):
                section = 'post'
                contents[i] = '<postTag>' + part + '</postTag>'
            elif section=='post': # and page=='486' and part in ('singular','plural'):
                part_clean = re.sub(r'</?su[bp]>', part, '')
                assert ' ' not in part and '<' not in part_clean and '>' not in part_clean,(part,contents)
                section = 'post'
                contents[i] = '<postTag>' + part + '</postTag>'
            elif section=='main':   # we've already seen a previous example
                if part.endswith('</em>.'):
                    contents[i] = part[:-6] + '.</em>'
                if not re.search(r'^[*!?#%]?\[?\(?(<em>|<double-u>)', part):
                    if part.startswith(('A: ', 'B: ', 'B (Jill): ')):
                        continue    # turn of a dialogue
                    elif ' ' not in part and '<' not in part and '>' not in part:
                        # single-word postTag as in feature matrices?
                        section = 'post'
                        contents[i] = '<postTag>' + part + '</postTag>'
                    elif part.startswith(('Comp of', 'intransitive ', 'monotransitive ')):
                        section = 'post'
                        contents[i] = '<postTag>' + part + '</postTag>'
                    elif part[0].isalpha() or part.startswith('<u>') and part[3].isalpha():   # subsequent column where italics carry over from previous column
                        part = '<em>' + part
                        contents[i] = part
                    else:
                        if page=='486' and part in ('1st','2nd','3rd'):
                            section = 'post'
                            contents[i] = '/postTag>' + part + '</postTag>'
                        elif ('[' in part and ']' in part) or ('“' in part and '”' in part):
                            section = 'post'
                            contents[i] = '<postTag>' + part + '</postTag>'
                        else:
                            #print('Should have <em>?:', part+'\n'+sent, file=sys.stderr)
                            assert False,part
                if part.endswith('</em>.'):
                    contents[i] = contents[i][:-6] + '.</em>'
                elif part.endswith('</em>...'):
                    contents[i] = part[:-8] + '...</em>'
                elif re.search(r'^[*!?#%]?\[?\(?<em>', part) and not part.endswith(('</em>',']',')')):  # italics continue on the next column
                    contents[i] = part + '</em>'   # TODO should this be added earlier when breaking columns?
            else:
                assert False,(section,part)
    else:
        if not contents[1].startswith(('[Knock on door] <em>', '[Knock at the door] <em>', '[viewing a photograph] <em>', '[no', '[pre-empted', '[Pointing', '[Host')) and contents[1]!='__':
            assert re.search(r'^(A: )?[*!?#%]?\[?\(?(<em>|<double-u>)', contents[1]) or contents[1].startswith('<u>(<em>'),contents
            if contents[1].endswith('</em>.'):
                contents[1] = contents[1][:-6] + '.</em>'
            elif contents[1].endswith('</em>...'):
                contents[1] = contents[1][:-8] + '...</em>'
            elif contents[1].endswith('] ...'):
                contents[1] = contents[1][:-3] + '<em>...</em>'
            elif contents[1].endswith('</em>]]].'):
                contents[1] = contents[1][:-1] + '<em>.</em>'
            elif not contents[1].endswith(('>', ']', ')')):
                contents[1] += '</em>'

    # join together dialogues
    for i in range(len(contents)-1, 1, -1): # working from the end, concatenate turns to previous turns
        # (note that a few dialogues are 3 or 4 turns, alternating between A and B)
        x = contents[i]
        if x.startswith(('A: ', 'B: ', 'B (Jill): ')):
            assert len(contents)>=3,contents
            if i>=2:
                # non-initial turn
                assert contents[i-1].startswith('A: ' if x.startswith('B') else 'B: ')
                contents[i-1] += ' ' + x
                contents[i] = ''
    contents = list(filter(lambda x: x!='', contents))

    # validation
    if flat_key not in ('ex00309_p188_[30]', 'ex00700_p386_[44]_iv_b', 'ex00700_p386_[44]_v_a'):
        for i,x in enumerate(contents[1:], start=1): 
            assert x not in {'A:','B:'},flat_key

            if x=='__': # empty paradigm slot - to avoid confusion with gap, substitute explicit filler
                if 'p546_[31]_i_b' in flat_key or 'p546_[31]_iv_b' in flat_key:
                   x = '[no counterpart]'
                   contents[i] = x
                else:
                    assert False,(x,flat_key)

            # every item after the ex ID should have...
            # an opening tag
            assert re.search(r'^(A: )?[*!?#%]?\[?\(?<', x) or x.startswith(('[no ','[Knock on','[Knock at', '[viewing ', '[Pointing', '[Host')) or x.endswith((']', '].', ')')),(x,contents)
            # a closing tag
            if '<preTag>' in x:
                assert x.endswith('</preTag>')
            elif '<postTag>' in x:
                assert x.endswith('</postTag>')
            elif x.endswith('</double-u>'):
                assert '</em>' in x,(x,contents) # TODO: for some reason <double-u> is not inside <em>
            else:
                assert x.endswith(('</em>', '</em>]', '</double-u>')) or x.startswith('[no ') or x.endswith((']', '].', ')', ').')),contents

            assert '  ' not in x,contents

            assert x.count('[')==x.count(']'),(flat_key,x)
            assert x.count('(')==x.count(')'),(flat_key,x)
            assert x.count('<em>')==x.count('</em>'),(flat_key,x)
            assert x.count('<u>')==x.count('</u>'),(flat_key,x)
            assert x.count('<double-u>')==x.count('</double-u>'),(flat_key,x)
            assert x.count('<sub>')==x.count('</sub>'),(flat_key,x)
            assert x.count('<small-caps>')==x.count('</small-caps>'),(flat_key,x)
            assert x.count('<strong>')==x.count('</strong>'),(flat_key,x)
            assert x.count('<preTag>')==x.count('</preTag>'),(flat_key,x)
            assert x.count('<postTag>')==x.count('</postTag>'),(flat_key,x)

            assert '>,<em>' not in x,(flat_key,x)
            assert '>,<u>' not in x,(flat_key,x)
            assert '>,<double-u>' not in x,(flat_key,x)
            if ']</u>' in x:
                print('[_]', flat_key,x)    # superfluous underlining of close bracket

            if not x.startswith(('<preTag>','<postTag>')):
                tagless = re.sub(r'<[^>]+>', '', x)
                assert tagless.strip()==tagless
                # check for incomplete-looking sentence
                if 15 < len(tagless) and re.search(r'^[A-Z].*[a-z]$', tagless):
                    print(flat_key,tagless)

            assert x!='<em></em>',contents

    if roman_num is None:
        if letter is None:
            if special is None:
                # num_ex
                examples_dict[key][num_ex] = contents
            else:
                # numex, special
                examples_dict[key][num_ex][special] = contents
        elif special is None:
            # numex, letter
            examples_dict[key][num_ex][letter] = contents
        else:
            # numex, letter, special
            if letter not in examples_dict[key][num_ex]:
                examples_dict[key][num_ex][letter] = {}
            examples_dict[key][num_ex][letter][special] = contents

        if letter is not None and letter!='a':
            assert chr(ord(letter)-1) in examples_dict[key][num_ex],flat_key
    else:
        if letter is None:
            if special is None:
                # numex, roman_num
                examples_dict[key][num_ex][roman_num] = contents
            else:
                # numex, roman_num, special
                if roman_num not in examples_dict[key][num_ex]:
                    examples_dict[key][num_ex][roman_num] = {}
                examples_dict[key][num_ex][roman_num][special] = contents
        else:
            if roman_num not in examples_dict[key][num_ex]:
                examples_dict[key][num_ex][roman_num] = {}
            if special is None:
                # numex, roman_num, letter
                examples_dict[key][num_ex][roman_num][letter] = contents
            else:
                # numex, roman_num, letter, special
                if letter not in examples_dict[key][num_ex]:
                    examples_dict[key][num_ex][roman_num][letter] = {}
                examples_dict[key][num_ex][roman_num][letter][special] = contents

        # for non-initial subnumbers, check that previous subnumber is present
        if roman_num is not None and roman_num!='i':
            ROMAN_NUMS = ['i', 'ii', 'iii', 'iv', 'v', 'vi', 'vii', 'viii', 'ix', 'x',
                          'xi', 'xii', 'xiii', 'xiv', 'xv', 'xvi', 'xvii', 'xviii', 'xix', 'x',
                          'xx', 'xxi', 'xxii', 'xxiii', 'xxiv', 'xxv', 'xxvi', 'xxvii', 'xxviii', 'xxix', 'xxx']
            if not ROMAN_NUMS[ROMAN_NUMS.index(roman_num)-1] in examples_dict[key][num_ex]:
                if not (page=='993' and num_ex=='[5]'): # in this example, only a subset of roman numerals matching a previous example
                    print('[roman]',flat_key)
        if letter is not None and letter!='a':
            pass
            if not chr(ord(letter)-1) in examples_dict[key][num_ex][roman_num]:
                print('[letter]',flat_key)

if __name__ == '__main__':
    pagified_path = 'pagified.html'  # change to desired input path
    yamlified_path = 'cge01-17Ex.yaml'  # change to desired output path
    main(pagified_path, yamlified_path)
