from __future__ import division
import random
import StringIO
from datetime import datetime
import re
from os import path

import pandas as pd
import seaborn as sns
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
from matplotlib.figure import Figure
from wordcloud import WordCloud, STOPWORDS, ImageColorGenerator
from PIL import Image

from flask import Flask, g, session, make_response
from flask import render_template, flash, redirect, url_for
from flask import request, send_file
from .forms import PersonTopicForm, WordcloudForm
from flask.ext.mysql import MySQL
from flask.ext.cache import Cache

app = Flask(__name__)
app.config.from_object('config') # mysql conn, cortical api key

mysql = MySQL()
mysql.init_app(app)

cache = Cache(app,config={'CACHE_TYPE': 'simple'})

def CountsByKeyword(df, col, person, topics, StartDate = '2009-01-01', EndDate = '2013-01-01'):
    """
    Returns a dict of total mention counts per keyword for the given person. 
    Returns counts for the passed in time frame, defaults to entire timeframe.
    
    'By' parameter controls which field you're getting counts by.
    Big return says: return a dictionary via comprehension for lists, or just a dict for one value
    
    This is not a good function. Change it to return one dataframe for all people/topics.
    """
    
    if not isinstance(topics, (str, unicode, list)): 
        raise TypeError('\'topics\' parameter must be either str or list') 
    
    person = '(' + person + ')'
    StartDate = datetime.strptime(StartDate, '%Y-%m-%d')
    EndDate = datetime.strptime(EndDate, '%Y-%m-%d') 

    return (
        {topic: df[col].loc[
                (df[col].str.contains(person, case = False)) 
                & (df['ExtractedBodyText'].str.contains(topic, case = False))
                & (df['MetadataDateSent'] > StartDate)
                & (df['MetadataDateSent'] < EndDate)].count()
            for topic in topics}
    )

# @cache.cached(timeout=600, key_prefix='emails')
def getEmails():
	con = mysql.connect()
	cur = con.cursor()
	sql = """SELECT * FROM EmailsC"""

	cur.execute(sql)

	Emails = cur.fetchall()
	Emails2 = [tuple(elm,) for elm in Emails]
	EmailsFinal = pd.DataFrame(Emails2, columns = [u'Id', u'DocNumber', u'MetadataSubject', u'MetadataTo', u'MetadataFrom',
       u'SenderPersonId', u'MetadataDateSent', u'MetadataDateReleased',
       u'MetadataPdfLink', u'MetadataCaseNumber', u'MetadataDocumentClass',
       u'ExtractedSubject', u'ExtractedTo', u'ExtractedFrom', u'ExtractedCc',
       u'ExtractedDateSent', u'ExtractedCaseNumber', u'ExtractedDocNumber',
       u'ExtractedDateReleased', u'ExtractedReleaseInPartOrFull',
       u'ExtractedBodyText', u'RawText'])
	
	return EmailsFinal

def buildCounterDF(personlist, topiclist):
	PersonThing = list()
	PersonTopic = pd.DataFrame()

	topiclist = topiclist.split(',')

	for person in personlist:
		PersonThing.append(
			tuple((person, 
			       CountsByKeyword(Emails, col = 'MetadataFrom', person = person, topics = topiclist))
			)
	)

	for item in PersonThing:
		tdf = pd.DataFrame.from_dict(item[1], orient = 'index')
		tdf['Person'] = item[0]
		tdf.reset_index(level = 0, inplace = True)
		tdf.rename(columns = {'index': 'Topic', 0: 'count'}, inplace = True)
		tdf = tdf[['Person', 'Topic', 'count']]

		PersonTopic = PersonTopic.append(tdf)

	return PersonTopic

def rmNonAlpha(texts):  
    """
    Remove non-alphabetic characters (roughly)
    """
    
    if isinstance(texts, list):
        ctext = [re.sub(r'\s+', ' ', ctext) for ctext in [re.sub(r'[[\]()<>{}!:,;-_|\."\'\\]', '', text) for text in texts]]
    
    elif isinstance(texts, (str, unicode)):
        ctext = re.sub(r'[(){}<>,\.!?;:\'"/\\\_|]', '', texts)
    
    return ctext

