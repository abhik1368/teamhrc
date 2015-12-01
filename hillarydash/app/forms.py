from flask.ext.wtf import Form
from wtforms import StringField, BooleanField, TextAreaField, SelectMultipleField, SelectField
from wtforms.validators import DataRequired

fullpersonlist = [('Hillary Clinton', 'Hillary Clinton'), 
    					('Sidney Blumenthal', 'Sidney Blumenthal'), 
    					('Huma Abedin', 'Huma Abedin'),
    					('Jake Sullivan', 'Jake Sullivan'),
    					('Cheryl Mills', 'Cheryl Mills'),
    					('Lauren Jiloty', 'Lauren Jiloty'),
    					('Philippe Reines', 'Philippe Reines'),
    					('Lona Valmoro', 'Lona Valmoro'),
    					('Anne Marie Slaughter', 'Anne Marie Slaughter'),
    					('Richard Verma', 'Richard Verma'),
    					('Melanne Verveer', 'Melanne Verveer'),
    					('Lissa Muscatine', 'Lissa Muscatine'),
    					('Judith McHale', 'Judith McHale'),
    					('Strobe Talbott', 'Strobe Talbott'),
    					('Betsy Ebeling', 'Betsy Ebeling'),
    					('Monica Hanley', 'Monica Hanley'),
    					('Robert Russo', 'Robert Russo'),
    					('Kris Balderston', 'Kris Balderston'),
    					('Cherie Blair', 'Cherie Blair')
    				]

class PersonTopicForm(Form):
    personlist = SelectMultipleField('personlist', 
    				choices = fullpersonlist, 
    				validators=[DataRequired()])

    topiclist = StringField('topiclist', validators=[DataRequired()])

class WordcloudForm(Form):
	person = SelectField('person',
					choices = fullpersonlist,
					validators = [DataRequired()])
