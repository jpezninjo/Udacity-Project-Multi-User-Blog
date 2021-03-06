import os
import re
import random
import hashlib
import hmac
from string import letters

import webapp2
import jinja2

from google.appengine.ext import db

template_dir = os.path.join(os.path.dirname(__file__), 'templates')
jinja_env = jinja2.Environment(loader = jinja2.FileSystemLoader(template_dir),
                               autoescape = True)

secret = 'keyboard cat'

def render_str(template, **params):
    t = jinja_env.get_template(template)
    return t.render(params)

def make_secure_val(val):
    return '%s|%s' % (val, hmac.new(secret, val).hexdigest())

def check_secure_val(secure_val):
    val = secure_val.split('|')[0]
    if secure_val == make_secure_val(val):
        return val

class BlogHandler(webapp2.RequestHandler):
    def write(self, *a, **kw):
        self.response.out.write(*a, **kw)

    def render_str(self, template, **params):
        params['user'] = self.user
        return render_str(template, **params)

    def render(self, template, **kw):
        self.write(self.render_str(template, **kw))

    def set_secure_cookie(self, name, val):
        cookie_val = make_secure_val(val)
        self.response.headers.add_header(
            'Set-Cookie',
            '%s=%s; Path=/' % (name, cookie_val))

    def read_secure_cookie(self, name):
        cookie_val = self.request.cookies.get(name)
        return cookie_val and check_secure_val(cookie_val)

    def login(self, user):
        self.set_secure_cookie('user_id', str(user.key().id()))

    def logout(self):
        self.response.headers.add_header('Set-Cookie', 'user_id=; Path=/')

    def initialize(self, *a, **kw):
        webapp2.RequestHandler.initialize(self, *a, **kw)
        uid = self.read_secure_cookie('user_id')
        self.user = uid and User.by_id(int(uid))

def render_post(response, post):
    response.out.write('<b>' + post.subject + '</b><br>')
    response.out.write(post.content)

class MainPage(BlogHandler):
  def get(self):
      self.write('Hello, Udacity!')

##### user stuff
def make_salt(length = 5):
    return ''.join(random.choice(letters) for x in xrange(length))

def make_pw_hash(name, pw, salt = None):
    if not salt:
        salt = make_salt()
    h = hashlib.sha256(name + pw + salt).hexdigest()
    return '%s,%s' % (salt, h)

def valid_pw(name, password, h):
    salt = h.split(',')[0]
    return h == make_pw_hash(name, password, salt)

def users_key(group = 'default'):
    return db.Key.from_path('users', group)

class User(db.Model):
    name = db.StringProperty(required = True)
    pw_hash = db.StringProperty(required = True)
    email = db.StringProperty()

    @classmethod
    def by_id(cls, uid):
        return User.get_by_id(uid, parent = users_key())

    @classmethod
    def by_name(cls, name):
        u = User.all().filter('name =', name).get()
        return u

    @classmethod
    def register(cls, name, pw, email = None):
        pw_hash = make_pw_hash(name, pw)
        return User(parent = users_key(),
                    name = name,
                    pw_hash = pw_hash,
                    email = email)

    @classmethod
    def login(cls, name, pw):
        u = cls.by_name(name)
        if u and valid_pw(name, pw, u.pw_hash):
            return u

    @classmethod
    def userExists(cls, name):
        u = cls.by_name(name)
        if u:
            return True
        else:
            return False

##### blog stuff
def blog_key(name = 'default'):
    return db.Key.from_path('blogs', name)

class Post(db.Model):
    subject = db.StringProperty(required = True)
    owner = db.StringProperty(required = False)
    content = db.TextProperty(required = True)
    
    user_upvotes = db.StringProperty()
    user_downvotes = db.StringProperty()

    created = db.DateTimeProperty(auto_now_add = True)
    last_modified = db.DateTimeProperty(auto_now = True)

    
    def render(self, link_to_self = False):
        self._render_text = self.content.replace('\n', '<br>')
        self.id = str(self.key().id())
        return render_str("post.html", p = self,
            upvotes = len(self.user_upvotes.split("|")) - 1 if self.user_upvotes else 0,
            downvotes = len(self.user_downvotes.split("|")) - 1 if self.user_downvotes else 0,
            link_to_self = link_to_self)

    def render_properties(self):
        return ('subject=%s owner=%s content=%s user_upvotes=%s user_downvotes=%s' %
            (self.subject, self.owner, self.content, self.user_upvotes, self.user_downvotes))

