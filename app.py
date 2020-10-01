from flask import Flask, redirect, url_for, render_template, request, session, flash, Markup
from flask_mail import Mail, Message
import datetime
from werkzeug.utils import secure_filename
from wtforms import Form, StringField, TextAreaField, PasswordField, FileField, SelectField, TextField, validators
from wtforms.validators import DataRequired, Email
from passlib.hash import sha256_crypt
from wtforms.fields.html5 import EmailField, DateField
import json
import os
from functools import wraps
from flask_sqlalchemy import SQLAlchemy

with open('config.json') as f:
	params = json.load(f)

# Creating instance of Flask...
app = Flask(__name__)

basedir = os.path.abspath(os.path.dirname(__file__))

app.secret_key = params["SECRET_KEY"]
senderEmail = params["MAIL_USER"]
# Set MONGO_URI for local dev server...
# app.config["MONGO_URI"] = "mongodb://localhost:27017/wordflow"
app.config['MAIL_SERVER']='smtp.gmail.com'
# Set path here for any uploads to be done on server side....
# app.config['UPLOAD_FOLDER'] = './uploads/'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USERNAME'] = params["MAIL_USER"]
app.config['MAIL_PASSWORD'] = params["MAIL_PASS"]
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USE_SSL'] = True
app.config['MAIL_DEBUG '] = True
# Set this to true if you want to test email sending module.. (Unit Testing)
app.config['MAIL_SUPPRESS_SEND'] = False
# Maximum file size allowed for upload
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'db.sqlite')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = True

# Creating an instance of Mail class ...
mail = Mail(app)

# Creating an instance of SQLAlchemy class ...
db = SQLAlchemy(app)

class User(db.Model):
	username = db.Column(db.String(40), primary_key = True, nullable=False)
	email = db.Column(db.String(100), unique=True, nullable=False)
	name = db.Column(db.String(), nullable=False)
	password = db.Column(db.String(), nullable=False)
	bdate = db.Column(db.String(), nullable=False)
	phone = db.Column(db.String())
	gender = db.Column(db.String(10))
	joined_on = db.Column(db.DateTime(), server_default=db.text('LOCALTIMESTAMP'))

class Post(db.Model):
	pid = db.Column(db.Integer, primary_key=True)
	title= db.Column(db.String(80), nullable=False)
	author = db.Column(db.String(40), nullable=False)
	content = db.Column(db.String(100), nullable=False)
	created_on = db.Column(db.DateTime, nullable=False)
	last_updated = db.Column(db.DateTime, nullable=False)
	tags = db.Column(db.String(50), nullable=False)

# route() function is a decorator which tells the application which URL should call with the associated function..
# Render the html file which is to be loaded on the requested url...
# This render_template function checks for the templates folder inside the directory where app.py is present
	
# The data inside '< >' is passed as parameter to associated function....
# Passing the name parametere from the url i.e. app.route() passes it to the function.....

def permit_login(username, password):
	try:
		user = User.query.filter_by(username=username).first()
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
	username = TextField('Username', [DataRequired(), validators.length(min=4, max=13)])
	name = TextField('Full Name', [DataRequired(), validators.length(max=80)])
	email = EmailField('Email', [DataRequired(), Email()])
	password = PasswordField('Password', [
		DataRequired(), 
		validators.length(min=8, max=30),
		validators.EqualTo('confirm', message='Passwords do not match !')
		])
	confirm = PasswordField('Confirm Password')
	birthDate = DateField('Birth Date', [DataRequired()])
	phone = TextField('Phone Number')
	choices = [('', 'Select Gender'),('male', 'Male'), ('female', 'Female'), ('can\'t say', 'Can\'t Say'), ('not specified', 'Not Specified')]
	gender = SelectField('Gender', choices=choices, default='')
	profile_image = FileField('Profile Image', [validators.optional()])

@app.route('/register' , methods=['POST', 'GET'])
def register():
	form = RegisterForm(request.form)
	#if user logins from register page.....
	try:
		username = request.form["username"]
		password = request.form["password"]
		return permit_login(username, password)
	except Exception as e:
		pass
		try:
			if request.method == 'POST' and form.validate():
				username = request.form["username"]
				name = request.form["name"]
				email = request.form["email"]
				password = sha256_crypt.hash(str(request.form["password"]))
				bdate = request.form["birthDate"]
				gender = request.form["gender"]
				profile_image = request.files["profile_image"]
				user = User(username=username, email=email, name=name, password=password, bdate=bdate, gender=gender, joined_on=datetime.datetime.utcnow())
				db.session.add(user)
				db.session.commit()
				session['username']	= username
				session['logged_in'] = True
				flash('Successfully created account !', category='success')
				return redirect(url_for("dashboard"))
			else:
				return render_template("register.html", form=form)
		except Exception as e:
			flash('Some error occured.', category='danger')
			return render_template('register.html', form=form)

