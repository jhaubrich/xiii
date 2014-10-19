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
    md = requests.get(url)
    return Markup(markdown.markdown(md.text))
    
@application.route('/')
def hello_world():
    content_md = render_dropbox_md("https://www.dropbox.com/s/swq7kavg920tvet/index.md?dl=1")
    sidebar_md = render_dropbox_md("https://www.dropbox.com/s/91p6lqk8rszb7h3/sidebar.md?dl=1")
    return render_template('index.tmpl', **locals())


@application.route('/faq')
def faq():
   sidebar_md = render_dropbox_md("https://www.dropbox.com/s/91p6lqk8rszb7h3/sidebar.md?dl=1")
   content_md = render_dropbox_md("https://www.dropbox.com/s/4r22zrd9q6wge0q/faq.md?dl=1")
   return render_template('index.tmpl', **locals()) 
 

@application.route('/professions/json/')
def profession_json():
    return jsonify(google_formatted_json())

def google_formatted_json():
    r = requests.get("https://docs.google.com/spreadsheets/d/1dwshW3o1kXcFC4gvCUXi9p6NmxoDLL2IvOkKu9acHLE/gviz/tq?tq=select+*")
    # strip the jsonp callback
    google_jsonp = dict(start='google.visualization.Query.setResponse(', end=');')
    google_json = r.text
    google_json = google_json.replace(google_jsonp['start'], '')
    google_json = google_json.replace(google_jsonp['end'], '')
    table = json.loads(google_json)

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
        
    table['by_name'] = data
    return table
    

@application.route('/professions/<sort>')
@application.route('/professions/')
def professions(sort="by_name"):
    sidebar_md = render_dropbox_md("https://www.dropbox.com/s/91p6lqk8rszb7h3/sidebar.md?dl=1")
    content_md = render_dropbox_md("https://www.dropbox.com/s/mgwh0fxz7nk10sg/professions.md?dl=1")

    table = google_formatted_json()
    if sort == "by_name":
        return render_template('professions.tmpl', members=table['by_name'], content_md=content_md, sidebar_md=sidebar_md)
        

@application.route('/mumble')
def mumble():
    content = """## Mumble
Get the client at [mumble.com](http://www.mumble.com/mumble-download.php).

#### Server
homebrew.mumble.com
#### Port
9812
    """

    return render_template('index.tmpl', content_md=Markup(markdown.markdown(content)))


if __name__ == '__main__':
    application.run(host='0.0.0.0')
