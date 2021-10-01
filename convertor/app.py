import stanza
from flask import Flask, render_template, request, url_for
from depedit import DepEdit
from json import dumps as jsonify

config_file  = open("ud-to-cgel.ini")
d = DepEdit(config_file)

app = Flask(__name__)

nlp = stanza.Pipeline(lang='en', processors='tokenize,mwt,pos,lemma,depparse')

@app.route("/")
def hello_world():
    return render_template('index.html')

@app.route("/query")
def query():
    sent = request.args.get('sent')
    doc = nlp(sent)
    res = '<table width="100%"><tr><td width="50%">'
    doc = doc.to_dict()
    
    for word in doc[0]:
        res += f'{word["id"]}: "{word["text"]}" ({word["upos"]} ←<sub>{word["deprel"]}</sub> {word["head"]})<br>'

    print(doc[0])
    conllu = f"# text = {sent}\n"
    for word in doc[0]:
        conllu += f'{word["id"]}\t{word["text"]}\t{word["lemma"]}\t{word["upos"]}\t{word["xpos"]}\t{word.get("feats", "")}\t{word["head"]}\t{word["deprel"]}\t_\t_\n'

    conllu = d.run_depedit(conllu).split('\n')
    res += '</td><td width="50%">'
    for word in conllu[1:]:
        x = word.split('\t')
        res += f'{x[0]}: "{x[1]}" ({x[3]} ←<sub>{x[7]}</sub> {x[6]})<br>'

    return res + "</td></tr></table>"

if __name__ == '__main__':
    # Threaded option to enable multiple instances for multiple user access support
    app.run(threaded=True, port=5000)