@app.route('/dashboard' , methods=['POST', 'GET'])
@is_logged_in
def dashboard():
	if 'logged_in' in session:
		# Getting recent posts...
		posts = Post.query.filter(Post.author != session["username"]).order_by(Post.created_on.desc(), Post.last_updated.desc()).all()
		current_user_posts = Post.query.filter_by(author=session["username"]).all()
		for post in posts:
			post.created_on= str(post.created_on).split('.')[0]
			post.last_updated=str(post.last_updated).split('.')[0]
		return render_template("dashboard.html", username=session['username'], logged_in=session['logged_in'], posts=posts, current_user_posts=current_user_posts)
	else:
		return redirect(url_for('home'))

@app.route("/about", methods=['POST', 'GET'])
def about():
	if request.method == 'POST':
		try:
			#if user logins in from about page.....
			username = request.form["username"]
			password = request.form["password"]
			return permit_login(username, password)
		except Exception as e:
			pass
			try:
				notifMailID = request.form["notifMailID"]
				if not(notifMailID == ''):
					msg = Message("Hello",sender=params["MAIL_USER"], recipients=[params["MAIL_USER"]])
					msg.html = 'Email ID: '+notifMailID
					mail.send(msg)
					flash('You\'ll be soon notified about the launch updates !', category='success')
					if 'logged_in' in session:
						return redirect(url_for('dashboard'))
					else:
						if 'logged_in' in session:
							return render_template('about.html', logged_in=True, username=session['username'], rel_date=params["RELEASE_DATE"])
						else:
							return render_template('about.html', logged_in=False, rel_date=params["RELEASE_DATE"])
				else:
					flash('Please enter an email address...', category='danger')
					if 'logged_in' in session:
						return render_template('about.html', logged_in=True, username=session['username'], rel_date=params["RELEASE_DATE"])
					else:
						return render_template('about.html', logged_in=False, rel_date=params["RELEASE_DATE"])
			except Exception as e:
				print(e)
				flash('Some error occured...!', category='danger')
				if 'logged_in' in session:
					return render_template('about.html', logged_in=True, username=session['username'], rel_date=params["RELEASE_DATE"])
				else:
					return render_template('about.html', logged_in=False, rel_date=params["RELEASE_DATE"])

	elif request.method == 'GET':
		if 'logged_in' in session:
			return render_template("about.html", username=session['username'], logged_in=True, rel_date=params["RELEASE_DATE"])
		else:	
			return render_template("about.html", logged_in=False, rel_date=params["RELEASE_DATE"])

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
			msg = Message("Hello",sender=senderEmail, recipients=[email])
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
@is_logged_in
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
@is_logged_in
def newPost(user):
	form = ArticleForm(request.form)
	if request.method == 'POST' and form.validate():
		title = request.form["title"]
		content = request.form["content"]
		tags = request.form["tags"]
		try:
			post = Post(title=title, author=user, content=content, created_on=datetime.datetime.utcnow(), last_updated=datetime.datetime.utcnow(), tags=tags)
			db.session.add(post)
			db.session.commit()
			flash('New post saved sucesfully', category='success')
			return redirect(url_for('dashboard'))
		except Exception as e:
			flash(Markup('<b>Some error occured</b> ! New Post not created..'), category='danger')
	return render_template('write.html', form=form, username=user, logged_in=True)

@app.route('/<user>/edit/<int:pid>', methods=['POST', 'GET'])
@is_logged_in
def editPost(user,pid):
	form = ArticleForm(request.form)
	if request.method == 'POST' and form.validate():
		title = request.form["title"]
		content = request.form["content"]
		tags = request.form["tags"]
		post = Post.query.filter_by(pid=pid).first()
		post.title = title
		post.content = content
		post.tags = tags
		post.last_updated = datetime.datetime.utcnow()
		db.session.commit()
		flash('Post edited succesfully', category='success')
		return render_template('edit.html',username=user, form=form, post=post, logged_in=True)

	elif request.method=='GET':
		post = Post.query.filter_by(pid=pid).first()
		form.content.data = post.content
		form.tags.data = post.tags
		return render_template('edit.html', form=form, post=post, username=user, logged_in=True)