###Comment stuff
def comment_key(name = 'default'):
    return db.Key.from_path('comments', name)

class Comment(db.Model):
    owner = db.StringProperty(required = False)
    content = db.TextProperty(required = True)
    created = db.DateTimeProperty(auto_now_add = True)
    
    post = db.ReferenceProperty(Post, collection_name='post_comments')

    def render(self):
        self._render_text = self.content.replace('\n', '<br>')
        self.id = str(self.key().id())
        return render_str("post.html", p = self, upvotes = self.user_upvotes, downvotes = self.user_downvotes, link_to_self = link_to_self)

    def render_properties(self):
        return ('owner=%s content=%s' % (self.owner, self.content))

    def getID(self):
        return str(self.key().id())

    @classmethod
    def by_id(cls, uid):
        return Comment.get_by_id(uid, parent = comment_key())







class BlogFront(BlogHandler):
    def get(self):
        posts = greetings = Post.all().order('-created')
        self.render('front.html', posts = posts)

class PostPage(BlogHandler):
    def get(self, post_id):
        key = db.Key.from_path('Post', int(post_id), parent=blog_key())
        post = db.get(key)

        if not post:
            self.error(404)
            return

        self.render("permalink.html", post = post)

class NewPost(BlogHandler):
    def get(self):
        if self.user:
            self.render("newpost.html")
        else:
            self.redirect("/login")

    def post(self):
        if not self.user:
            self.redirect('/blog')

        subject = self.request.get('subject')
        anonymous = self.request.get('anonymous')
        username = self.user.name
        if anonymous:
            username = anonymous
        # self.read_secure_cookie("user")
        content = self.request.get('content')

        if subject and content:
            p = Post(parent = blog_key(), subject = subject, owner = username, user_upvotes="", user_downvotes="", content = content)
            p.put()
            self.redirect('/blog/%s' % str(p.key().id()))
        else:
            error = "subject and content, please!"
            self.render("newpost.html", subject=subject, content=content, error=error)

USER_CHAR_RE = re.compile(r"^[a-zA-Z0-9]+")
def valid_username_chars(username):
    return username and USER_CHAR_RE.match(username)

USER_LEN_RE = re.compile(r"^[a-zA-Z0-9_-]{3,20}$")
def valid_username_len(username):
    return username and USER_LEN_RE.match(username)

PASS_RE = re.compile(r"^.{3,20}$")
def valid_password(password):
    return password and PASS_RE.match(password)

EMAIL_RE  = re.compile(r'^[\S]+@[\S]+\.[\S]+$')
def valid_email(email):
    return not email or EMAIL_RE.match(email)

class Signup(BlogHandler):
    def get(self):
        self.render("signup-form.html")

    def post(self):
        have_error = False
        self.username = self.request.get('username')
        self.password = self.request.get('password')
        self.verify = self.request.get('verify')
        self.email = self.request.get('email')

        params = dict(username = self.username,
                      email = self.email)

        if not valid_username_chars(self.username):
            params['error_username'] = "Valid usernames must contain only letters, numbers and dashes"
            have_error = True
        elif not valid_username_len(self.username):
            params['error_username'] = "Valid usernames must be between 3 and 20 characters"
            have_error = True
        elif User.userExists(self.username):
            params['error_username'] = "That username is taken"
            have_error = True

        if not valid_password(self.password):
            params['error_password'] = "That wasn't a valid password."
            have_error = True
        elif self.password != self.verify:
            params['error_verify'] = "Your passwords didn't match."
            have_error = True

        if not valid_email(self.email):
            params['error_email'] = "That's not a valid email."
            have_error = True

        if have_error:
            self.render('signup-form.html', **params)
        else:
            self.done()

    def done(self, *a, **kw):
        raise NotImplementedError

class Signup(Signup):
    def done(self):
        self.redirect('/welcome?username=' + self.username)

