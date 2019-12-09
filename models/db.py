from mongoengine import *
import datetime

class User(Document):
	username = StringField(max_length=20, required=True, primary_key=True)
	email = EmailField(max_length=50, required=True)
	name = StringField(max_length=150, required=True)
	password = StringField(required=True)
	bdate = StringField(required=True)
	phone = StringField()
	gender = StringField(choices=("male", "female", "can't say", "not specified"), required=True)
	joined_on = DateTimeField(required=True)
	photo = ImageField()
#thumbnail_size(500,500)
class Post(Document):
	pid = IntField(required=True, primary_key=True)
	title = StringField(max_length=120,required=True)
	author = StringField(required=True)
	content = StringField()
	created_on = DateTimeField(required=True)
	last_updated = DateTimeField(required=True)
	#image = ImageField()
	tags = ListField(StringField(max_length=30))


'''
	username = db.Column('username', db.String(), primary_key = True, nullable=False)
	email = db.Column(db.String(), nullable=False)
	name = db.Column(db.String(), nullable=False)
	password = db.Column(db.String(), nullable=False)
	bdate = db.Column(db.String(), nullable=False)
	phone = db.Column(db.String(10))
	gender = db.Column(db.String(10))
	joined_on = db.Column(db.DateTime(), server_default=db.text('LOCALTIMESTAMP'))
'''