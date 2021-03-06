from flask import Flask, render_template, request, redirect, url_for, session
from flask_bootstrap import Bootstrap
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import timedelta

# from flaskext.mysql import MySQL
# import mysql.connector
import re
import sqlite3
import os.path
import json

app = Flask(__name__)
bootstrap = Bootstrap(app)

# Change this to your secret key (can be anything, it's for extra protection)
app.secret_key = 'Flask%Crud#Application'

app.permanent_session_lifetime = timedelta(minutes=5)


# Enter your database connection details below
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
db_path = os.path.join(BASE_DIR, "db.sqlite")

#SqLite database connection
conn = sqlite3.connect(db_path, check_same_thread=False)

movie_list = [] # movie list shown on page

@app.route('/')
def index():
    #load the json file containing movies
    f = open("static/movies.json", encoding="utf8")
    movieList = json.load(f)
    f.close()

    cursor = conn.cursor()

    #check movie table to see if already populated
    cursor.execute('SELECT * FROM movies')
    db_len = len(cursor.fetchall())

    #populate movie table with latest 1000 movies if not already populated
    if db_len == 0:
        for i in range(len(movieList) - 1, len(movieList) - 1001, -1):
            title = movieList[i]["title"]
            year = movieList[i]["year"]
            cast = movieList[i]["cast"]
            genreList = movieList[i]["genres"]
            cast_members = ''
            for member in cast:
                cast_members = cast_members + member + ', '
            cast_members = cast_members.rstrip(', ')
            genres = ''
            for genre in genreList:
                genres = genres + genre + ', '
            genres = genres.rstrip(', ')
            cursor.execute('INSERT INTO movies (title, year, movie_cast, genres) VALUES (?, ?, ?, ?)', (str(title), str(year), str(cast_members), str(genres)))

    conn.commit()

    return render_template('index.html')

@app.route('/home', methods=['GET', 'POST'])
def home():
    cursor = conn.cursor()
    # Check if user is loggedin
    if 'loggedin' in session:
        # variables
        k = "" # keyword string from user

        user = session['username']

        if request.method == 'POST': # POST method used when user submits query
            movie_list.clear()
            k = request.form['keyword_search']
            key_array = k.split(',')
            for key in key_array:
                # insert keyword into keyword search table in db
                key = key.strip(' ')
                cursor.execute('INSERT INTO user_search_activity (username, keyword_searched) VALUES (?, ?)', (user, key))
                conn.commit()
                key = '%' + key + '%' # makes each key search friendly
                # searches database with single keyword
                cursor.execute('SELECT * FROM movies WHERE title LIKE ? OR year LIKE ? OR genres LIKE ? OR movie_cast LIKE ?', (key, key, key, key,))
                # fetches all movies that met the criteria
                movies_in_genre = cursor.fetchall()
                for movie_tuple in movies_in_genre:
                    movie_string = str(movie_tuple)
                    movie_string = movie_string.strip("()'")
                    movie_array = movie_string.split(', ')
                    movie_array[0] = movie_array[0].strip("'")
                    # if the movie isn't already in the list then append to list
                    if movie_array[0] not in movie_list:
                        movie_list.append(movie_array[0])

            # show user the home page with a movie list
            return render_template('home.html', username=session['username'], movie_list=movie_list)
        else:
            # show user the home page without a movie list
            return render_template('home.html', username=session['username'])

    else:
    # User is not loggedin redirect to login page
        return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'loggedin' in session:
        return redirect(url_for('home'))

    # Output message if something goes wrong...
    msg = ''

    # Check if "username" and "password" POST requests exist (user submitted form)
    if request.method == 'POST' and 'username' in request.form and 'password' in request.form:
        session.permanent = True

        # Create variables for easy access
        username = request.form['username']
        password = request.form['password']

        # Check if user exists using MySQL
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE username = ?', (username,))

        # Fetch one record and return result
        user = cursor.fetchone()
        print(user)

        # If user exists in users table in the database
        if user and check_password_hash(user[4], password):

            # Create session data, we can access this data in other routes
            session['loggedin'] = True
            session['firstname'] = user[0]
            session['username'] = user[3]

            # Redirect to home page
            return redirect(url_for('home'))
        else:
            # user doesnt exist or username/password incorrect
            msg = 'Incorrect username/password! :/'

    # Show the login form with message (if any)
    return render_template('login.html', msg=msg)