class Register(Signup):
    def done(self):
        #make sure the user doesn't already exist
        u = User.by_name(self.username)
        if u:
            msg = 'That user already exists.'
            self.render('signup-form.html', error_username = msg)
        else:
            u = User.register(self.username, self.password, self.email)
            u.put()

            self.login(u)
            self.redirect('/blog')

class Login(BlogHandler):
    def get(self):
        self.render('login-form.html')

    def post(self):
        username = self.request.get('username')
        password = self.request.get('password')

        u = User.login(username, password)
        if u:
            self.login(u)
            self.redirect('/blog')
        else:
            msg = 'Invalid login'
            self.render('login-form.html', error = msg)

class Logout(BlogHandler):
    def get(self):
        self.logout()
        self.redirect('/blog')

class Welcome(BlogHandler):
    def get(self):
        username = self.request.GET['username']
        self.render('welcome.html', username = username)

class DeletePost(BlogHandler):
    def get(self, post_id):
        #Get post by post_id
        key = db.Key.from_path('Post', int(post_id), parent=blog_key())
        post = db.get(key)
        
        #Get post.owner
        owner = post.owner

        #Get logged in user
        uid = self.read_secure_cookie('user_id')
        if not uid:
            self.render("/signup-form.html")
            return
        user = User.by_id(int(uid))
        username = user.name


        if owner != username:
            self.render("error.html", error="you cannot perform this action")
            return

        if not post:
            self.error(404)
            return

        #Check if owner == currently logged in user
        owner = post.owner

        #Delete

        #Profit
        self.render('delete-post.html', content="Are you sure you want to delete your post?", post_id = post_id)

    def post(self, post_id):
        key = db.Key.from_path('Post', int(post_id), parent=blog_key())
        post = db.get(key)
        post.delete();

        self.render('delete-post.html', content="Your post has been deleted", post_id = post_id)

class PauseTime(BlogHandler):
    def get(self):
        self.redirect('/')

class EditPost(BlogHandler):
    def get(self, post_id):
        #Get post by post_id
        key = db.Key.from_path('Post', int(post_id), parent=blog_key())
        post = db.get(key)

        #Get post.owner
        owner = post.owner

        #Get logged in user
        uid = self.read_secure_cookie('user_id')
        if not uid:
            self.render("/signup-form.html")
            return
        user = User.by_id(int(uid))
        username = user.name


        if owner != username:
            self.render("error.html", error="you cannot edit this post")
            return

        if not post:
            self.error(404)
            return
        self.render('edit-post.html', subject=post.subject, content = post.content, error="")

    def post(self, post_id):
        key = db.Key.from_path('Post', int(post_id), parent=blog_key())
        post = db.get(key)
        
        post.subject = self.request.get('subject')
        post.content = self.request.get('content')
        post.put()

        self.redirect("/blog/" + post_id)

class UpvotePost(BlogHandler):
    def get(self, post_id):
        key = db.Key.from_path('Post', int(post_id), parent=blog_key())
        post = db.get(key)

        #Get post.owner
        owner = post.owner

        #Get post.upvotes
        upvotes = str(post.user_upvotes)
        downvotes = str(post.user_downvotes)

        #Get logged in user
        uid = self.read_secure_cookie('user_id')
        if not uid:
            self.render("/signup-form.html")
            return
        user = User.by_id(int(uid))
        username = user.name

        #Check user against owner
        # if False:
        if owner == username:
            self.render("error.html", error="you cannot upvote yourself")
            return
        #Check user against post.upvotes
        elif username in upvotes:
            True
        else:
            #Check user against post.upvotes
            if username in downvotes:
                downvotes = downvotes.replace("|%s" % username, "")

            #Add user to post.upvotes
            upvotes = "|" + username
            post.user_upvotes += upvotes
            post.user_downvotes = downvotes
            post.subject = "Changed man"
            post.put()
        # self.render('welcome.html', content = (upvotes, post.user_upvotes))
        self.redirect("/blog/" + post_id)