@app.route('/delete/<int:pid>', methods=['POST', 'GET'])
@is_logged_in
def deletePost(pid):
	if request.method=='GET':
		del_post = Post.query.filter_by(pid=pid).first()
		db.session.delete(del_post)
		db.session.commit()
		flash('Post deleted succesfully', category='success')
	return redirect(url_for('dashboard'))

@app.route('/pricing', methods=['POST', 'GET'])
def pricing():
	if request.method == 'POST':
		#if user logins in after checking pricing for various features.....
		username = request.form["username"]
		password = request.form["password"]
		return permit_login(username, password)

	elif request.method == 'GET':
		if 'logged_in' in session:
			return render_template('pricing.html', username=session["username"], logged_in=True)
		else:
			return render_template('pricing.html', logged_in=False)

@app.route('/<user>/view/<int:pid>')
@is_logged_in
def viewPost(user,pid):
	post = Post.query.filter_by(pid=pid).first()
	post.created_on= str(post.created_on).split('.')[0]
	post.last_updated=str(post.last_updated).split('.')[0]
	return render_template('post.html', username=session["username"], logged_in=True, post=post)

@app.route('/<user>/blogs')
@is_logged_in
def userBlogs(user):
	posts = Post.query.filter_by(author=user).all()
	for post in posts:
		post.created_on= str(post.created_on).split('.')[0]
		post.last_updated=str(post.last_updated).split('.')[0]
	return render_template('post.html', username=session["username"], logged_in=True, post=posts, userBlog=True)

@app.route('/help', methods=['POST', 'GET'])
def help():
	if request.method == 'POST':
		# if user logins in after checking for help questions.....
		username = request.form["username"]
		password = request.form["password"]
		return permit_login(username, password)
	elif request.method == 'GET':
		if 'logged_in' in session:
			return render_template('help.html', username=session["username"], logged_in=True)
		else:
			return render_template('help.html', logged_in=False)

class ProfileForm(Form):
	username = TextField('Username', [DataRequired(), validators.length(min=4, max=13)])
	name = TextField('Full Name', [DataRequired(), validators.length(max=80)])
	email = EmailField('Email', [DataRequired(), Email()])
	birthDate = DateField('Birth Date', [DataRequired()])
	phone = TextField('Phone Number')
	oldPassword = PasswordField('Old Password', [DataRequired(), validators.length(min=8, max=30)])
	newPassword = PasswordField('New Password', [DataRequired(), validators.length(min=8, max=30)])
	choices = [('', 'Select Gender'), ('male', 'Male'), ('female', 'Female'), ('can\'t say', 'Can\'t Say'), ('not specified', 'Not Specified')]
	gender = SelectField('Gender', choices=choices)

@app.route('/profile/<user>', methods=['GET', 'POST'])
@is_logged_in
def profile(user):
	user = User.query.filter_by(username=user).first()
	form = ProfileForm(request.form)
	if request.method == 'POST' and form.validate():
		username = request.form["username"]
		name = request.form["name"]
		email = request.form["email"]
		bdate = request.form["birthDate"]
		phone = request.form["phone"]
		gender = request.form["gender"]
		oldPassword = request.form["oldPassword"]
		newPassword = request.form["newPassword"]
		try:
			if sha256_crypt.verify(oldPassword, user.password):
				user.username = username
				user.name = name
				user.email = email
				user.bdate = bdate
				user.phone = phone
				user.gender = gender
				user.password = sha256_crypt.hash(str(newPassword))
				db.session.commit()
				flash('Profile edited succesfully !', category='success')
				return redirect(url_for("dashboard"))
			else:
				flash('Kindly enter correct current password', category='danger')
				return render_template('profile.html', username=session["username"], logged_in=True, user=user, form=form)	
		except Exception as e:
			return render_template('profile.html', username=session["username"], logged_in=True, user=user, form=form)
	else:
		return render_template('profile.html', username=session["username"], logged_in=True, user=user, form=form)

if __name__ == "__main__":
# debug=True helps to render changes of website without need for running the server again & again....
	app.run(debug=True)


'''
To run the Flask Application on Windows Platform :-

Point to Flask App file => set FLASK_APP=app.py
Set Flask Environment to Development mode => set FLASK_ENV=development
Run the Flask App => flask run
Flask app url => http://127.0.0.1:5000/ 

for creating sqlite3 DB:
In python shell do following:
	from app import db
	db.create_all()

To get version of python package use command => 
On Windows: pip freeze | findstr pymongo
On Linux: pip freeze | grep pymongo

start mongodb server => mongod

'''
