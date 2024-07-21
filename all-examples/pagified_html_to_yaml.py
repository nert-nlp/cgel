import re
import sys
from collections import defaultdict
from more_itertools import peekable
import yaml
from yaml.representer import Representer
from add_page_numbers import reNUMERICEX as RE_NUMERIC_EX, reSENTTERMINAL as RE_SENT_TERMINAL

RE_EX_SPLITTER = re.compile(r'(\[\d+\]\t)|([xvi]+\t)|((?<!\w)[a-i]′?\.\t)|(\[[A-M]\]\t)|(Class [1-5]\t)')
RE_ROMAN_EX = re.compile(r'[xvi]+(?!\.)')
RE_LETTER_EX = re.compile(r'(?<!\w)[a-i]′?\.')  # also handles the special case example labels
RE_SPECIAL_CASE = re.compile(r'(\[[A-M]\])|(Class [1-5])')
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

def propagate_em_across_tabs(line):
    """E.g. <em>ABC\tDEF\tGHI</em>\tJKL -> <em>ABC</em>\t<em>DEF</em>\t<em>GHI</em>\tJKL"""
    assert '<em>' in line,line
    again = True
    while again:
        for m in re.finditer(r'<em>.*?</em>', line):
            if '\t' in m.group():
                line = line[:line.index('\t',m.start())] + '</em>\t<em>' + line[line.index('\t',m.start())+1:]
                again = True
            else:
                again = False
    return line

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
    headers = []
    with open(pagified_path, 'r', encoding="utf-8") as pagified:
        p = peekable(pagified.readlines()[1:])  # skip first line - list of docx files
        for line in p:
            if skip_next:
                #print("skipping", line)
                skip_next = False
                continue

            line = re.sub(r'<a id="[^"]*"></a>', '', line) # hidden bookmarks are created by Word for some reason

            line = line.replace('</em>\t(\t<em>', '</em>\t{{{\t<em>').replace('</em>\t(\t[', '</em>\t{{{\t[')  # second part of sentence in curly braces
            line = line.replace('\t)', '\t}}}').replace('(\t', '{{{\t')  # at the beginning/end of a sentence to indicate a grouping with large curly braces
            line = line.replace('\t</em>)\t', '</em>\t}}}\t')
            line = line.replace('\t</em>)', '</em>\t').replace('(<em>\t', '\t<em>')
            line = line.replace('<small-caps>\t', '\t<small-caps>')
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
            
            if re.search('<em><small-caps>to', line) is not None:  # formatting change for parsing
                line = line.replace('<em><small-caps>', '<small-caps><em>')

            # b., c., etc. must not come immediately after a bracketed number
            assert not re.search(r'^[^\|]+\|\s+\[[0-9]+\]\s+[b-i]′?\.', line),line

            if page == '302' and num_ex == '[21]':
                line = line.replace('ii\tb.', 'ii\ta.') # numbering error in PDF

            # b., c., etc. must not come immediately after a roman numeral
            assert not re.search(r'^[^\|]+\|\s+[ivx]+\s+[b-i]′?\.', line),line

            assert not re.search(r'^<p>#.*\t[b-g]\s', line),line
            
            # two consecutive tags must not be the same
            assert not (m := re.search(r'(</?[A-Za-z-]+>)[^<]+\1', line)),(m.group(0),line)

            # workaround: add_page_numbers.py now applies "#" more liberally, but the code in the loop below
            # relies on "!" being used for any line without a sentence terminal for processing subsequent
            # continuation lines ("@"). So restore "!" for these cases.
            if line.startswith('<p>#') and p.peek(default='').startswith('<p>@'):
                mainpart = '\t'.join(line.split('\t')[3:]).strip()
                mainpart = mainpart.replace('   ','\t').replace('</p>','').replace('</em>','').replace('</u>','').replace('</double-u>','')
                mainpart = re.sub(r'(^|\t)[a-z]′?\.\t', '\t\t', mainpart)
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
            # if '#589| [50]			<small-caps>precedes</small-caps>?		<small-caps>adjacent</small-caps>?' in line:
            #     # contains "?" (sentence terminal) so add_page_numbers doesn't recognize it as header row
            #     line = line.replace('#589|','!589|')
            if '<em>' not in line and '<small-caps>' in line and line.startswith('<p>#'):
                line = '<p>!' + line[4:]

            # examples that are preTags, or don't contain proper sentences/phrases
            REMOVE_THESE = [
                '#105| modal <strong><em>can</em></strong>/<strong><em>will</em></strong>/...	perfect <strong><em>have</em></strong>',
                '#731| <em>on account</em> [<em>of</em>]	<em>out</em> [<em>of</em>]',
                '#695| <em>two days ago	in two weeks',  # mainly a lexical list (with some phrases)
                '#934| [31]				<small-caps>1st inclusive',
                '#1232| <em>delay</em>	<em>describe</em>	<em>detest</em>',
                '#1516| [19]				<small-caps>the fused-head construction</small-caps>',
                '#1516| [20]				<small-caps>the pro-nominal</small-caps>',
                '#1524| [15]				<small-caps>primary forms of</small-caps>',
                '#1524| [16]				<small-caps>secondary forms of</small-caps>',
                '#1529| [37]				<small-caps>ellipsis or pro-form</small-caps>'
            ]
            for this in REMOVE_THESE:
                if this in line:
                    line = '<p>!' + line[4:]
                    break

            # some examples starting with 2-word phrases
            ADD_THESE = [
                '!300| 		e.	<em>They clapped.</em>',
                '!340| 	i	a.	*<em>these <u>equipment</u>',
                '!388| [49]		i	a.	<em>either parent</em>',
                '!429| 	iii		<small-caps>other relative</small-caps>	<em>the car</em> [<em><u>which</u> came first</em>]',
                '!529| 	ii		<em>the <u>rich</u>',
                '!933| [28]		i		<em>Be warned!</em>',
                '!1040| 	ii		<em>the curtain</em>',
                '!1041| 	ii		<em>problems</em>',
                '!1043| 	ii		<em>the student</em>',
                '!1328| 	ii	a.	<em>the <u>civic</u>, <u>school</u>,'
            ]
            for this in ADD_THESE:
                if this in line:
                    line = line[:line.index('!')] + '#' + line[line.index('!')+1:]
                    break

            # special layout
            if '#223| [20]				<em>Unfortunately,	Kim	often	reads	things	too quickly.</em>' in line:
                # remove sentence-internal tabs (and ignore metalinguistic annotations above sentence)
                line = '#223| [20]				<em>Unfortunately, Kim often reads things too quickly.</em>'
            ADD_THESE = [
                '@257| <em>go	He went <u>mad</u>.',
                '@257| <em>stay	She stayed <u>calm</u>.',
                '@257| <em>get</em>	<em>They got me <u>angry</u>.</em>',
                '@257| <em>leave</em>	<em>They left me <u>unmoved</u>.',
                '@258| <em>seem</em>	<em>Kim seemed <u>angry</u>.</em>',
                '@258| <em>sound</em>	<em>They sounded <u>strange</u>.</em>',
                '@258| <em>make</em>	<em>She made him <u>happy</u>.</em>	',
                '@258| <em>render</em>	<em>This rendered it <u>useless</u>.</em>',
                '@277| <small-caps>ii</small-caps>',
                '@277| <small-caps>iii</small-caps>',
                '@277| <small-caps>iv</small-caps>',
                '@277| <small-caps>v</small-caps>',
                '@277| <small-caps>vi</small-caps>',
                '@286| <small-caps>ii</small-caps>',
                '@286| <small-caps>iii</small-caps>',
                '@286| <small-caps>iv</small-caps>',
                '@286| <small-caps>v</small-caps>',
                '@286| <small-caps>vi</small-caps>',
                '@286| <small-caps>vii</small-caps>'
            ]
            for this in ADD_THESE:
                if this in line:
                    line = line[:line.index('@')] + '#' + line[line.index('@')+1:]
                    break

            changed = False
            no_subnumbers = False
            line_parts = re.split(RE_EX_SPLITTER, line) # recognize and split based on (sub)numbers
            if len(line_parts)>1 and line_parts[1] and line_parts[1].startswith('['):
                line_starter = line_parts[:2]
            elif '| ' in line:
                line_starter = [line[:line.index('| ')+2]]  # page number portion
            else:
                line_starter = []

            if ('#50|' in line 
                or (('#277|' in line or '#286|' in line) and '<small-caps>' in line)):
                # one sentence per line (multiple preTags)
                no_subnumbers = True
                if '[1]' not in line and '[16]' not in line and '[44]' not in line:
                    line_parts = line_parts[0]
                    line_parts = line_parts.split(' ',1)
            elif (len(line_parts)==1 or '#849| [12]' in line or '#849| [13]' in line) and line.startswith('<p>#') and '\t' in line and line[line.index('| ')+2].strip() and not roman_num:
                # multiple sentences per line
                no_subnumbers = True
                # absent subnumbers, assume each sentence is all on one line (no @ lines to worry about)
                # fix <em>...</em> extending across a tab
                _line = propagate_em_across_tabs(line)
                if page=='849':
                    _line = _line.replace('[12]\t', '').replace('[13]\t', '')   # remove these so they won't interfere with processing (they are stored in line_starter)
                if _line!=line:
                    changed = True
                line = _line

                if page=='849':
                    headers = ['<small-caps>question</small-caps> + <small-caps>positive answer</small-caps>',
                                '<small-caps>question</small-caps> + <small-caps>negative answer</small-caps>']
                    # these headers are modified from the actual page layout of 3 sentence-columns, each with a header.
                    # in principle they are QA pairs, with the question in the first column.
                    # rearrange into two 'columns' and put QA pairs into the same entry.
                    # the headers are explicit in the text only for [11] but implicitly carry over to [12] and [13]
                    # (see below)

                c1, *rest = line[line.index('| ')+2:].split('\t')
                if c1=='{{{':   # distribute across curly brace rows
                    if rest[0].strip().startswith(('<em>I was told so.', '<em>It seems so.')):
                        c1 = '<em>Are they reliable?</em>'
                    elif rest[0].strip().startswith('<em>Most definitely so.'):
                        c1 = '<em>Is the city beautiful?</em>'
                    elif rest[0].strip().startswith(('*<em>So in the winter.', '*<em>Usually so this early.')):
                        c1 = '<em>Does it rain much?</em>'
                    else:
                        assert False,(c1,rest)
                if page=='849':
                    rest = [_ for _ in rest if _!='{{{']
                    # reformat question-answer pairs as dialogue turns
                    line_parts = line_starter + ['A: '+c1+' B: '+r.lstrip() for r in rest if r.strip()]
                else:
                    assert '<small-caps>' in c1,(c1,rest)   # row header
                    # distribute row header across sentence-columns
                    line_parts = line_starter + [c1+'\t'+r for r in rest if r.strip()]

            string_list = process_full_sentence_line(line_parts)    # each entry is a sentence, with possible tab-separated headers
            page = re.search(r'[0-9?_]+', string_list[0]).group()
            #assert page!='338' or string_list[0][0]!='#',string_list
            if page in ('257','258') and line.startswith('<p>#') and num_ex in ('[14]','[15]') and '[16]' not in line and '| \ti' not in line:  # note that num_ex may be stale
                line = propagate_em_across_tabs(line).replace('<p>','').replace('</p>','')
                string_list = line.split(' ',1)

            for string in string_list[1:]:
                assert '\t\t' not in string
                if RE_NUMERIC_EX.match(string) is not None:  # labels like '[1]'
                    num_ex = string
                    key = f'ex{len(examples_dict)+1:05}'
                    global beforeCurlyBrace, afterCurlyBrace
                    beforeCurlyBrace = None    # ensure part of item doesn't carry over to next example
                    afterCurlyBrace = None
                    roman_num = None
                    letter_label = None
                    special_label = None
                    headers = []
                    # headers that should carry over from previous example
                    if page=='849' and num_ex in ('[12]', '[13]'):
                        headers = ['<small-caps>question</small-caps> + <small-caps>positive answer</small-caps>',
                                   '<small-caps>question</small-caps> + <small-caps>negative answer</small-caps>']
                        line = line.replace('\t{{{\t', '\t')
                elif RE_ROMAN_EX.match(string) is not None:  # labels like 'i'
                    roman_num = string
                    letter_label = None
                elif RE_LETTER_EX.match(string) is not None:  # labels like 'a.', 'b′.'
                    letter_label = string
                elif RE_SPECIAL_CASE.match(string) is not None:  # labels like [A], Class 1, A:, B:
                    special_label = string
                else:  # handle the text on the line
                    if (page=='1169' and num_ex=='[26]'):
                        continue    # lexical list
                    elif (page=='1232' and num_ex=='[29]'):
                        continue    # lexical list

                    if string_list[0][0:1] == '#':
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

                        examples_dict[key]['page'] = page
                        sent = string
                        sent = re.sub(r'([a-z]\.)([A-Z])', r'\1 \2', sent)
                        #sent = re.sub(RE_END_TAG, r'\t\1', sent)
                        assert '\t\t' not in sent,sent
                        assert '???' not in sent,sent

                    
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
                        if (no_subnumbers and page not in ('257','258')) or (page == '50' and num_ex == '[1]'):
                            if page not in ('50', '849'):
                                assert sent.startswith(('<small-caps>', '<em><small-caps>')),(sent,line)
                            _num_ex = num_ex + f'-{sum(1 for k in examples_dict[key] if k.startswith("["))+1}'
                        else:
                            _num_ex = num_ex
                        
                        insert_sent(examples_dict, key, _num_ex, roman_num, letter_label, special_label, page, headers, sent)

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

                                assert letter_label in (None,'a.','b.') or re.search(r'^[a-z]′?\.', letter_label) is not None,(letter_label,page,num_ex) # continuation of a. column, b. column, or full-width column
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
                                            headers, sent)
                        else: # non-sentence
                            pass #print(line, file=sys.stderr)
                    else:  # '!' lines without any italics
                        if '<small-caps>' in string or '\u2013' in string or '=' in string:
                            # e.g. 'S – P – PC\tPC – P – S' (p. 268); 'S<sub>intr</sub> = S<sub>trans</sub>\tS<sub>intr</sub> = O<sub>trans</sub>' (p. 296)
                            _headers = string
                            if re.match(r'^[^a-z]+$', _headers):
                                _headers = '<small-caps>' + _headers + '</small-caps>'  # to signal it is a header preTag, even if "small caps" has no effect on the appearance
                            _headers = re.sub(r'(^[^a-z<>]+)(<small-caps>)', r'\2\1', _headers)
                            _headers = re.sub(r'\s*\t\s*', '\t', _headers)
                            _headers = re.sub(r'<small-caps>\s+', '<small-caps>', _headers)
                            _headers = re.sub(r'(?<=[^>])\t\s*(?=[^<])', '</small-caps>\t<small-caps>', _headers)
                            assert 'V \u2013 <small-caps>' not in _headers,_headers
                            headers.extend(map(str.strip, _headers.split('\t')))
                        else:
                            assert '</small-caps>' not in string
                            assert page in {'___', '???', '125', '126', '136', '223', '239', '426', '452', '468', '510',
                                            '752', '917', '934', '1214', '1218', '1277', '1278', '1279', '1285'} or int(page)<100 or string.endswith('</em>') or '</em>\t' in string or len(string)<10,(page,string)
                        pass #print(line, file=sys.stderr)

    with open(yamlified, 'w', encoding="utf-8") as yamlified:
        yaml.dump(examples_dict, yamlified, #default_style='"', 
                  width=float("inf"), sort_keys=False)