class DownvotePost(BlogHandler):
    def get(self, post_id):
        key = db.Key.from_path('Post', int(post_id), parent=blog_key())
        post = db.get(key)

        #Get post.owner
        owner = post.owner

        #Get post.upvotes
        upvotes = str(post.user_upvotes)
        downvotes = str(post.user_downvotes)

        #Get logged in user
        uid = self.read_secure_cookie('user_id')
        if not uid:
            self.render("/signup-form.html")
            return
        user = User.by_id(int(uid))
        username = user.name

        #Check user against owner
        # if False:
        if owner == username:
            self.render("error.html", error="you cannot downvote yourself")
            return
        #Check user against post.upvotes
        elif username in downvotes:
            False
        else:
            #Check user against post.upvotes
            if username in upvotes:
                upvotes = upvotes.replace("|%s" % username, "")

            #Add user to post.upvotes
            downvotes = "|" + username
            post.user_downvotes += downvotes
            post.user_upvotes = upvotes
            post.subject = "Changed man"
            post.put()
        # self.render('welcome.html', content = (upvotes, post.user_upvotes))
        self.redirect("/blog/" + post_id)

class NewComment(BlogHandler):
    def post(self, post_id):
        key = db.Key.from_path('Post', int(post_id), parent=blog_key())
        post = db.get(key)

        uid = self.read_secure_cookie('user_id')
        if not uid:
            self.render("/signup-form.html")
            return
        user = User.by_id(int(uid))

        anonymous = self.request.get('anonymous')
        username = user.name
        if anonymous:
            username = anonymous

        content = self.request.get('content')

        comment = Comment(parent = comment_key(), owner = username, content = content, post = post)
        comment.put()
        self.render("newcomment-redirect.html", content = "Thank you for your comment!")

class EditComment(BlogHandler):
    def get(self, post_id, comment_id):

        #Get post.owner
        comment = Comment.by_id(int(comment_id))
        owner = comment.owner

        #Get logged in user
        uid = self.read_secure_cookie('user_id')
        if not uid:
            self.render("/signup-form.html")
            return
        user = User.by_id(int(uid))
        username = user.name

        if owner != username:
            self.render("error.html", error="you cannot edit this comment")
            return

        if not comment:
            self.error(404)
            return

        self.render('edit-post.html', content = comment.content, error="", comment=True)

    def post(self, post_id, comment_id):
        comment = Comment.by_id(int(comment_id))
        content = self.request.get('content')
        comment.content = content
        comment.put()
        # self.render('delete-post.html', content="Your comment has been edited", post_id = post_id)
        self.render("newcomment-redirect.html", content="Your comment has been edited.", post_id = post_id)
        # self.redirect("/blog/" + post_id)

class DeleteComment(BlogHandler):
    def get(self, post_id, comment_id):

        #Get post.owner
        comment = Comment.by_id(int(comment_id))
        owner = comment.owner

        #Get logged in user
        uid = self.read_secure_cookie('user_id')
        if not uid:
            self.render("/signup-form.html")
            return
        user = User.by_id(int(uid))
        username = user.name

        if owner != username:
            self.render("error.html", error="you cannot delete this commentif owner")
            return

        if not comment:
            self.error(404)
            return
        comment.delete();
        # self.render('delete-post.html', content="Your comment has been deleted", post_id = post_id)
        self.render("newcomment-redirect.html", content="Your comment has been deleted.", post_id = post_id)
        # self.redirect("/blog/" + post_id)

app = webapp2.WSGIApplication([('/', BlogFront),
                               ('/welcome', Welcome),
                               ('/blog/?', BlogFront),
                               ('/blog/([0-9]+)', PostPage),
                               ('/blog/([0-9]+)/comment/new', NewComment),
                               ('/blog/([0-9]+)/comment/edit/([0-9]+)', EditComment),
                               ('/blog/([0-9]+)/comment/delete/([0-9]+)', DeleteComment),
                               ('/blog/newpost', NewPost),
                               ('/blog/edit/([0-9]+)', EditPost),
                               ('/blog/delete/([0-9]+)', DeletePost),
                               ('/blog/upvote/([0-9]+)', UpvotePost),
                               ('/blog/downvote/([0-9]+)', DownvotePost),
                               ('/signup', Register),
                               ('/login', Login),
                               ('/logout', Logout),
                               ('/welcome', DeletePost),
                               ('/blog/delete/redirect', PauseTime),
                               ],
                              debug=True)
