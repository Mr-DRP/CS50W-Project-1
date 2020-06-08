from functools import wraps
from flask import session,redirect,request,url_for
#Defining our custom decorator login_required

def login_required(function):
    @wraps(function)
    def wrapup(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect('/login')
        return function(*args, **kwargs)
    return wrapup