def insert_sent(examples_dict: dict[str,dict[str,dict|list]], key, num_ex, roman_num, letter, special, page, headers, sent):
    sent = sent.replace('Ph. D.', 'Ph.D.')
    sent = sent.replace('`', '\'')
    sent = sent.replace('≡', '')    # on p. 359 this is used as a semantic relation between examples
    sent = sent.replace(' </u> ', '</u> ')
    sent = sent.replace('<small-caps></small-caps>', '').replace('<small-caps> </small-caps>', ' ').replace('<small-caps>.</small-caps>', '.')
    sent = re.sub(r'(?<=\S)\{\{\{', r'\t{{{', sent)
    assert '<p>' not in sent
    assert '</p>' not in sent,sent
    assert '???' not in sent,sent
    assert '<em></em>' not in sent,sent
    assert '] .<' not in sent and '[ of' not in sent,(page,sent)
    
    sent = sent.replace(']  </em>[', ']<em> </em>[')
    if sent.endswith('</em>].') or sent.endswith('</em>).'):
        sent = sent[:-1] + '<em>.</em>'
    
    if (page,num_ex) in {('257', '[14]'), ('258', '[15]')}:
        sent = propagate_em_across_tabs(sent)

    # two consecutive tags must not be the same
    assert not (m := re.search(r'(</?[A-Za-z-]+>)[^<]+\1', sent)),(page,m.group(0),sent)

    # a case of hyphenation
    if page == '319' and 'ma-' in sent:
        sent = sent.replace('ma-</u> <u>jor', 'major')

    if page == '130' and num_ex == '[16]':  # Chronicles of history layout with "YEAR\tEVENT"
        sent = sent.replace('1434\t', '1434: ').replace('1435\t', '1435: ').replace('1438\t', '1438: ')
        assert 'Cosimo' in sent,sent

    if page=='486' and num_ex=='[5]':
        # headers are for feature columns only. remove them
        headers = []
        # complicated nesting of curly braces. process the repetition manually
        sent = (sent.replace('1st\t}}}\tsingular', '1st\tsingular')
                    .replace('2nd\t}}}', '2nd\tsingular')
                    .replace('masculine\t}}}\t3rd\t}}}', 'masculine\t3rd\tsingular')
                    .replace('feminine\t}}}\t}}}', 'feminine\t3rd\tsingular')
                    .replace('neuter\t}}}\t}}}', 'neuter\t3rd\tsingular')
                    .replace('1st\t}}}\tplural', '1st\tplural')
                    .replace('2nd\t}}}', '2nd\tplural')
                    .replace('3rd\t}}}', '3rd\tplural'))

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
    contents2 = []
    assert sent.count('{{{')<=1
    iCurlyBraceOnLine = 0
    for i,x in enumerate(contents):
        if x=='{{{':
            assert '}}}' not in x,x
            global beforeCurlyBrace
            if i>1:
                beforeCurlyBrace = contents[i-1]
                #print('SETTING{ ', beforeCurlyBrace)
            else:
                assert beforeCurlyBrace,contents
                contents2.append(beforeCurlyBrace)
        elif x=='}}}':
            global afterCurlyBrace
            iCurlyBraceOnLine += 1
            if afterCurlyBrace is None:
                afterCurlyBrace = []
            if i+1==len(contents) or contents[i+1]=='}}}':
                # copy from above
                assert len(afterCurlyBrace)>iCurlyBraceOnLine-1,(contents,iCurlyBraceOnLine,afterCurlyBrace)
                contents2.append(afterCurlyBrace[iCurlyBraceOnLine-1])
                assert sent.count('}}}')<=1,(contents,contents2)
            else:
                if iCurlyBraceOnLine==1:
                    afterCurlyBrace = []
                afterCurlyBrace.append(contents[i+1])
                #print('SETTING} ', afterCurlyBrace, contents[0])
        else:
            if i>0 and contents[i-1]=='{{{' and contents2[-1].endswith(('</em>','</double-u>')):
                if x.replace('<em>','')[0].isupper():   # new column
                    contents2.append(x)
                else:   # continuation of sentence
                    contents2[-1] += ' ' + x  # before { is the first part of a sentence
                    contents2[-1] = contents2[-1].replace('</em> <em>', ' ')
            else:
                contents2.append(x)

    contents = list(filter(lambda x: x!='', contents2))

    assert '<em>' not in contents,contents
    assert '</em>' not in contents,contents

    #if flat_key=='ex01011_p540_[34]_iii_a':
    # if page=='540' and num_ex=='[34]':
    #    print(contents)
    if len(contents)>2: # sequence is: exampleID preTag* main+ postTag*
        section = 'pre'
        for i,part in enumerate(contents):
            if i==0: continue   # example ID
            elif part.startswith(('<small-caps>', '<em><small-caps>', '<strong>', 'verb \u2013')):
                assert section=='pre',(part,contents)
                contents[i] = '<preTag>' + part + '</preTag>'
            elif section=='pre' and i==1 and (page,num_ex) in {('108','[48]'), ('257', '[14]'), ('258', '[15]'), ('108','[49]'), ('994','[3]')}:
                contents[i] = '<preTag>' + part + '</preTag>'    # no formatting markup for pre-tag
            elif section=='pre' and 1<=i<=2 and (page,num_ex) in {('1323','[3]')}:
                contents[i] = '<preTag><em>' + part.replace('<em>','') + '</em></preTag>'
            elif section=='pre':
                section = 'main'    # first of possibly multiple main sentence columns
                if page=='1323' and num_ex=='[3]':
                    part = '<em>' + part
                    contents[i] = part
                assert re.search(r'^([AB]: )?[*!?#%]?\[?\(?(<em>|<double-u>)', part) or part in ('[not possible]','[No antecedent]','[pre-empted by iib]'),contents
                if part.endswith('</em>.'):
                    contents[i] = part[:-6] + '.</em>'
                elif part.endswith('</em>...'):
                    contents[i] = part[:-8] + '...</em>'
                elif not part.endswith(('</em>',']',')')) and part!='A:':  # italics continue on the next column
                    if '<em>' in part and '</em>' in part and part.rindex('<em>') < part.rindex('</em>'):
                        assert part.endswith((']', '].', ')', ').')),(flat_key,part,contents)
                    elif part!='[not possible]' and not part.startswith(('A: ','B: ')):
                        contents[i] = part + '</em>'
            elif section in ('main','post') and part.startswith('(='):
                section = 'post'
                contents[i] = '<postTag>' + part + '</postTag>'
            elif section in ('main','post') and part.startswith('[') and part.endswith(']'):
                section = 'post'
                contents[i] = '<postTag>' + part + '</postTag>'
            elif section=='post': # and page=='486' and part in ('singular','plural'):
                part_clean = re.sub(r'</?su[bp]>', part, '')
                if not part.startswith('Comp of '):
                    assert ' ' not in part and '<' not in part_clean and '>' not in part_clean,(part,contents)
                section = 'post'
                contents[i] = '<postTag>' + part + '</postTag>'
            elif section=='main':   # we've already seen a previous example
                if part.endswith('</em>.'):
                    contents[i] = part[:-6] + '.</em>'
                if not re.search(r'^[*!?#%]?\[?\(?(<em>|<double-u>)', part):
                    part_clean = re.sub(r'</?su[bp]>', '', part)
                    if part.startswith(('A: ', 'B: ', 'B (Jill): ')):
                        continue    # turn of a dialogue
                    elif ' ' not in part and '<' not in part_clean and '>' not in part_clean:
                        # single-word postTag as in feature matrices?
                        section = 'post'
                        contents[i] = '<postTag>' + part + '</postTag>'
                    elif part.startswith(('Comp of', 'intransitive ', 'monotransitive ', 'subj-det', 'subject of ', 'object of ', 'closed interrogative')):
                        section = 'post'
                        contents[i] = '<postTag>' + part + '</postTag>'
                    elif part[0].isalpha() or part.startswith('<u>') and part[3].isalpha():   # subsequent column where italics carry over from previous column
                        part = '<em>' + part
                        contents[i] = part
                    else:
                        if ('[' in part and ']' in part) or ('“' in part and '”' in part):
                            if '[' in part and ']' in part:
                                assert part.startswith('[') and part.endswith(']') or part.startswith('(') and part.endswith(')'),part
                            section = 'post'
                            contents[i] = '<postTag>' + part + '</postTag>'
                        elif page in ('743', '751', '752') and part in ('}}} future','}}} present','}}} past'):
                            section = 'post'
                            contents[i] = '<postTag>future</postTag>'
                        else:
                            #print('Should have <em>?:', part+'\n'+sent, file=sys.stderr)
                            assert False,(flat_key,part)
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
            assert re.search(r'^(A: )?[*!?#%]?\[?\(?(<em>|<double-u>)', contents[1]) or contents[1].startswith('<u>(<em>'),(flat_key,sent,contents)
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
                assert '_p889_[59]' in contents[0] or contents[i-1].startswith('A: ' if x.startswith('B') else 'B: '),contents
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
            assert ' </u>' not in x,(flat_key,x)
            assert '</u> /' not in x,(flat_key,x)

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

    for h in headers:
        assert h.count('<small-caps>')==h.count('</small-caps>'),(page,h)
    if len(headers)==1: # header is a title for the full numbered example
        examples_dict[key]['title'] = headers[0]
        headers = []

    if '-' in num_ex:
        pseudonum = num_ex[num_ex.index('-')+1:]    # e.g. the "1" of "[3]-1" (a column number that doesn't appear in the text)
    else:
        pseudonum = None

    if roman_num is None:
        if letter is None:
            if special is None:
                # num_ex
                if headers:
                    col = (int(pseudonum)-1) % len(headers)  # pseudonum counting is row by row. assume each row has len(headers) columns
                    header = headers[col]
                    contents.insert(1, f'<preTag>{header}</preTag>')
                assert num_ex not in examples_dict[key],(num_ex,examples_dict[key])
                examples_dict[key][num_ex] = contents
            else:
                # numex, special
                assert special not in examples_dict[key][num_ex]
                assert not headers
                examples_dict[key][num_ex][special] = contents
        elif special is None:
            # numex, letter
            if headers:
                assert len(headers)>1 and letter.islower()
                header = headers['abc'.index(letter)]
                contents.insert(1, f'<preTag>{header}</preTag>')
            assert isinstance(examples_dict[key][num_ex],dict),(letter,contents,examples_dict[key][num_ex])
            examples_dict[key][num_ex][letter] = contents
        else:
            # numex, letter, special
            if headers:
                assert len(headers)>1 and letter.islower()
                header = headers['abc'.index(letter)]
                contents.insert(1, f'<preTag>{header}</preTag>')

            if letter not in examples_dict[key][num_ex]:
                examples_dict[key][num_ex][letter] = {}
            assert special not in examples_dict[key][num_ex][letter]
            examples_dict[key][num_ex][letter][special] = contents

        if letter is not None and letter!='a':
            if letter[-1]=='′':
                assert chr(ord(letter[:-1])) in examples_dict[key][num_ex],flat_key
            else:
                assert chr(ord(letter)-1) in examples_dict[key][num_ex],flat_key
    else:
        if letter is None:
            if special is None:
                # numex, roman_num
                if (page,num_ex) not in {('257','[14]'), ('258','[15]')}:
                    assert roman_num not in examples_dict[key][num_ex],(roman_num,contents,examples_dict[key][num_ex])
                if contents[0].endswith('_p156_[24]_iv'):   # middle col is empty
                    contents.insert(2, None)
                while headers and 'A: ' in contents[1] and ' B: ' in contents[1]: # e.g. p. 887 [54]; sometimes A: B: B: as p. 889 [59], hence the loop
                    # split A: and B: into two parts as they have independent col headers
                    contents.insert(2,contents[1][contents[1].rindex(' B: ')+1:])
                    contents[1] = contents[1][:contents[1].rindex(' B: ')]

                if headers and len(headers)==len(contents[1:])-int(contents[1].startswith('<preTag>')):
                    if (page,num_ex) in {('257','[14]'), ('258','[15]')}:
                        # 'i' and 'ii' each group together 3 rows. so each row and column combination needs pseudonumbering
                        lexpretag = re.sub(r'</?[A-Za-z-]+>', '', contents[1])
                        c0 = {'i': {'get': 0, 'go': 1, 'stay': 2, 'become': 0, 'seem': 1, 'sound': 2},
                              'ii': {'drive': 0, 'get': 1, 'leave': 2, 'call': 0, 'make': 1, 'render': 2}}[roman_num][lexpretag]*2
                    else:
                        c0 = 0

                    for col,(header,x) in enumerate(zip(headers,contents[1+int(contents[1].startswith('<preTag>')):], strict=True), start=c0):
                        if x is not None:
                            # here we create a different kind of pseudonum, of a column within a Roman numeral-labeled row
                            _contents = [contents[0]+f'-{col+1}', f'<preTag>{header}</preTag>', x]
                            if contents[1].startswith('<preTag>'):
                                _contents.insert(2, contents[1])
                            examples_dict[key][num_ex][roman_num][str(col+1)] = _contents
                elif headers and not contents[1].startswith('<preTag>') and contents[-1].startswith('<postTag>') and not contents[-2].startswith('<postTag>') and len(headers)==len(contents[1:])-1:
                    # exclude multiple <postTag> entries as these tend to be feature-value matrices, where the header is the feature name (e.g. p. 219 [10])
                    for col,(header,x) in enumerate(zip(headers,contents[1:-1], strict=True)):
                        _contents = [contents[0]+f'-{col+1}', f'<preTag>{header}</preTag>', x]
                        if contents[-1].startswith('<postTag>'):
                            _contents.append(contents[-1])
                        examples_dict[key][num_ex][roman_num][str(col+1)] = _contents
                else:
                    if headers:
                        print(contents[0], 'SKIPPING HEADERS')
                    examples_dict[key][num_ex][roman_num] = contents
            else:
                # numex, roman_num, special
                if roman_num not in examples_dict[key][num_ex]:
                    examples_dict[key][num_ex][roman_num] = {}
                assert special not in examples_dict[key][num_ex][roman_num]
                assert not headers
                examples_dict[key][num_ex][roman_num][special] = contents
        else:
            if headers:
                assert len(headers)>1 and letter.islower()
                assert 'abc'.index(letter)+1<=len(headers),(page,letter,headers)
                header = headers['abc'.index(letter)]
                contents.insert(1, f'<preTag>{header}</preTag>')

            if roman_num not in examples_dict[key][num_ex]:
                examples_dict[key][num_ex][roman_num] = {}
            if special is None:
                # numex, roman_num, letter
                assert letter not in examples_dict[key][num_ex][roman_num],(letter,contents,examples_dict[key][num_ex])
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
            if len(letter)==1 and chr(ord(letter)-1) not in examples_dict[key][num_ex][roman_num]:
                print('[letter]',flat_key)

if __name__ == '__main__':
    pagified_path = 'pagified.html'  # change to desired input path
    yamlified_path = 'cge01-17Ex.yaml'  # change to desired output path
    main(pagified_path, yamlified_path)
