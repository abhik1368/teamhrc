from __future__ import division
import random
import StringIO
from datetime import datetime

import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
from matplotlib.figure import Figure

from flask import Flask, g, session, make_response
from flask import render_template, flash, redirect, url_for
from flask import request, send_file
from .forms import PersonTopicForm
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
    
    Ultimately this should return a pandas DF, but pandas is finicky.
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
        if isinstance(topics, list) 
        else {topics: df[col].loc[
                (df[col].str.contains(person, case = False))
                & (df['ExtractedBodyText'].str.contains(topics, case = False))
                & (df['MetadataDateSent'] > StartDate)
                & (df['MetadataDateSent'] < EndDate)].count()}
    )

# @cache.cached(timeout=600, key_prefix='emails')
def getEmails():
	con = mysql.connect()
	cur = con.cursor()
	sql = """SELECT * FROM Emails"""

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

	personlist = personlist.split(',')
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

	remap = {'^Abedin, Huma$': 'Huma Abedin', 
	        '^sbwhoeop$': 'Sidney Blumenthal', 
	        '^Sullivan, Jacob J$': 'Jacob Sullivan', 
	        '^H$': 'Hillary Clinton', 
	        '^Mills, Cheryl D$': 'Cheryl Mills'}

	PersonTopic.Person.replace(remap, inplace=True)

	return PersonTopic

# get emails globally?
Emails = getEmails()
Emails.MetadataDateSent = Emails.MetadataDateSent.astype('datetime64[ns]')

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

    personlist = request.args.get('personlist')
    topiclist = request.args.get('topiclist')
    
    if request.method == 'POST' and form.validate():        
        return redirect(url_for('counter'))

    return render_template('counter.html', 
                            form = form,
                            personlist = personlist,
                            topiclist = topiclist)   



@app.route('/fig/<personlist>/<topiclist>/plot.png')
def plot(personlist, topiclist):

	PersonTopic = buildCounterDF(personlist, topiclist)

	plt.clf()

	plt.rcParams['figure.figsize'] = [10,5]
	sns.barplot(x='Person', y = 'count', hue = 'Topic', data=PersonTopic)
	plt.ylabel('Number of emails with mention')
	plt.xlabel('Sender of email')
	
	fig = plt.gcf()
	img = StringIO.StringIO()
	fig.savefig(img)
	img.seek(0)

	return send_file(img, mimetype='image/png')

	# canvas = FigureCanvas(fig)
	# output = StringIO.StringIO()
	# canvas.print_png(output)
	# response = make_response(output.getvalue())
	# response.mimetype = 'image/png'
	# return response

# @app.route('/fig/<personlist>/<topiclist>')
# def fig(personlist, topiclist):
#     fig = draw_polygons(cropzonekey)
#     img = StringIO()
#     fig.savefig(img)
#     img.seek(0)
#     return send_file(img, mimetype='image/png')




