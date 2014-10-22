import json

import requests
import markdown

import flask
from flask import Response, request
from flask import render_template, jsonify
from flask import Markup
 
application = flask.Flask(__name__)

#Set application.debug=true to enable tracebacks on Beanstalk log output. 
#Make sure to remove this line before deploying to production.
application.debug=True
 
def render_dropbox_md(url):
    with open(url) as f:
        html = Markup(markdown.markdown(f.read()))
    return html
    
@application.route('/')
def hello_world():
    content_md = render_dropbox_md("static/markdown/index.md")
    sidebar_md = render_dropbox_md("static/markdown/sidebar.md")
    return render_template('index.tmpl', **locals())


@application.route('/faq')
def faq():
   sidebar_md = render_dropbox_md("static/markdown/sidebar.md")
   content_md = render_dropbox_md("static/markdown/faq.md")
   return render_template('index.tmpl', **locals()) 
 

@application.route('/professions/')
def professions(sort="by_name"):
    sidebar_md = render_dropbox_md("static/markdown/sidebar.md")
    content_md = render_dropbox_md("static/markdown/professions.md")

    return render_template('professions.tmpl', content_md=content_md, sidebar_md=sidebar_md)
        

@application.route('/mumble.json')
def local_mumble_json():
    mumble_json = requests.get("https://api.mumble.com/mumble/cvp.php?token=LSG-8A-A8183DEB").text
    return Response(mumble_json, mimetype='application/json')


def get_google_json(speadsheet_url):
    r = requests.get(speadsheet_url)
    # strip the jsonp callback
    google_jsonp = dict(start='google.visualization.Query.setResponse(', end=');')
    google_json = r.text
    google_json = google_json.replace(google_jsonp['start'], '')
    google_json = google_json.replace(google_jsonp['end'], '')
    # remove bad date objects and unicode escape chars
    google_json = google_json.replace('\\u0022', '').replace('\\u00', '').replace('new Date(', '"').replace('),"', '","')
    table = json.loads(google_json)
    return table
    

@application.route('/professions.json')
def profession_json():
    table = get_google_json("https://docs.google.com/spreadsheets/d/1dwshW3o1kXcFC4gvCUXi9p6NmxoDLL2IvOkKu9acHLE/gviz/tq?tq=select+*")
    # create a list of dict(name, guild_profession, [other_professions], comments)
    cols = table['table']['cols']
    rows = table['table']['rows']
    data = []
    for row in rows:
        item = {}
        item['other_professions'] = {}
        item['guild_profession'] = ''

        for col in cols:
            i = cols.index(col)
            column_label = col['label']
            cell = row['c'][i]  # v=value (f=formatted)
            if cell and column_label:
                if cell['v'] < 0:
                    item['guild_profession'] = {'name': column_label, 'value': abs(cell['v'])}
                elif column_label != "Comments" and column_label != 'Name':
                    item['other_professions'][column_label] = "{:,}".format(int(cell['v']))
                else:
                    item[column_label] = cell['v']

        data.append(item)
        
    table['by_member'] = data
 
    return jsonify(table)

@application.route('/assets.json')
def assets_json():
    treasurey_table = get_google_json("https://docs.google.com/spreadsheets/d/1X9JMdmksP1QdThU_Hgvno9hJlUCtBp2Y568DwIrdhNw/gviz/tq?tq=select+*&gid=0")
    # resources_table = get_google_json("https://docs.google.com/spreadsheets/d/1X9JMdmksP1QdThU_Hgvno9hJlUCtBp2Y568DwIrdhNw/gviz/tq?tq=select+*&gid=2041050771")
    return jsonify(dict(gold=treasurey_table['table']['rows'][0]['c'][2]['f'].replace('.', ' '),
                        charcoal=0, crystal=0, rocksalt=0))

    
if __name__ == '__main__':
    application.run(host='0.0.0.0')