@app.route('/register', methods=['GET', 'POST'])
def register():
    # Output message if something goes wrong...
    msg = ''

    # Check if "username", "password" and "email" POST requests exist (user submitted form)
    if request.method == 'POST' and 'username' in request.form and 'password' in request.form and 'email' in request.form:
        # Create variables for easy access
        first = request.form['firstname']
        last = request.form['lastname']
        email = request.form['email']
        username = request.form['username']
        password = request.form['password']
        hash = generate_password_hash(password)
        email = request.form['email']

        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE username = ?', (username,))  # SqLite Connect statement
        user = cursor.fetchone()

        # If user exists show error and validation checks
        if user:
            msg = 'Username/user already exists!'
        elif not re.match(r'[^@]+@[^@]+\.[^@]+', email):
            msg = 'Invalid email address!'
        elif not re.match(r'[A-Za-z0-9]+', username):
            msg = 'Username must contain only characters and numbers!'
        elif not username or not password or not email:
            msg = 'Please fill out the form!'
        else:
            # user doesnt exists and the form data is valid, now insert new user into users table
            # SqLite Insert Statement
            cursor.execute('INSERT INTO users (firstname, lastname, email, username, password) VALUES (?, ?, ?, ?, ?)',
                           (first, last, email, username, hash,))
            conn.commit()
            msg = 'You have successfully registered!'
            return render_template('login.html', msg=msg)

    elif request.method == "POST":
        # Form is empty... (no POST data)
        msg = 'Please fill all required fields!'

    # Show registration form with message (if any)
    return render_template('register.html', msg=msg)

@app.route('/logout')
def logout():
    # Remove session data, this will log the user out
    session.pop('loggedin', None)
    session.pop('firstname', None)
    session.pop('username', None)

    # Redirect to login page
    return redirect(url_for('login'))

@app.route('/update_movies_watched/<movie_name>')
def movies_watched(movie_name):
    cursor = conn.cursor()

    cursor.execute('SELECT genres FROM movies WHERE title LIKE ?', (movie_name,))
    preferred_genres = cursor.fetchall()
    preferred_genres = str(preferred_genres)
    preferred_genres = preferred_genres.strip("[]()',")
    # print(preferred_genres)
    user = session['username']
    cursor.execute('INSERT INTO user_watch_activity (username, movie_watched, genres) VALUES (?, ?, ?)', (user, movie_name, preferred_genres))
    conn.commit()
    return render_template('home.html', username=session['username'], movie_list=movie_list)

@app.route('/search_history')
def display_search_history():

    search_history = []
    watch_history = []
    cursor = conn.cursor()

    cursor.execute('SELECT * FROM user_search_activity')

    movies_in_search_history = cursor.fetchall()
    for movie_tuple in movies_in_search_history:
        movie_string = str(movie_tuple)
        movie_string = movie_string.strip("()'")
        movie_array = movie_string.split(', ')
        movie_array[1] = movie_array[1].strip("'")
        # if the movie isn't already in the list then append to list
        if movie_array[1] not in search_history:
            search_history.append(movie_array[1])

    cursor.execute('SELECT * FROM user_watch_activity')

    movies_in_watch_history = cursor.fetchall()
    for movie_tuple in movies_in_watch_history:
        movie_string = str(movie_tuple)
        movie_string = movie_string.strip("()'")
        movie_array = movie_string.split(', ')
        movie_array[1] = movie_array[1].strip("'")
        # if the movie isn't already in the list then append to list
        if movie_array[1] not in watch_history:
            watch_history.append(movie_array[1])

    return render_template('history.html', search_history=search_history, watch_history=watch_history)

if __name__ == '__main__':
    app.run()
