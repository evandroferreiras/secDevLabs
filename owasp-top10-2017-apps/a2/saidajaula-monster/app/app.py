#!/usr/bin/env python
# -*- coding: utf-8 -*-
from flask import Flask, request, make_response, render_template, redirect, Markup
from model.password import Password
from model.db import DataBase
import base64
import os
import json
import hashlib, binascii
import time
import uuid
from functools import wraps
import uuid


app = Flask(__name__)
database = DataBase(os.environ.get('A2_DATABASE_HOST'), os.environ.get('A2_DATABASE_USER'),
			os.environ.get('A2_DATABASE_PASSWORD'), os.environ.get('A2_DATABASE_NAME'))


def get_cookie():
    cookie = request.cookies.get("sessionId", "")
    cookie = base64.b64decode(cookie).decode("utf-8")
    cookie_separado = cookie.split('.')
    if(len(cookie_separado) != 2):
        return None, "Invalid cookie!"
    hash_cookie = hashlib.sha256(cookie_separado[0].encode('utf-8')).hexdigest()
    if (hash_cookie != cookie_separado[1]):
        return None, "different_cookie"
    return cookie_separado[0], None


def prepare_cookie(value):
    cookie_dic = value
    cookie = json.dumps(cookie_dic)
    hash_cookie = hashlib.sha256(cookie.encode('utf-8')).hexdigest()
    cookie_done = '.'.join([cookie, hash_cookie])
    return base64.b64encode(str(cookie_done).encode("utf-8"))


def login_admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        cookie_json, error = get_cookie()
        if error == 'different_cookie':
            return redirect("/login")
        j = json.loads(cookie_json)
        if j.get("permissao") != 1:
            return "You don't have permission to access this route. You are not an admin. \n"
        return f(*args, **kwargs)
    return decorated_function

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        cookie_json, error = get_cookie()
        if error == 'different_cookie':        
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function

@app.route("/", methods=['GET'])
def home():
    return render_template('index.html')

@app.route("/register", methods=['GET', 'POST'])
def register():
    if request.method == 'GET':
        return render_template('register.html')

    if request.method == 'POST':
        form_username = request.form.get('username', "")
        form_password = request.form.get('password', "")
        form_password2 = request.form.get('password2', "")

        if form_username == "" or form_password == "":
            return "Error! You have to pass username and password! \n"
        elif form_password != form_password2:
            return "Error! Passwords must be the same! \n"

        guid = str(uuid.uuid4())
        password = Password(form_password, form_username, guid)
        hashed_password = password.get_hashed_password()
        message, success = database.insert_user(guid, form_username, hashed_password)
        if success:
            return render_template('login.html')
        return "Error: account creation failed \n"


@app.route("/login", methods=['GET','POST'])
def login():
    if request.method == 'GET':
        return render_template('login.html')

    if request.method == 'POST':
        form_username = request.form.get('username', "")
        form_password = request.form.get('password', "")
        if form_username == "" or form_password == "":
            return "Error! You have to pass username and password! \n"

        result, success = database.get_user(form_username)
        if not success:
            return "Login failed! \n"

        if result == None:
            return "Login failed! \n"

        password = Password(form_password, form_username, result[2])
        if not password.validate_password(result[0]):
            return "Login failed! \n"

        cookie_dic = {"permissao": result[1], "username": form_username}
        cookie_done = prepare_cookie(cookie_dic)

        resp = make_response()
        resp.set_cookie("sessionId", cookie_done)
        return resp

@app.route("/admin", methods=['GET'])
@login_admin_required
def admin():
    return "You are an admin! \n"

@app.route("/user", methods=['GET'])
@login_required
def userInfo():
    return "You are an user! \n"

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=10082)
