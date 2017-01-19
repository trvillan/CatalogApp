from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database_setup import Base
from database_setup import User
from database_setup import Activities
from database_setup import Subcategories

import logging

from flask import Flask
from flask import render_template
from flask import request
from flask import redirect
from flask import url_for
from flask import flash
from flask import jsonify

from database_setup import Base
from database_setup import User
from database_setup import Activities
from database_setup import Subcategories

from flask import session as login_session
import random
import string

from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError
import httplib2
import json
from flask import make_response
import requests

app = Flask(__name__)

CLIENT_ID = json.loads(
    open('client_secrets.json', 'r').read())['web']['client_id']
APPLICATION_NAME = "FSWD P3 Application"

# Connect to Database and create database session
engine = create_engine('sqlite:///categories.db')
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
session = DBSession()


# Create a state token to prevent request forgery
# Store it in the session for later validation
@app.route('/login')
def showLogin():
    state = ''.join(random.choice(string.ascii_uppercase +
                    string.digits) for x in xrange(32))
    login_session['state'] = state
    return render_template('login.html', STATE=state)


@app.route('/gconnect', methods=['POST'])
def gconnect():
    # Validate state token
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    # Obtain authorization code
    code = request.data

    try:
        # Upgrade the authorization code into a credentials object
        oauth_flow = flow_from_clientsecrets('client_secrets.json', scope='')
        oauth_flow.redirect_uri = 'postmessage'
        credentials = oauth_flow.step2_exchange(code)
    except FlowExchangeError:
        response = make_response(
            json.dumps('Failed to upgrade the authorization code.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Check that the access token is valid.
    access_token = credentials.access_token
    url = ('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s'
           % access_token)
    h = httplib2.Http()
    result = json.loads(h.request(url, 'GET')[1])
    # If there was an error in the access token info, abort.
    if result.get('error') is not None:
        response = make_response(json.dumps(result.get('error')), 500)
        response.headers['Content-Type'] = 'application/json'

    # Verify that the access token is used for the intended user.
    gplus_id = credentials.id_token['sub']
    if result['user_id'] != gplus_id:
        response = make_response(
            json.dumps("Token's user ID doesn't match given user ID."), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is valid for this app.
    if result['issued_to'] != CLIENT_ID:
        response = make_response(
            json.dumps("Token's client ID does not match app's."), 401)
        print "Token's client ID does not match app's."
        response.headers['Content-Type'] = 'application/json'
        return response

    stored_token = credentials.access_token
    stored_gplus_id = login_session.get('gplus_id')
    if stored_token is not None and gplus_id == stored_gplus_id:
        response = make_response(json.dumps('Current user is \
            already connected.'), 200)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Store the access token in the session for later use.
    login_session['access_token'] = credentials.access_token
    login_session['gplus_id'] = gplus_id

    # Get user info
    userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
    params = {'access_token': credentials.access_token, 'alt': 'json'}
    answer = requests.get(userinfo_url, params=params)

    data = answer.json()

    login_session['username'] = data['name']
    login_session['picture'] = data['picture']
    login_session['email'] = data['email']

    output = ''
    output += '<h1>Welcome, '
    output += login_session['username']
    output += '!</h1>'
    output += '<img src="'
    output += login_session['picture']
    output += ' " style = "width: 300px; height: 300px;border-radius: \
            150px;-webkit-border-radius: 150px;-moz-border-radius: 150px;"> '
    if getUserID(login_session['email']) is None:
        createUser(login_session)
    flash("You are now logged in as %s" % login_session['username'])
    return output


# User Helper Functions
def createUser(login_session):
    newUser = User(
        name=login_session['username'],
        email=login_session['email'],
        picture=login_session['picture'])
    session.add(newUser)
    session.commit()
    user = session.query(User).filter_by(email=login_session['email']).one()
    return user.id


def getUserInfo(user_id):
    user = session.query(User).filter_by(id=user_id).one()
    return user


def getUserID(email):
    try:
        user = session.query(User).filter_by(email=email).one()
        return user.id
    except:
        return None

# DISCONNECT - Revoke a current user's token and reset their login_session
@app.route('/gdisconnect')
def gdisconnect():
    # Only disconnect a connected user.
    try:
        access_token = login_session['access_token']
    except:
        flash('Current user not connected.')
        return redirect(url_for('showLogin'))
    url = 'https://accounts.google.com/o/oauth2/revoke?token=%s' % access_token
    h = httplib2.Http()
    result = h.request(url, 'GET')[0]
    if result['status'] == '200':
        del login_session['access_token']
        del login_session['gplus_id']
        del login_session['username']
        del login_session['email']
        del login_session['picture']
        flash('Successfully disconnected.')
        return redirect(url_for('showLogin'))
    else:
        flash('Failed to revoke token for given user.')
        return redirect(url_for('activityList'))


# Main page
@app.route('/')
@app.route('/activities')
def activityList():
    activities = session.query(Activities).all()
    return render_template(
        'activities.html', activities=activities, login_session=login_session)


# Create new activity
@app.route('/activities/new', methods=['GET', 'POST'])
def activityListNew():
    if 'username' not in login_session:
        return redirect('/login')
    if request.method == 'POST':
        newItem = Activities(
            name=request.form['name'],
            user_id=getUserID(login_session['email']))
        session.add(newItem)
        session.commit()
        flash("New activity added")
        return redirect(url_for('activityList'))
    else:
        return render_template(
            'activities_new.html',
            login_session=login_session)


# Activities "make changes" page
# same as main page but with edit and delete buttons
@app.route('/activities/makechanges')
def activityListEdit():
    if 'username' not in login_session:
        return redirect('/login')
    activities = session.query(Activities).all()
    return render_template(
        'activities_makechanges.html',
        activities=activities,
        login_session=login_session)


# Main page for activity with items list
@app.route('/activities/<int:activity_id>')
def subCategory(activity_id):
    activity = session.query(Activities).filter_by(id=activity_id).one()
    subcategories = session.query(Subcategories).\
        filter_by(activity_id=activity_id).all()
    return render_template(
        'activity.html',
        activity=activity,
        subcategories=subcategories,
        login_session=login_session)


# Items "make changes" page
# same as subCategory page but with edit/delete buttons
@app.route('/activities/<int:activity_id>/makechanges')
def subCategoryEdit(activity_id):
    if 'username' not in login_session:
        return redirect('/login')
    activity = session.query(Activities).filter_by(id=activity_id).one()
    subcategories = session.query(Subcategories).\
        filter_by(activity_id=activity_id).all()
    return render_template(
        'activity_makechanges.html',
        activity=activity,
        subcategories=subcategories,
        login_session=login_session)


# Edit an item
# implemented authorization check for creator.
@app.route(
    '/activities/<int:activity_id>/makechanges/<int:item_id>/edit',
    methods=['GET', 'POST'])
def itemEdit(activity_id, item_id):
    editedItem = session.query(Subcategories).filter_by(id=item_id).one()
    creator = getUserInfo(editedItem.user_id)
    if 'username' not in login_session or creator.id != login_session['user_id']:
        return redirect('/login')
    if request.method == 'POST':
        if request.form['name']:
            editedItem.name = request.form['name']
            editedItem.user_id = getUserID(login_session['email'])
        session.add(editedItem)
        session.commit()
        flash("Item has been edited")
        return redirect(url_for('subCategoryEdit', activity_id=activity_id))
    else:
        return render_template(
            'activity_edit.html',
            activity_id=activity_id,
            item_id=item_id,
            item=editedItem,
            login_session=login_session)


# Delete an item
# Implemented authorization check for creator
@app.route(
    '/activities/<int:activity_id>/makechanges/<int:item_id>/delete',
    methods=['GET', 'POST'])
def itemDelete(activity_id, item_id):
    itemToDelete = session.query(Subcategories).filter_by(id=item_id).one()
    creator = getUserInfo(itemToDelete.user_id)
    if 'username' not in login_session or creator.id != login_session['user_id']:
        return redirect('/login')
    if request.method == 'POST':
        session.delete(itemToDelete)
        session.commit()
        flash("Item has been deleted!")
        return redirect(url_for('subCategoryEdit', activity_id=activity_id))
    else:
        return render_template(
            'activity_delete.html',
            item=itemToDelete,
            item_id=item_id,
            activity_id=activity_id,
            login_session=login_session)


# Create a new item
@app.route('/activities/<int:activity_id>/new', methods=['GET', 'POST'])
def itemNew(activity_id):
    if 'username' not in login_session:
        return redirect('/login')
    if request.method == 'POST':
        newItem = Subcategories(
            name=request.form['name'],
            activity_id=activity_id,
            user_id=getUserID(login_session['email']))
        session.add(newItem)
        session.commit()
        flash("New activity added")
        return redirect(url_for('subCategory', activity_id=activity_id))
    else:
        return render_template(
            'activity_new.html',
            activity_id=activity_id,
            login_session=login_session)


# Edit an activity
@app.route(
    '/activities/makechanges/<int:activity_id>/edit',
    methods=['GET', 'POST'])
def activityEdit(activity_id):
    if 'username' not in login_session:
        return redirect('/login')
    editedItem = session.query(Activities).filter_by(id=activity_id).one()
    if request.method == 'POST':
        if request.form['name']:
            editedItem.name = request.form['name']
            editedItem.user_id = getUserID(login_session['email'])
        session.add(editedItem)
        session.commit()
        flash("Activity has been edited")
        return redirect(url_for('activityListEdit'))
    else:
        return render_template(
            'activityname_edit.html',
            activity_id=activity_id,
            activity=editedItem,
            login_session=login_session)


# Delete an activity
@app.route(
    '/activities/makechanges/<int:activity_id>/delete',
    methods=['GET', 'POST'])
def activityDelete(activity_id):
    if 'username' not in login_session:
        return redirect('/login')
    itemToDelete = session.query(Activities).filter_by(id=activity_id).one()
    subItemsToDelete = session.query(Subcategories).\
        filter_by(activity_id=activity_id).all()
    if request.method == 'POST':
        session.delete(itemToDelete)
        session.commit()
        for i in subItemsToDelete:
            session.delete(i)
        session.commit()
        flash("Activity has been deleted!")
        return redirect(url_for('activityListEdit'))
    else:
        return render_template(
            'activities_delete.html',
            activity=itemToDelete,
            activity_id=activity_id,
            login_session=login_session)


# Making an API Endpoint (GET Request)
@app.route('/activities/JSON')
def activitiesJSON():
    items = session.query(Activities).all()
    return jsonify(ActivityList=[i.serialize for i in items])


# Making an API Endpoint (GET Request)
@app.route('/activities/JSON2')
def subcategoriesJSON():
    items = session.query(Subcategories).all()
    return jsonify(ActivityList=[i.serialize for i in items])


@app.route('/activities/<int:activity_id>/JSON')
def itemsJSON(activity_id):
    activities = session.query(Activities).filter_by(id = activity_id).one()
    items = session.query(Subcategories).filter_by(activity_id = activity_id).all()
    return jsonify(Subcategories=[i.serialize for i in items])


@app.route('/activities/<int:activity_id>/<int:item_id>/JSON')
def itemsJSON(activity_id, item_id):
    # activities = session.query(Activities).filter_by(id = activity_id).one()
    items = session.query(Subcategories).filter_by(id = item_id).one()
    return jsonify(Subcategories=items.serialize)

if __name__ == '__main__':
    app.secret_key = 'super_secret_key'
    app.debug = False
    app.run(host='0.0.0.0', port=8000)