def rmBoring(texts):
    """
    Remove boring stuff.
    Warning: strong assumptions ahead...but we gotta do some chopping.
    """
    
    # overhead stuff
    ctext = re.sub(r'^From .*\n', '', texts, flags=re.MULTILINE)
    ctext = re.sub(r'^To .*\n', '', ctext, flags=re.MULTILINE)
    ctext = re.sub(r'^Case No .*\n', '', ctext, flags=re.MULTILINE)
    ctext = re.sub(r'^Sent .*\n', '', ctext, flags=re.MULTILINE)
    ctext = re.sub(r'^Doc No .*\n', '', ctext, flags=re.MULTILINE)
    ctext = re.sub(r'^Subject .*\n', '', ctext, flags=re.MULTILINE)
    
    # other misc
    ctext = re.sub(r'.*@.*', '', ctext) # emails
    ctext = re.sub(r'(?i)(monday|tuesday|wednesday|thursday|friday|saturday|sunday).*\d{3,4} [AP]M\n', '', ctext, flags = re.MULTILINE) # timestamps
    ctext = re.sub(r'Fw .*\n', '', ctext, flags = re.MULTILINE) # forward line
    ctext = re.sub(r'Cc .*\n', '', ctext, flags = re.MULTILINE) # Cc line
    ctext = re.sub(r'B[56(7C)]', '', ctext)
    
    # house benghazi committee stuff
    ctext = re.sub(r'Date 05132015.*\n', '', ctext, flags = re.MULTILINE) 
    ctext = re.sub(r'STATE DEPT  .*\n', '', ctext, flags = re.MULTILINE)
    ctext = re.sub(r'SUBJECT TO AGREEMENT.*\n', '', ctext, flags = re.MULTILINE)
    ctext = re.sub(r'US Department of State.*\n', '', ctext, flags = re.MULTILINE)

    return re.sub(r'\s+', ' ', ctext).lower()

def GetTextRange(df, person, dateFrom = '2008-05-01', dateTo = '2015-05-13'):
    """
    Returns string of all email text from particular date range for particular person
    
    dateFrom and dateTo must both be in formt 'YYYY-MM-DD'.
    """
    
    stoplist = set('for a of the and to in on from'.split())

    emails = df.loc[
        (df.MetadataDateSent > datetime.strptime(dateFrom, '%Y-%m-%d').date())
        & (df.MetadataDateSent < datetime.strptime(dateTo, '%Y-%m-%d').date())
        & (df.MetadataFrom.str.contains(person)), 
        'ExtractedBodyText'] \
    .values.tolist()
    
    return ' '.join([word for word in emails if word not in stoplist])

# get emails globally?
Emails = getEmails()
Emails.MetadataDateSent = pd.to_datetime(Emails.MetadataDateSent)

###############
# BEGIN VIEWS #
###############

@app.route('/')
@app.route('/index')
def index():
    return render_template('index.html')


@app.route('/counter', methods=['GET', 'POST'])
def counter():
    form = PersonTopicForm(request.form)

    personlist = request.args.getlist('personlist')
    topiclist = request.args.get('topiclist')

    if request.method == 'POST' and form.validate():        
        return redirect(url_for('counter'))

    return render_template('counter.html', 
                            form = form,
                            personlist = ','.join(personlist),
                            topiclist = topiclist)   


@app.route('/wordcloud', methods=['GET', 'POST'])
def wordcloud():
    form = WordcloudForm(request.form)

    person = request.args.get('person')

    if request.method == 'POST' and form.validate():        
        return redirect(url_for('wordcloud'))

    return render_template('wordcloud.html', 
                            form = form,
                            person = person)   

@app.route('/fig/<personlist>/<topiclist>/ptplot.png')
def ptplot(personlist, topiclist):

    PersonTopic = buildCounterDF(personlist.split(','), topiclist)

    # scale = len(personlist.join(','))

    plt.clf()

    sns.barplot(x='Person', y = 'count', hue = 'Topic', data=PersonTopic)
    plt.ylabel('Number of emails with mention')
    plt.xlabel('Sender of email')

    fig = plt.gcf()
    img = StringIO.StringIO()
    fig.savefig(img)
    img.seek(0)

    return send_file(img, mimetype='image/png')

@app.route('/fig/<person>/cloudplot.png')
def cloudplot(person):

    text = GetTextRange(Emails, person)
    text = rmBoring(rmNonAlpha(text)).decode('ascii', 'ignore')

    plt.clf()

    d = path.dirname(path.abspath(__file__))

    hilcolor = np.array(Image.open(path.join(d, "static/img/hillarylogo.jpg")))

    wc = WordCloud(background_color="white", max_words=150, mask=hilcolor,
               stopwords=STOPWORDS.add("said"),
               max_font_size=80, random_state=42,
               relative_scaling = 0.5)


    wc.generate(text)
    image_colors = ImageColorGenerator(hilcolor)

    plt.imshow(wc.recolor(color_func=image_colors))
    plt.axis("off")

    fig = plt.gcf()
    img = StringIO.StringIO()
    fig.savefig(img)
    img.seek(0)

    return send_file(img, mimetype='image/png')
