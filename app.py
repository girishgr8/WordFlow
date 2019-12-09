from flask import Flask, redirect, url_for, render_template, request, session, flash, Markup
from flask_mail import Mail, Message
from pymongo import MongoClient
import datetime
from models.db import *
from mongoengine import *
from werkzeug.utils import secure_filename
from wtforms import Form, StringField, TextAreaField, PasswordField, FileField, SelectField, TextField, validators
from wtforms.validators import DataRequired, Email
from passlib.hash import sha256_crypt
from wtforms.fields.html5 import EmailField, DateField
import dns
import json
import os
from functools import wraps

with open('config.json') as f:
	params = json.load(f)

# Creating instance of Flask...
app = Flask(__name__)
# Creating an instance of Mail class ...
mail = Mail(app)

app.secret_key = params["SECRET_KEY"]
senderEmail = 'codeintegrate1999@gmail.com'
# Set MONGO_URI for local dev server...
# app.config["MONGO_URI"] = "mongodb://localhost:27017/bloggerbit"
app.config['MAIL_SERVER']='smtp.gmail.com'
# Set path here for any uploads to be done on server side....
# app.config['UPLOAD_FOLDER'] = './uploads/'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USERNAME'] = str(params["MAIL_USER"])
app.config['MAIL_PASSWORD'] = str(params["MAIL_PASS"])
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USE_SSL'] = True
app.config['MAIL_DEBUG '] = True
# Set this to true if you want to test email sending module.. (Unit Testing)
app.config['MAIL_SUPPRESS_SEND'] = False
# Maximum file size allowed for upload
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024

# Connection to 'bloggerbit' MongoDB database....
dbName = str(params["DB_NAME"])
dbUser = str(params["DB_USER"])
dbPass = str(params["DB_PASS"])
connect(host='mongodb+srv://'+dbUser+':'+dbPass+'@devcluster-qbbgy.mongodb.net/'+dbName+'?retryWrites=true&w=majority')

# route() function is a decorator which tells the application which URL should call with the associated function..
# Render the html file which is to be loaded on the requested url...
# This render_template function checks for the templates folder inside the directory where app.py is present
	
# The data inside '< >' is passed as parameter to associated function....
# Passing the name parametere from the url i.e. app.route() passes it to the function.....

def permit_login(username, password):
	try:
		user = User.objects.get(pk=username)
		# Compare Passwords...
		if sha256_crypt.verify(password, user.password):
			session['username'] = username
			session['logged_in'] = True
			flash('Successfully logged in !', category='success')
			return redirect(url_for('dashboard'))
		else:
			flash('Passwords do not match', category='danger')
			return render_template("home.html")
	except DoesNotExist as e:
		flash('Please check login credentials !', category='danger')
		return render_template("home.html")

def is_logged_in(f):
	@wraps(f)
	def wrap(*args, **kwargs):
		if 'logged_in' in session:
			return f(*args, **kwargs)
		else:
			flash('Unauthorized, Please Login !', category='danger')
			return redirect(url_for('home'))
	return wrap

@app.route("/", methods=['POST', 'GET'])
def home():
	if request.method == 'POST':
		username = request.form["username"]
		password = request.form["password"]
		return permit_login(username, password)
	else:	
		if 'logged_in' in session:
			return redirect(url_for('dashboard'))
		else:
			return render_template("home.html")

# Form Validation for RegisterForm
class RegisterForm(Form):
	username = TextField('Username', [DataRequired(), validators.length(min=10, max=20)])
	name = TextField('Full Name', [DataRequired(), validators.length(max=80)])
	email = EmailField('Email', [DataRequired(), Email()])
	password = PasswordField('Password', [
		DataRequired(), 
		validators.length(min=8, max=30),
		validators.EqualTo('confirm', message='Passwords do not match !')
		])
	confirm = PasswordField('Confirm Password')
	birthDate = DateField('Birth Date', [DataRequired()])
	phone = StringField('Phone Number')
	choices = [('', 'Select Gender'),('male', 'Male'), ('female', 'Female'), ('can\'t say', 'Can\'t Say'), ('not specified', 'Not Specified')]
	gender = SelectField('Gender', choices=choices)
	profile_image = FileField('Profile Image', [validators.optional()])

@app.route('/register' , methods=['POST', 'GET'])
def register():
	form = RegisterForm(request.form)
	if request.method == 'POST' and form.validate():
		username = request.form["username"]
		name = request.form["name"]
		email = request.form["email"]
		password = sha256_crypt.encrypt(str(request.form["password"]))
		bdate = request.form["birthDate"]
		gender = request.form["gender"]
		profile_image = request.files["profile_image"]
		user = User(username, email=email, name=name, password=password, bdate=bdate, gender=gender, joined_on=datetime.datetime.utcnow())
		if profile_image.filename!= '':
			user.photo.replace(profile_image, filename=secure_filename(str(username+'.'+profile_image.filename.split('.')[-1])))
		user.save()
		session['username']	= username
		session['logged_in'] = True
		flash('You are registered now and can log in', category='success')
		return redirect(url_for("dashboard"))
	return render_template("register.html", form=form)

