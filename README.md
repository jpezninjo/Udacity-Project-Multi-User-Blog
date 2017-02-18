# Udacity-Project-Multi-User-Blog
  
  This is my project repository for the Udacity Online Nano Degree, Intro to Backend, Multi-User Blog Project
Everything below this line is for future me to read


Website at: https://udacity-project-user-blog.appspot.com/
_________________________________________________

##Dude congrats! You made this in under 48 hours and wrote a 575+ lined python file!

This app was built using Python 2.7. It uses webapp2.WSGIApplication.
It does not use Flask. It does use the Jinja2 template engine.
Data is stored in an instance of the google.appengine.ext > db

Google Cloud SDK

Download the cloud SDK and then open up the cloud command-line interface.
From there, type the command to download the Python SDK.

Use the gcloud project set command to link your gcloud to your online project (via id ex. "udacity-project-multi-user-blog")


###Running locally
On a Windows 10,
C:\Users\Chell II\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin
contains a dev-server.py file
You call python dev-server.py [app.yaml] file to start a server on localhost (admin at :8000, actual site at :8080)
We freaking cheated by keeping all our code in a folder called hw4 (lol) and calling python dev-server.py ./hw4/app.yaml



###Directory structure
* static
  * css files
* templates
  * html forms
* app.yaml
* blog.py
* other less important files

  
###app.yaml
Contains our project info needed for the Google App Engine


###blog.py
The very bottom contains the following line
  app = webapp2.WSGIApplication([('/', BlogFront),
                                 ('/welcome', Welcome),
                               
This is your request router

We have created a class BlogHandler which extends the webapp2.RequestHandler

Every request handler is its own class with extends BlogHandler


###Three data models: Post, User, Comment

Each Post cheats by storing User.username, not the actual User object

Each Post has a one-to-many relationship with Comment. This relationship is actually defined in the Comment model for some godamn reason


We have prepped the User model with some helper functions:
    def register(cls, name, pw, email = None):
    def login(cls, name, pw):
    def userExists(cls, name):
    


This site features the following:
  user account system with creation and login capabilities
  Secure password storing using the generic
  ```h = hashlib.sha256(name + pw + salt).hexdigest()```
  I really don't care enough about putting this out there
  
Post creation, post-editting, and deleting with server-side user validation
Post upvoting and downvoting
Comment system with comment-editing and deleting with server-side user validation


A Kickass colorschema
