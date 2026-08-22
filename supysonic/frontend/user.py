# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2013-2026 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

import logging
from functools import wraps

from flask import (
    current_app,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from ..db import ClientPrefs, User
from ..lastfm import LastFm
from ..listenbrainz import ListenBrainz
from ..managers.user import UserManager
from ..parsers import parse_int, parse_mail
from . import admin_only, frontend, parse_checkbox

logger = logging.getLogger(__name__)


def _resolve_user(uid):
    """Look up the user with the given id.

    Returns a (user, response) tuple. On failure the user is None and the
    response is a redirection to the index, the error having been flashed.
    """

    try:
        return UserManager.get(uid), None
    except ValueError as e:
        flash(str(e), "danger")
    except User.DoesNotExist:
        flash("No such user", "danger")

    return None, redirect(url_for("frontend.index"))


def _resolve_me_or_uuid(uid):
    """Same as _resolve_user, but 'me' resolves to the requesting user.

    Any other id is reserved to admins.
    """

    if uid == "me":
        return request.user, None
    if not request.user.admin:
        return None, redirect(url_for("frontend.index"))

    return _resolve_user(uid)


def _user_injector(resolve, arg="uid"):
    """Build a decorator passing the user resolved from a view's uid to it."""

    def decorator(f):
        @wraps(f)
        def decorated_func(*args, **kwargs):
            if kwargs:
                uid = kwargs[arg]
            else:
                uid = args[0]

            user, error = resolve(uid)
            if error is not None:
                return error

            if kwargs:
                kwargs["user"] = user
            else:
                args = (uid, user)

            return f(*args, **kwargs)

        return decorated_func

    return decorator


me_or_uuid = _user_injector(_resolve_me_or_uuid)
uuid_user = _user_injector(_resolve_user)


@frontend.route("/user")
@admin_only
def user_index():
    return render_template("users.html", users=User.select())


@frontend.route("/user/<uid>")
@me_or_uuid
def user_profile(uid, user):
    return render_template(
        "profile.html",
        user=user,
        api_key=current_app.config["LASTFM"]["api_key"],
        clients=user.clients,
    )


@frontend.route("/user/<uid>", methods=["POST"])
@me_or_uuid
def update_clients(uid, user):
    clients_opts = {}
    for key, value in request.form.items():
        if "_" not in key:
            continue
        parts = key.split("_")
        if len(parts) != 2:
            continue
        client, opt = parts
        if not client or not opt:
            continue

        if client not in clients_opts:
            clients_opts[client] = {opt: value}
        else:
            clients_opts[client][opt] = value
    logger.debug(clients_opts)

    for client, opts in clients_opts.items():
        prefs = user.clients.where(ClientPrefs.client_name == client).first()
        if prefs is None:
            continue

        if parse_checkbox(opts, "delete"):
            prefs.delete_instance()
            continue

        try:
            bitrate = parse_int(opts.get("bitrate"), min=0)
        except ValueError:
            flash(f"Invalid bitrate for client '{client}'.", "danger")
            return user_profile(uid, user)

        prefs.format = opts["format"] if "format" in opts and opts["format"] else None
        prefs.bitrate = bitrate
        prefs.save()

    flash("Clients preferences updated.", "success")
    return user_profile(uid, user)


@frontend.route("/user/<uid>/changeusername")
@admin_only
@uuid_user
def change_username_form(uid, user):
    return render_template("change_username.html", user=user)


@frontend.route("/user/<uid>/changeusername", methods=["POST"])
@admin_only
@uuid_user
def change_username_post(uid, user):
    username = request.form.get("user")
    if username in ("", None):
        flash("The username is required", "danger")
        return render_template("change_username.html", user=user)
    if user.name != username:
        try:
            User.get(name=username)
            flash("This name is already taken", "danger")
            return render_template("change_username.html", user=user)
        except User.DoesNotExist:
            pass

    admin = parse_checkbox(request.form, "admin")

    if user.name != username or user.admin != admin:
        user.name = username
        user.admin = admin
        user.save()
        flash(f"User '{username}' updated.", "success")
    else:
        flash(f"No changes for '{username}'.")

    return redirect(url_for("frontend.user_profile", uid=uid))


@frontend.route("/user/<uid>/changemail")
@me_or_uuid
def change_mail_form(uid, user):
    return render_template("change_mail.html", user=user)


@frontend.route("/user/<uid>/changemail", methods=["POST"])
@me_or_uuid
def change_mail_post(uid, user):
    try:
        user.mail = parse_mail(request.form.get("mail"))
    except ValueError as e:
        flash(f"Invalid email address: {e}", "danger")
        return change_mail_form(uid, user)

    user.save()
    return redirect(url_for("frontend.user_profile", uid=uid))


@frontend.route("/user/<uid>/changepass")
@me_or_uuid
def change_password_form(uid, user):
    return render_template("change_pass.html", user=user)


@frontend.route("/user/<uid>/changepass", methods=["POST"])
@me_or_uuid
def change_password_post(uid, user):
    error = False
    if user.id == request.user.id:
        current = request.form.get("current")
        if not current:
            flash("The current password is required", "danger")
            error = True

    new, confirm = map(request.form.get, ("new", "confirm"))

    if not new:
        flash("The new password is required", "danger")
        error = True
    if new != confirm:
        flash("The new password and its confirmation don't match", "danger")
        error = True

    if not error:
        try:
            if user.id == request.user.id:
                UserManager.change_password(user.id, current, new)
            else:
                UserManager.change_password2(user.name, new)

            flash("Password changed", "success")
            return redirect(url_for("frontend.user_profile", uid=uid))
        except ValueError as e:
            flash(str(e), "danger")

    return change_password_form(uid, user)


@frontend.route("/user/add")
@admin_only
def add_user_form():
    return render_template("adduser.html")


@frontend.route("/user/add", methods=["POST"])
@admin_only
def add_user_post():
    error = False
    args = request.form.copy()
    (name, passwd, passwd_confirm) = map(
        args.pop, ("user", "passwd", "passwd_confirm"), (None,) * 3
    )
    if not name:
        flash("The name is required.", "danger")
        error = True
    if not passwd:
        flash("Please provide a password.", "danger")
        error = True
    elif passwd != passwd_confirm:
        flash("The passwords don't match.", "danger")
        error = True

    mail = None
    try:
        mail = parse_mail(args.pop("mail", None))
    except ValueError as e:
        flash(f"Invalid email address: {e}", "danger")
        error = True

    if not error:
        try:
            UserManager.add(name, passwd, mail=mail, **args)
            flash(f"User '{name}' successfully added", "success")
            return redirect(url_for("frontend.user_index"))
        except ValueError as e:
            flash(str(e), "danger")

    return add_user_form()


@frontend.route("/user/del/<uid>", methods=["POST"])
@admin_only
def del_user(uid):
    try:
        UserManager.delete(uid)
        flash("Deleted user", "success")
    except ValueError as e:
        flash(str(e), "danger")
    except User.DoesNotExist:
        flash("No such user", "danger")

    return redirect(url_for("frontend.user_index"))


# Intentionally GET: this is the Last.fm OAuth callback. Last.fm redirects the
# user's browser here with a "token" query param, so it must stay GET (making it
# POST-only would return 405 and break account linking).
@frontend.route("/user/<uid>/lastfm/link")
@me_or_uuid
def lastfm_reg(uid, user):
    token = request.args.get("token")
    if not token:
        flash("Missing LastFM auth token", "warning")
        return redirect(url_for("frontend.user_profile", uid=uid))

    lfm = LastFm(current_app.config["LASTFM"], user)
    status, error = lfm.link_account(token)
    if not status:
        flash(error, "danger")
    else:
        flash("Successfully linked LastFM account", "success")

    return redirect(url_for("frontend.user_profile", uid=uid))


@frontend.route("/user/<uid>/lastfm/unlink", methods=["POST"])
@me_or_uuid
def lastfm_unreg(uid, user):
    lfm = LastFm(current_app.config["LASTFM"], user)
    lfm.unlink_account()
    flash("Unlinked LastFM account", "success")
    return redirect(url_for("frontend.user_profile", uid=uid))


@frontend.route("/user/<uid>/listenbrainz/link", methods=["POST"])
@me_or_uuid
def listenbrainz_reg(uid, user):
    token = request.form.get("token")
    if not token:
        flash("Missing ListenBrainz auth token", "warning")
        return redirect(url_for("frontend.user_profile", uid=uid))

    lbz = ListenBrainz(current_app.config["LISTENBRAINZ"], user)
    status, error = lbz.link_account(token)
    if not status:
        flash(error, "danger")
    else:
        flash("Successfully linked ListenBrainz account", "success")

    return redirect(url_for("frontend.user_profile", uid=uid))


@frontend.route("/user/<uid>/listenbrainz/unlink", methods=["POST"])
@me_or_uuid
def listenbrainz_unreg(uid, user):
    lbz = ListenBrainz(current_app.config["LISTENBRAINZ"], user)
    lbz.unlink_account()
    flash("Unlinked ListenBrainz account", "success")
    return redirect(url_for("frontend.user_profile", uid=uid))


@frontend.route("/user/login", methods=["GET", "POST"])
def login():
    return_url = url_for("frontend.index")
    if request.user:
        flash("Already logged in")
        return redirect(return_url)

    if request.method == "GET":
        return render_template("login.html")

    name, password = map(request.form.get, ("user", "password"))
    error = False
    if not name:
        flash("Missing user name", "danger")
        error = True
    if not password:
        flash("Missing password", "danger")
        error = True

    if not error:
        user = UserManager.try_auth(name, password)
        if user:
            logger.info("Logged user %s (IP: %s)", name, request.remote_addr)
            session["userid"] = str(user.id)
            flash("Logged in!", "success")
            return redirect(return_url)
        else:
            logger.error(
                "Failed login attempt for user %s (IP: %s)", name, request.remote_addr
            )
            flash("Wrong username or password", "danger")

    return render_template("login.html")


@frontend.route("/user/logout")
def logout():
    session.clear()
    flash("Logged out!", "success")
    return redirect(url_for("frontend.login"))
