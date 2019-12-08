from flask import Flask, redirect, url_for, render_template, request, session, flash
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
import os

# Creating instance of Flask...
app = Flask(__name__)
# Creating an instance of Mail class ...
mail = Mail(app)

app.secret_key = 'bloggerbit'
senderEmail = 'blogbit99@gmail.com'
# Set MONGO_URI for local dev server...
# app.config["MONGO_URI"] = "mongodb://localhost:27017/bloggerbit"
app.config['MAIL_SERVER']='smtp.gmail.com'
# Set path here for any uploads to be done on server side....
# app.config['UPLOAD_FOLDER'] = './uploads/'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USERNAME'] = 'WEBSITE MAIL ID'
app.config['MAIL_PASSWORD'] = 'PASSWORD'
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USE_SSL'] = True
app.config['MAIL_DEBUG '] = True
# Set this to true if you want to test email sending module.. (Unit Testing)
app.config['MAIL_SUPPRESS_SEND'] = False
# Maximum file size allowed for upload
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024

# Connection to 'bloggerbit' MongoDB database....
dbName = "bloggerbit"
dbUser = "DB_USERNAME"
dbPass = "DB_PASS"
connect(host='mongodb+srv://'+dbUser+':'+dbPass+'@devcluster-qbbgy.mongodb.net/'+dbName+'?retryWrites=true&w=majority')

# route() function is a decorator which tells the application which URL should call with the associated function..
# Render the html file which is to be loaded on the requested url...
# This render_template function checks for the templates folder inside the directory where app.py is present
	
# The data inside '< >' is passed as parameter to associated function....
# Passing the name parametere from the url i.e. app.route() passes it to the function.....

@app.route("/", methods=['POST', 'GET'])
def home():
	if request.method == 'POST':
		username = request.form["username"]
		password = request.form["password"]
		try:
			user = User.objects.get(pk=username)
			# Compare Passwords...
			if sha256_crypt.verify(password, user.password):
				session['username'] = username
				session['logged_in'] = True
				print(session)
				flash('Successfully logged in !', category='success')
				return redirect(url_for('dashboard'))
			else:
				flash('Passwords do not match', category='danger')
				return render_template("home.html")
		except DoesNotExist as e:
			print(e)
			return render_template("home.html");
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

@app.route('/login', methods=['POST', 'GET'])
def login():
	if request.method == 'POST':
		username = request.form["username"]
		password = request.form["password"]
		session['username'] = request.form["username"]
		return redirect(url_for("dashboard"))
	else:
		return render_template("login.html");

@app.route('/dashboard' , methods=['POST', 'GET'])
def dashboard():
	if 'username' in session:
		return render_template("dashboard.html", username=session['username'], logged_in=session['logged_in'])
	else:
		return redirect(url_for('home'))

@app.route("/about", methods=['POST', 'GET'])
def about():
	if request.method == 'GET':
		return render_template("about.html", username=session['username'], logged_in=session['logged_in'])

@app.route("/contact", methods=['POST', 'GET'])
def contact():
	if request.method == 'POST':
		'''
		if user logins in after contacting.....
		username = request.form["username"]
		password = request.form["password"]
		'''
		name = request.form["name"]
		email = request.form["email"]
		#service = request.form["service"].value
		message = request.form["message"]
		msg = Message("Hello",sender=email, recipients=[senderEmail])
		msg.html = 'Details:<br>Name: '+name+'<br>Email: '+email+'<br>Message: '+message
		mail.send(msg)
		if 'logged_in' in session:
			return render_template("contact.html", mailSent=True, username=session['username'], logged_in=session['logged_in'])
		else:	
			return render_template("contact.html", mailSent=True, logged_in=False)
	elif request.method == 'GET':
		if 'logged_in' in session:
			return render_template("contact.html", username=session['username'], logged_in=True)
		else:	
			return render_template("contact.html", logged_in=False)

@app.route('/logout' , methods=['POST', 'GET'])
def logout():
	session.clear()
	print(session)
	return redirect(url_for('home'))

@app.errorhandler(404) 
def not_found(e):
	if 'logged_in' in session:
		return render_template('notfound.html', logged_in=True)
	elif not('logged_in' in session):
		return render_template('notfound.html', logged_in=False)

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