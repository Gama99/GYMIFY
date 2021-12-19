from flask import Flask, render_template, redirect, request
from flask_mongoengine import MongoEngine
from flask_user import login_required, UserManager, UserMixin, current_user, current_app
from turbo_flask import Turbo
import threading
import time
import keys
from queueManager import QueueItem, QueueManager
import spotipy
from spotipy.oauth2 import SpotifyOAuth


# Class-based application configuration
class ConfigClass(object):
    """ Flask application config """

    # Flask settings
    SECRET_KEY = 'masterGymifySecret'

    # Flask-MongoEngine settings
    MONGODB_SETTINGS = {
        'db': 'gymify',
        'host': 'mongodb://localhost:27017/gymify'
    }

    # Flask-User settings
    USER_APP_NAME = "GYMIFY"  # Shown in and email templates and page footers
    USER_ENABLE_EMAIL = False  # Disable email authentication
    USER_ENABLE_USERNAME = True  # Enable username authentication
    USER_REQUIRE_RETYPE_PASSWORD = False  # Simplify register form
    USER_COPYRIGHT_YEAR = "2021"
    USER_CORPORATION_NAME = "Team14"


def create_app():
    """ Flask application factory """

    # Setup Flask and load app.config
    app = Flask(__name__)
    app.debug = True
    app.config.from_object(__name__ + '.ConfigClass')

    # Setup Flask-MongoEngine
    db = MongoEngine(app)

    # Setup Turbo Flask
    turbo = Turbo(app)

    # Spotify API oAuth connection
    scope = "user-read-playback-state,user-modify-playback-state"
    sp = spotipy.Spotify(auth_manager=SpotifyOAuth(client_id=keys.client_ID, client_secret=keys.client_SECRET,
                                                   redirect_uri=keys.redirect_url, scope=scope, open_browser=True))

    dashboardData = {
        'CURRENTLYPLAYING': None,
        'COVER': None,
        'PROGRESS_BAR': None,
        'QUEUE1': {
            'empty': 'True',
            'track': None,
            'user': None
        },
        'QUEUE2': {
            'empty': 'True',
            'track': None,
            'user': None
        },
        'QUEUE3': {
            'empty': 'True',
            'track': None,
            'user': None
        }
    }

    songQueue = QueueManager()
    songQueue_lock = threading.Lock()

    # Define the User document.
    # NB: Make sure to add flask_user UserMixin !!!
    class User(db.Document, UserMixin):
        active = db.BooleanField(default=True)

        # User authentication information
        username = db.StringField(default='')
        password = db.StringField()

        # User information
        first_name = db.StringField(default='')
        last_name = db.StringField(default='')

        # Relationships
        roles = db.ListField(db.StringField(), default=[])


    # Setup Flask-User and specify the User data-model
    user_manager = UserManager(app, db, User)

    # The Home page is accessible to anyone
    @app.route('/')
    def home_page():

        return render_template('login.html')

    # The Members page is only accessible to authenticated users via the @login_required decorator
    @app.route('/dashboard', methods=['POST', 'GET'])
    @login_required  # User must be authenticated
    def dashboard():
        if request.method == 'POST':
            with songQueue_lock:
                if 'addSong' in request.form:
                    addSong = request.form.get('addSong')

                    results = sp.search(q=addSong, limit=1)
                    songQueue.put(QueueItem(results, current_user.username))

                elif 'vote1up' in request.form and not songQueue.empty():
                    if current_user.username not in songQueue.queue[0].votes:
                        songQueue.queue[0].votes.append(current_user.username)

                # elif 'vote1down' in request.form and not songQueue.empty():
                #     if current_user.username in songQueue.queue[0].votes:
                #         songQueue.queue[0].votes.remove(current_user.username)

                elif 'remove1' in request.form and (current_user.username == songQueue.queue[0].user):
                        del songQueue.queue[0]

                elif 'vote2up' in request.form and not songQueue.empty():
                    if current_user.username not in songQueue.queue[1].votes:
                        songQueue.queue[1].votes.append(current_user.username)

                # elif 'vote2down' in request.form and not songQueue.empty():
                #     if current_user.username in songQueue.queue[1].votes:
                #         songQueue.queue[1].votes.remove(current_user.username)

                elif 'remove2' in request.form and (current_user.username == songQueue.queue[1].user):
                        del songQueue.queue[1]

                elif 'vote3up' in request.form and not songQueue.empty():
                    if current_user.username not in songQueue.queue[2].votes:
                        songQueue.queue[2].votes.append(current_user.username)

                # elif 'vote3down' in request.form and not songQueue.empty():
                #     if current_user.username in songQueue.queue[2].votes:
                #         songQueue.queue[2].votes.remove(current_user.username)

                elif 'remove3' in request.form and (current_user.username == songQueue.queue[2].user):
                        del songQueue.queue[2]

                songQueue.sortQueue()
                return redirect('/dashboard')

        return render_template('dashboard.html')
        return render_template('dashboard.html')

    @app.context_processor
    def inject_load():
        return dashboardData

    @app.before_first_request
    def before_first_request():
        # with app.test_request_context('/dashboard', method='POST'):
        threading.Thread(target=update_Current_Playback).start()
        threading.Thread(target=addToSpotifyQueue).start()
        threading.Thread(target=update_Queue).start()

    def update_Current_Playback():
        with app.app_context():
            while True:
                result = sp.current_playback()

                artist = result['item']['artists'][0]['name']
                track = result['item']['name']
                coverImage = result['item']['album']['images'][1]['url']

                current_playback = str(track + ' - ' + artist)

                dashboardData['CURRENTLYPLAYING'] = current_playback
                dashboardData['COVER'] = coverImage
                dashboardData['PROGRESS_BAR'] = (result['progress_ms'] / result['item']['duration_ms']) * 100

                turbo.push(turbo.replace(render_template('loadCurrent.html'), 'load'))

    def update_Queue():
        with app.app_context():
            while True:
                time.sleep(2)
                with songQueue_lock:
                    if songQueue.size() > 0:
                        queue1 = songQueue.queue[0]
                        dashboardData['QUEUE1']['empty'] = 'False'
                        dashboardData['QUEUE1']['track'] = queue1.track['tracks']['items'][0]['name'] + \
                                                           ' - ' + queue1.track['tracks']['items'][0]['artists'][0][
                                                               'name']
                        dashboardData['QUEUE1']['user'] = queue1.user

                        if songQueue.size() > 1:
                            queue2 = songQueue.queue[1]
                            dashboardData['QUEUE2']['empty'] = 'False'
                            dashboardData['QUEUE2']['track'] = queue2.track['tracks']['items'][0]['name'] + \
                                                               ' - ' + queue2.track['tracks']['items'][0]['artists'][0][
                                                                   'name']
                            dashboardData['QUEUE2']['user'] = queue2.user

                        else:
                            dashboardData['QUEUE2']['empty'] = 'True'

                        if songQueue.size() > 2:
                            queue3 = songQueue.queue[2]
                            dashboardData['QUEUE3']['empty'] = 'False'
                            dashboardData['QUEUE3']['track'] = queue3.track['tracks']['items'][0]['name'] + \
                                                               ' - ' + queue3.track['tracks']['items'][0]['artists'][0][
                                                                   'name']
                            dashboardData['QUEUE3']['user'] = queue3.user


                        else:
                            dashboardData['QUEUE3']['empty'] = 'True'

                    else:
                        dashboardData['QUEUE1']['empty'] = 'True'
                        dashboardData['QUEUE2']['empty'] = 'True'
                        dashboardData['QUEUE3']['empty'] = 'True'

                    turbo.push(turbo.replace(render_template('loadQueue.html'), 'loadQueue'))

    def addToSpotifyQueue():
        while True:
            result = sp.current_playback()

            timeLeft = result['item']['duration_ms'] - result['progress_ms']

            if timeLeft < 15000:
                time.sleep((timeLeft / 1000))
                with songQueue_lock:
                    if not songQueue.empty():
                        sp.add_to_queue(songQueue.get().track['tracks']['items'][0]['uri'])

            time.sleep(5)

    # Example code to test a get spotipy wrapper working with Spotify API
    # def spot():
    #     scope = "user-read-playback-state,user-modify-playback-state"
    #     # sp = spotipy.Spotify(auth_manager=SpotifyOAuth(client_id=keys.client_ID, client_secret=keys.client_SECRET,
    #     #                                                redirect_uri=keys.redirect_url, scope=scope, open_browser=False))
    #     sp = spotipy.Spotify(auth_manager=SpotifyOAuth(scope=scope, open_browser=False))
    #
    #     results = sp.search(q='Dakiti', limit=1)
    #     print(results['tracks']['items'][0]['uri'])
    #     for i, t in enumerate(results['tracks']['items']):
    #         print(' ', i, t['uri'])
    #
    #     sp.start_playback(uris=[results['tracks']['items'][0]['uri']])
    #
    # return app

if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=80)