@app.route('/dashboard' , methods=['POST', 'GET'])
@is_logged_in
def dashboard():
	if 'logged_in' in session:
		posts = Post.objects(author=session["username"])
		for post in posts:
			post.created_on= str(post.created_on).split('.')[0]
			post.last_updated=str(post.last_updated).split('.')[0]
		return render_template("dashboard.html", username=session['username'], logged_in=session['logged_in'], posts=posts)
	else:
		return redirect(url_for('home'))

@app.route("/about", methods=['POST', 'GET'])
def about():
	if request.method == 'POST':
		#if user logins in after reading about.....
		username = request.form["username"]
		password = request.form["password"]
		return permit_login(username, password)

	elif request.method == 'GET':
		if 'logged_in' in session:
			return render_template("about.html", username=session['username'], logged_in=True)
		else:	
			return render_template("about.html", logged_in=False)

@app.route("/contact", methods=['POST', 'GET'])
def contact():
	if request.method == 'POST':
		#if user logins in after contacting.....
		try:
			username = request.form["username"]
			password = request.form["password"]
			return permit_login(username, password)
		except Exception as e:
			pass
		try:
			name = request.form["name"]
			email = request.form["email"]
			#service = request.form["service"]
			message = request.form["message"]
			msg = Message("Hello",sender=email, recipients=[senderEmail])
			msg.html = 'Details:<br>Name: '+name+'<br>Email: '+email+'<br>Message: '+message
			mail.send(msg)
			flash('Your message has been sent sucesfully !', category='success')
			if 'logged_in' in session:
				return render_template("contact.html", username=session['username'], logged_in=True)
			else:	
				return render_template("contact.html", logged_in=False)
		except Exception as e:
			flash('Some error occured',category='danger')
			return render_template('contact.html')

	elif request.method == 'GET':
		if 'logged_in' in session:
			return render_template("contact.html", username=session['username'], logged_in=True)
		else:	
			return render_template("contact.html", logged_in=False)

@app.route('/logout' , methods=['POST', 'GET'])
def logout():
	session.clear()
	return redirect(url_for('home'))

@app.errorhandler(404) 
def not_found(e):
	if 'logged_in' in session:
		return render_template('notfound.html', logged_in=True)
	elif not('logged_in' in session):
		return render_template('notfound.html', logged_in=False)

# Form Validation for ArticleForm
class ArticleForm(Form):
	title = TextField('Title', [DataRequired(), validators.length(min=1, max=200)])
	content = TextAreaField('Post')
	tags = TextAreaField('Tags')

@app.route('/<user>/new/', methods=['POST', 'GET'])
def newPost(user):
	form = ArticleForm(request.form)
	if request.method == 'POST' and form.validate():
		title = request.form["title"]
		content = request.form["content"]
		tags = request.form["tags"].split(' ')
		try:
			all_posts=Post.objects()
			last_pid = 1
			for i in all_posts:
				last_pid=i.pid
			post = Post(last_pid+1, title=title, author=user, content=content, created_on=datetime.datetime.utcnow(), last_updated=datetime.datetime.utcnow(), tags=tags)
			post.save()
			flash('New post saved sucesfully', category='success')
			return redirect(url_for('dashboard'))
		except Exception as e:
			print(e)
			flash(Markup('<b>Some error occured<b>New Post not created..'))
	return render_template('write.html', form=form, username=user)

@app.route('/<user>/edit/<int:pid>', methods=['POST', 'GET'])
def editPost(user,pid):
	form = ArticleForm(request.form)
	if request.method == 'POST' and form.validate():
		title = request.form["title"]
		content = request.form["content"]
		tags = request.form["tags"].split(' ')
		post = Post.objects.get(pk=pid, author=user)
		Post.objects(pk=pid).update_one(title=title, content=content, tags=tags, last_updated=datetime.datetime.utcnow())
		post = Post.objects.get(pk=pid, author=user)
		flash('Post edited succesfully', category='success')
		return render_template('edit.html',username=user, form=form, post=post, logged_in=True)

	elif request.method=='GET' and session["logged_in"]==True:
		post = Post.objects.get(pk=pid, author=user)
		form.content.data = post.content
		for tag in post.tags:
			form.tags.data+= tag+' '
		return render_template('edit.html', form=form, post=post, username=user, logged_in=True)

@app.route('/delete/<int:pid>', methods=['POST', 'GET'])
def deletePost(pid):
	if request.method=='GET' and 'logged_in' in session:
		post = Post.objects(pk=pid,author=session["username"]).delete()
		flash('Post deleted succesfully', category='success')
	return redirect(url_for('dashboard'))

@app.route('/pricing')
def pricing():
	if 'logged_in' in session:
		return render_template('pricing.html', username=session["username"], logged_in=True)

	return render_template('pricing.html')

@app.route('/<user>/view/<int:pid>')
def viewPost(user,pid):
	post = Post.objects.get(pk=pid)
	return render_template('post.html', username=user, logged_in=True, post=post)

if __name__ == "__main__":
# debug=True helps to render changes of website without need for running the server again & again....
	app.run(debug=True)


'''
To run the Flask Application on Windows Platform :-

Point to Flask App file => set FLASK_APP=app.py
Set Flask Environment to Development mode => set FLASK_ENV=development
Run the Flask App => flask run
Flask app url => http://127.0.0.1:5000/ 

To get version of python package use command => 
On Windows: pip freeze | findstr pymongo
On Linux: pip freeze | grep pymongo

start mongodb server => mongod

'''