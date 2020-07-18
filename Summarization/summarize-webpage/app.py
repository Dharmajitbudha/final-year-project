import traceback
from time import strftime

from flask import Flask, request, jsonify, make_response, render_template, redirect, url_for, session

from config.cfg_handler import CfgHandler
from config.cfg_utils import fetch_base_url
from framework.justext.core import justextHTML
from framework.parser.parser import Parser
from implement import word_frequency_summarize_parser
from flask_bootstrap import Bootstrap
#import database library
from flask_mysqldb import MySQL
import MySQLdb.cursors
import re

# Initialize the Flask application
app = Flask(__name__)

# Change this to your secret key (can be anything, it's for extra protection)
app.secret_key = 'your secret key'

# Enter your database connection details below
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = '1234'
app.config['MYSQL_DB'] = 'pythonlogin'

# Intialize MySQL
mysql = MySQL(app)

# REST Service methods


# handle undefined routes
@app.errorhandler(404)
def not_found(error):
    return make_response(jsonify({'error': str(error)}), 404)


@app.after_request
def after_request(response):
    """ Logging after every request. """
    # This avoids the duplication of registry in the log,
    # since that 500 is already logged via @app.errorhandler.
    if response.status_code != 500:
        ts = strftime('[%Y-%b-%d %H:%M]')
        app.logger.info('%s %s %s %s %s %s',
                        ts,
                        request.remote_addr,
                        request.method,
                        request.scheme,
                        request.full_path,
                        response.status)
    return response


@app.errorhandler(Exception)
def exceptions(exception):
    """ Logging after every Exception. """
    ts = strftime('[%Y-%b-%d %H:%M]')
    tb = traceback.format_exc()
    app.logger.error('%s %s %s %s %s ERROR:%s \n%s',
                     ts,
                     request.remote_addr,
                     request.method,
                     request.scheme,
                     request.full_path,
                     str(exception),
                     tb)

    return make_response(jsonify({'error': str(exception)}))



#login page 
@app.route('/', methods=['GET', 'POST'])
def login():
    # Output message if something goes wrong...
    msg = ''
    # Check if "username" and "password" POST requests exist (user submitted form)
    if request.method == 'POST' and 'username' in request.form and 'password' in request.form:
        # Create variables for easy access
        username = request.form['username']
        password = request.form['password']
        # Check if account exists using MySQL
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM accounts WHERE username = %s AND password = %s', (username, password,))
        # Fetch one record and return result
        account = cursor.fetchone()
        # If account exists in accounts table in out database
        if account:
            # Create session data, we can access this data in other routes
            session['loggedin'] = True
            session['id'] = account['id']
            session['username'] = account['username']
            # Redirect to home page
            return redirect(url_for('index'))
        else:
            # Account doesnt exist or username/password incorrect
            msg = 'Incorrect username/password!'
    # Show the login form with message (if any)
    return render_template('login.html', msg=msg)


    # this will be the logout page
@app.route('/logout')
def logout():
    # Remove session data, this will log the user out
   session.pop('loggedin', None)
   session.pop('id', None)
   session.pop('username', None)
   # Redirect to login page
   return redirect(url_for('login'))

#  this will be the registration page, we need to use both GET and POST requests
@app.route('/register', methods=['GET', 'POST'])
def register():
    # Output message if something goes wrong...
    msg = ''
    # Check if "username", "password" and "email" POST requests exist (user submitted form)
    if request.method == 'POST' and 'username' in request.form and 'password' in request.form and 'email' in request.form:
        # Create variables for easy access
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']

                # Check if account exists using MySQL
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM accounts WHERE username = %s', (username,))
        account = cursor.fetchone()
        # If account exists show error and validation checks
        if account:
            msg = 'Account already exists!'
        elif not re.match(r'[^@]+@[^@]+\.[^@]+', email):
            msg = 'Invalid email address!'
        elif not re.match(r'[A-Za-z0-9]+', username):
            msg = 'Username must contain only characters and numbers!'
        elif not username or not password or not email:
            msg = 'Please fill out the form!'
        else:
            # Account doesnt exists and the form data is valid, now insert new account into accounts table
            cursor.execute('INSERT INTO accounts VALUES (NULL, %s, %s, %s)', (username, password, email,))
            mysql.connection.commit()
            msg = 'You have successfully registered!'

    elif request.method == 'POST':
        # Form is empty... (no POST data)
        msg = 'Please fill out the form!'
    # Show registration form with message (if any)
    return render_template('register.html', msg=msg)

# test page 
@app.route('/login/index')
def home():
    # Check if user is loggedin
    if 'loggedin' in session:
        # User is loggedin show them the home page
        return render_template('index.html', username=session['username'])
    # User is not loggedin redirect to login page
    return redirect(url_for('login'))

#end of test page 

#main page of summarization 
@app.route('/index')
def index():
    # Check if user is loggedin to check session 
    if 'loggedin' in session:
        base_url = fetch_base_url(CfgHandler())
        return render_template('index.html', base_url=base_url)
     # User is not loggedin redirect to login page
    return redirect(url_for('login'))

# `summarize` method takes webpage url as argument and returns the summarized text as json object
@app.route('/v1/summarize', methods=['GET'])
def summarize():
    app.logger.debug('summarize(): requested')
    if 'url' not in request.args:
        return make_response(jsonify({'error': str('Bad Request: argument `url` is not available')}), 400)

    url = request.args['url']

    if not url:  # if url is empty
        return make_response(jsonify({'error': str('Bad Request: `url` is empty')}), 400)

    summary = ""

    try:
        # Fetch web content
        web_text = justextHTML(html_text=None, web_url=url)

        # Parse it via parser
        parser = Parser()
        parser.feed(web_text)

        # summary = facebook_parser_word_frequency_summarize.run_summarization(parser.paragraphs)
        summary = word_frequency_summarize_parser.run_summarization(parser.paragraphs)

    except Exception as ex:
        app.logger.error('summarize(): error while summarizing: ' + str(ex) + '\n' + traceback.format_exc())
        pass

    return make_response(jsonify({'summary': summary}))


if __name__ == '__main__':

    app.run(
        host="localhost"
    )
