"""Provides all routes for the Social Insecurity application.

This file contains the routes for the application. It is imported by the app package.
It also contains the SQL queries used for communicating with the database.
"""

from pathlib import Path

from flask import flash, redirect, render_template, send_from_directory, url_for, request

from app import app, sqlite, bcrypt
from app.forms import CommentsForm, FriendsForm, IndexForm, PostForm, ProfileForm

import html


@app.route("/", methods=["GET", "POST"])
@app.route("/index", methods=["GET", "POST"])
def index():
    """Provides the index page for the application.

    It reads the composite IndexForm and based on which form was submitted,
    it either logs the user in or registers a new user.

    If no form was submitted, it simply renders the index page.
    """
    index_form = IndexForm()
    login_form = index_form.login
    register_form = index_form.register

    if request.method == "POST":  # Check if the request method is POST

        if login_form.is_submitted() and login_form.submit.data:

            if login_form.validate_on_submit():  # Check if the login form is valid

                user = sqlite.get_user(login_form.username.data)

                if user is None:
                    flash("Sorry, username or password is not valid!", category="warning")
                elif not bcrypt.check_password_hash(user["password"], html.escape(login_form.password.data)):
                    flash("Sorry, username or password is not valid!", category="warning")
                elif bcrypt.check_password_hash(user["password"], html.escape(login_form.password.data)):
                    return redirect(url_for("stream", username=login_form.username.data))
            else:
                flash("Login form data is not valid or Empty, The fields in question is:", category="warning")

        elif register_form.is_submitted() and register_form.submit.data:

            if register_form.validate_on_submit():
                hashed_password = bcrypt.generate_password_hash(register_form.password.data).decode('utf-8')
                response = sqlite.create_user(register_form.username.data, register_form.first_name.data,
                                    register_form.last_name.data, hashed_password)
                if response == 1:
                    # response = 1 when user creation is succssesfull.
                    flash("User successfully created!", category="success")
                    return redirect(url_for("index"))
                else:
                    # when somthing gose wrong with the creation of user.
                    flash("Somthing went wrong, user was not created!", category="warning")
            else:
                error_messages = []
                
                if 'first_name' in register_form.errors:
                    error_messages.append("First Name field is required.")
                if 'last_name' in register_form.errors:
                    error_messages.append("Last Name field is required.")
                if 'password' in register_form.errors:
                    error_messages.append("Password field is required.")

                if 'username' in register_form.errors:
                    username_error = "Username field is required."
                    # Check if the username doesn't meet the requirements (minimum length and character composition)
                    if len(register_form.username.data) < 4:
                        username_error = "Username must be at least 4 characters long."
                    elif not register_form.username.data.isalnum():
                        username_error = "Username must contain only letters and numbers."
                    error_messages.append(username_error)

                if 'confirm_password' in register_form.errors:
                    error_messages.append("Passwords must match")
                    
                # Flash the aggregated error message
                flash("\n".join(error_messages), category="warning")

    return render_template("index.html.j2", title="Welcome", form=index_form)


@app.route("/stream/<string:username>", methods=["GET", "POST"])
def stream(username: str):
    """Provides the stream page for the application.

    If a form was submitted, it reads the form data and inserts a new post into the database.

    Otherwise, it reads the username from the URL and displays all posts from the user and their friends.
    """
    post_form = PostForm()
   
    user = sqlite.get_user(username)

    if post_form.validate_on_submit():
        if post_form.image.data:
            path = Path(app.instance_path) / app.config["UPLOADS_FOLDER_PATH"] / post_form.image.data.filename
            post_form.image.data.save(path)

        sqlite.create_post(user["id"], post_form.content.data, post_form.image.data.filename)
        
        return redirect(url_for("stream", username=username))


    posts = sqlite.get_posts(user["id"])
    return render_template("stream.html.j2", title="Stream", username=username, form=post_form, posts=posts)


@app.route("/comments/<string:username>/<int:post_id>", methods=["GET", "POST"])
def comments(username: str, post_id: int):
    """Provides the comments page for the application.

    If a form was submitted, it reads the form data and inserts a new comment into the database.

    Otherwise, it reads the username and post id from the URL and displays all comments for the post.
    """
    comments_form = CommentsForm()
 
    user = sqlite.get_user(username)

    if comments_form.validate_on_submit():
 
        sqlite.create_comment(post_id, user["id"], comments_form.comment.data)

    post = sqlite.get_post(post_id)
    comments = sqlite.get_comments(post_id)
    return render_template(
        "comments.html.j2", title="Comments", username=username, form=comments_form, post=post, comments=comments
    )


@app.route("/friends/<string:username>", methods=["GET", "POST"])
def friends(username: str):
    """Provides the friends page for the application.

    If a form was submitted, it reads the form data and inserts a new friend into the database.

    Otherwise, it reads the username from the URL and displays all friends of the user.
    """
    friends_form = FriendsForm()

    user = sqlite.get_user(username)

    if friends_form.validate_on_submit():

        friend = sqlite.get_user(friends_form.username.data)
 
        friends = sqlite.get_friend(user["id"])

        if friend is None:
            flash("User does not exist!", category="warning")
        elif friend["id"] == user["id"]:
            flash("You cannot be friends with yourself!", category="warning")
        elif friend["id"] in [friend["f_id"] for friend in friends]:
            flash("You are already friends with this user!", category="warning")
        else:
   
            sqlite.create_friend(user["id"], friend["id"])
            flash("Friend successfully added!", category="success")

    friends = sqlite.get_friends(user["id"])
    return render_template("friends.html.j2", title="Friends", username=username, friends=friends, form=friends_form)


@app.route("/profile/<string:username>", methods=["GET", "POST"])
def profile(username: str):
    """Provides the profile page for the application.

    If a form was submitted, it reads the form data and updates the user's profile in the database.

    Otherwise, it reads the username from the URL and displays the user's profile.
    """
    profile_form = ProfileForm()

    user = sqlite.get_user(username)

    if profile_form.validate_on_submit():

        sqlite.update_profile(username, profile_form.education.data, profile_form.employment.data, 
                              profile_form.music.data, profile_form.movie.data, profile_form.nationality.data, 
                              profile_form.birthday.data)
        return redirect(url_for("profile", username=username))

    return render_template("profile.html.j2", title="Profile", username=username, user=user, form=profile_form)


@app.route("/uploads/<string:filename>")
def uploads(filename):
    """Provides an endpoint for serving uploaded files."""
    return send_from_directory(Path(app.instance_path) / app.config["UPLOADS_FOLDER_PATH"], filename)
