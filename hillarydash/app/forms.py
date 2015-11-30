from flask.ext.wtf import Form
from wtforms import StringField, BooleanField, TextAreaField
from wtforms.validators import DataRequired

class PersonTopicForm(Form):
    personlist = StringField('personlist', validators=[DataRequired()])
    topiclist = StringField('topiclist', validators=[DataRequired()])
