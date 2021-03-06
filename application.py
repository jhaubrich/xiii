import json
import re

import requests
import markdown
import feedparser

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

 
@application.route('/join/')
def join():
    sidebar_md = render_dropbox_md("static/markdown/sidebar.md")
    return render_template('join.tmpl', sidebar_md=sidebar_md)

 
@application.route('/mumble.json')
def local_mumble_json():
    mumble_json = requests.get("https://api.mumble.com/mumble/cvp.php?token=LSG-8A-A8183DEB").text
    return Response(mumble_json, mimetype='application/json')


@application.route('/calendar/')
def calendar():
    sidebar_md = render_dropbox_md("static/markdown/sidebar.md")
    return render_template('calendar.tmpl', sidebar_md=sidebar_md)

    
def get_google_json(speadsheet_url):
    r = requests.get(speadsheet_url)
    # strip the jsonp callback
    google_jsonp = dict(start='google.visualization.Query.setResponse(', end=');')
    google_json = r.text
    google_json = google_json.replace(google_jsonp['start'], '')
    google_json = google_json.replace(google_jsonp['end'], '')
    # remove bad date objects and unicode escape chars
    google_json = google_json.replace('\\u0022', '').replace('\\u00', '').replace('new Date(', '"').replace('),"', '","')  # 
    table = json.loads(google_json.decode('unicode_escape'))
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
    gold = treasurey_table['table']['rows'][0]['c'][3]['f'] # google spredsheet render workaround
    gold = gold[:-1].replace('.', 'g ') + 's'  # 55g 55s

    # charcoal doesn't show up in the json. It's set to None
    # ...
    #  u'table': {
    #      u'rows': [{u'c': [None,
    #                        None,
    #                        {u'v': u'1'},
    #                        {u'f': u'2', u'v': 2.0},
    #                        {u'v': None}]},
    #                {u'c': [None, None, {u'v': u'Type'}, None, {u'v': u'Comment'}]},
    # ...
    # resources_table = get_google_json("https://docs.google.com/spreadsheets/d/1X9JMdmksP1QdThU_Hgvno9hJlUCtBp2Y568DwIrdhNw/gviz/tq?tq=select+*&gid=2041050771")
    # charcoal = resources_table['table']['rows'][0][0]['c'][1]
    # crystal = resources_table['table']['rows'][0][0]['c'][2]
    # rocksalt = resources_table['table']['rows'][0][0]['c'][3]
    return jsonify(dict(gold=gold, charcoal=0, crystal=0, rocksalt=0))

    
@application.route('/motd.json')
def motd_json():
    motd = get_google_json("https://docs.google.com/spreadsheets/d/1GI73t_KnSWBKRp_QfmXeJKrtPwavYC5yFjNAphvge3c/gviz/tq?tq=select+*&gid=0")
    return jsonify({'text': motd['table']['rows'][0]['c'][0]['v']})
    # r = requests.get("https://docs.google.com/spreadsheets/d/1GI73t_KnSWBKRp_QfmXeJKrtPwavYC5yFjNAphvge3c/gviz/tq?tq=select+*&gid=0")
    # return r.text.decode('unicode_escape')
    
    
@application.route('/calendar.json')
def calendar_json():
    """
    >>> import feedparser
    >>> d = feedparser.parse('https://www.google.com/calendar/feeds/f0i8n739nted6nehflb0b9hreg%40group.calendar.google.com/public/basic')
    >>> d['updated']
    'Tue, 28 Oct 2014 14:59:23 GMT'
    >>> d['entries'][0]['title']
    u'Test Event'
    >>> d['entries'][0]['updated']
    u'2014-10-28T14:51:40.000Z'
    >>> d['entries'][0]['link']
    u'https://www.google.com/calendar/event?eid=dDY4bTM2NDU2bnFtbHFzYjhqYTd1dmU3MDAgZjBpOG43MzludGVkNm5laGZsYjBiOWhyZWdAZw'
    >>> d['entries'][0]['content'][0]['value']
    u'When: Wed Oct 29, 2014 10am to 11am\xa0\nCDT<br />\n\n\n<br />Event Status: confirmed\n<br />Event Description: test description'
    """
    import datetime
    feed = feedparser.parse('https://www.google.com/calendar/feeds/f0i8n739nted6nehflb0b9hreg%40group.calendar.google.com/public/basic')

    d = dict(updated=feed['updated'], entries=[])
    for entry in feed['entries']:
        content = entry['summary']

        # Parse Date
        date = 0  # cause date parsing to fail hard
        try: # Date range (time to time) event
            date_re = re.compile("When: (?P<date>.*) to")
            m = date_re.search(content)  # Wed Oct 29, 2014 9pm
            date = datetime.datetime.strptime(m.groupdict()['date'], "%a %b %d, %Y %I%p")
        except: 
            pass
            print(content)
            print("Not a date and time event")
            print("date doesn't match: %a %b %d, %Y %I%p\n\n")
        try:  # All day event
            date_re = re.compile("When: (?P<date>.*)<")
            m = date_re.search(content)  # Wed Oct 29, 2014 9pm
            date = datetime.datetime.strptime(m.groupdict()['date'], "%a %b %d, %Y") + datetime.timedelta(days=1)
            print(date)
        except:
            pass
            print(content)
            print("Not an all day event")
            print("date doesn't match: %a %b %d, %Y\n\n")
        try:  # multi day event
            date_re = re.compile("When: (?P<from_date>.*) to (?P<to_date>.*)&nbsp") # "When: Sun Dec 21, 2014 to Sat Jan 3, 2015&nbsp;"
            m = date_re.search(content)
            date = datetime.datetime.strptime(m.groupdict()['to_date'], "%a %b %d, %Y") + datetime.timedelta(days=1)
        except:
            print(content)
            print("Not a multi-day event")
            print("date doesn't match: %a %b %d, %Y to %a %b %d, %Y\n\n")
            

        content = content.replace('<br />', '', 1)
        content = content.replace('When: ', '')
        content = content.replace('Event Status: confirmed', '')
        content = content.replace('Event Status: confirmed\n<br />', '')
        content = content.replace('Event Description: ', '')
        
        
        d['entries'].append(dict(
            title=entry['title'],
            updated=entry['updated'],
            link=entry['link'],
            content=content,
            date=date,
        ))

    current_events = []
    for event in d['entries']:
        # drop past events older than 2 hours (CST = UTC-6)
        if event['date'] > datetime.datetime.utcnow() - datetime.timedelta(hours=8):
            current_events.append(event)
            
    sorted_events = sorted(current_events, key=lambda k: k['date'])
    d['entries'] = sorted_events
    d['next_events'] = sorted_events[:2]

    # aws flask version bug
    # return jsonify(d)
    date_handler = lambda obj: obj.isoformat() if isinstance(obj, datetime.datetime) else None
    return json.dumps(d, default=date_handler)
    
    
if __name__ == '__main__':
    application.run(host='0.0.0.0')
