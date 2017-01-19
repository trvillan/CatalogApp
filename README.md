# Udacity Item Catalog Project
# By Tyler Villanueva
# Date: Jan 6, 2017

Description:

This app is meant to collect data on activities and items within those
activities. Items and activities can be created by users. A 3rd party
authentication system (Google+) is implemented to let users add, update
and delete. Also, this app implements API endpoints with a JSON format.

Requirements:
Vagrant
VirtualBox
Python 2.7

Steps to run:
1. Launch the Vagrant VM from inside the vagrant folder with:
vagrant up
vagrant ssh
Then move inside the catalog folder:
cd /vagrant/item-catalog

2. Setup the database by running:
python database_setup.py

3. Run the app by running:
python application.py

4. After the last command you are able to browse the application at this URL:
http://localhost:8000/

API endpoints:

You can use the following to receive JSON API endpoint information:
1. /activities/JSON
2. /activities/JSON2
3. /activities/*ACTIVITY ID*/JSON
4. /activities/*ACTIVITY ID*/*ITEM ID*/JSON