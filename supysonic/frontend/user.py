# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2013-2023 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

import logging

from flask import flash, redirect, render_template, request, session, url_for
from flask import current_app
from functools import wraps

from ..db import ClientPrefs, User
from ..lastfm import LastFm
from ..listenbrainz import ListenBrainz
from ..managers.user import UserManager

from . import admin_only, frontend

logger = logging.getLogger(__name__)


def me_or_uuid(f, arg="uid"):
    @wraps(f)
    def decorated_func(*args, **kwargs):
        if kwargs:
            uid = kwargs[arg]
        else:
            uid = args[0]

        if uid == "me":
            user = request.user
        elif not request.user.admin:
            return redirect(url_for("frontend.index"))
        else:
            try:
                user = UserManager.get(uid)
            except ValueError as e:
                flash(str(e), "error")
                return redirect(url_for("frontend.index"))
            except User.DoesNotExist:
                flash("No such user", "error")
                return redirect(url_for("frontend.index"))

        if kwargs:
            kwargs["user"] = user
        else:
            args = (uid, user)

        return f(*args, **kwargs)

    return decorated_func


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

        if "delete" in opts and opts["delete"] in [
            "on",
            "true",
            "checked",
            "selected",
            "1",
        ]:
            prefs.delete_instance()
            continue

        prefs.format = opts["format"] if "format" in opts and opts["format"] else None
        prefs.bitrate = (
            int(opts["bitrate"]) if "bitrate" in opts and opts["bitrate"] else None
        )
        prefs.save()

    flash("Clients preferences updated.")
    return user_profile(uid, user)


@frontend.route("/user/<uid>/changeusername")
@admin_only
def change_username_form(uid):
    try:
        user = UserManager.get(uid)
    except ValueError as e:
        flash(str(e), "error")
        return redirect(url_for("frontend.index"))
    except User.DoesNotExist:
        flash("No such user", "error")
        return redirect(url_for("frontend.index"))

    return render_template("change_username.html", user=user)


@frontend.route("/user/<uid>/changeusername", methods=["POST"])
@admin_only
def change_username_post(uid):
    try:
        user = UserManager.get(uid)
    except ValueError as e:
        flash(str(e), "error")
        return redirect(url_for("frontend.index"))
    except User.DoesNotExist:
        flash("No such user", "error")
        return redirect(url_for("frontend.index"))

    username = request.form.get("user")
    if username in ("", None):
        flash("The username is required")
        return render_template("change_username.html", user=user)
    if user.name != username:
        try:
            User.get(name=username)
            flash("This name is already taken")
            return render_template("change_username.html", user=user)
        except User.DoesNotExist:
            pass

    if request.form.get("admin") is None:
        admin = False
    else:
        admin = True

    if user.name != username or user.admin != admin:
        user.name = username
        user.admin = admin
        user.save()
        flash(f"User '{username}' updated.")
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
    mail = request.form.get("mail", "")
    # No validation, lol.
    user.mail = mail
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
            flash("The current password is required")
            error = True

    new, confirm = map(request.form.get, ("new", "confirm"))

    if not new:
        flash("The new password is required")
        error = True
    if new != confirm:
        flash("The new password and its confirmation don't match")
        error = True

    if not error:
        try:
            if user.id == request.user.id:
                UserManager.change_password(user.id, current, new)
            else:
                UserManager.change_password2(user.name, new)

            flash("Password changed")
            return redirect(url_for("frontend.user_profile", uid=uid))
        except ValueError as e:
            flash(str(e), "error")

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
        flash("The name is required.")
        error = True
    if not passwd:
        flash("Please provide a password.")
        error = True
    elif passwd != passwd_confirm:
        flash("The passwords don't match.")
        error = True

    if not error:
        try:
            UserManager.add(name, passwd, **args)
            flash(f"User '{name}' successfully added")
            return redirect(url_for("frontend.user_index"))
        except ValueError as e:
            flash(str(e), "error")

    return add_user_form()


@frontend.route("/user/del/<uid>")
@admin_only
def del_user(uid):
    try:
        UserManager.delete(uid)
        flash("Deleted user")
    except ValueError as e:
        flash(str(e), "error")
    except User.DoesNotExist:
        flash("No such user", "error")

    return redirect(url_for("frontend.user_index"))


@frontend.route("/user/<uid>/lastfm/link")
@me_or_uuid
def lastfm_reg(uid, user):
    token = request.args.get("token")
    if not token:
        flash("Missing LastFM auth token")
        return redirect(url_for("frontend.user_profile", uid=uid))

    lfm = LastFm(current_app.config["LASTFM"], user)
    status, error = lfm.link_account(token)
    flash(error if not status else "Successfully linked LastFM account")

    return redirect(url_for("frontend.user_profile", uid=uid))


@frontend.route("/user/<uid>/lastfm/unlink")
@me_or_uuid
def lastfm_unreg(uid, user):
    lfm = LastFm(current_app.config["LASTFM"], user)
    lfm.unlink_account()
    flash("Unlinked LastFM account")
    return redirect(url_for("frontend.user_profile", uid=uid))


@frontend.route("/user/<uid>/listenbrainz/link")
@me_or_uuid
def listenbrainz_reg(uid, user):
    token = request.args.get("token")
    if not token:
        flash("Missing ListenBrainz auth token")
        return redirect(url_for("frontend.user_profile", uid=uid))

    lbz = ListenBrainz(current_app.config["LISTENBRAINZ"], user)
    status, error = lbz.link_account(token)
    flash(error if not status else "Successfully linked ListenBrainz account")

    return redirect(url_for("frontend.user_profile", uid=uid))


@frontend.route("/user/<uid>/listenbrainz/unlink")
@me_or_uuid
def listenbrainz_unreg(uid, user):
    lbz = ListenBrainz(current_app.config["LISTENBRAINZ"], user)
    lbz.unlink_account()
    flash("Unlinked ListenBrainz account")
    return redirect(url_for("frontend.user_profile", uid=uid))


@frontend.route("/user/login", methods=["GET", "POST"])
def login():
    return_url = request.args.get("returnUrl") or url_for("frontend.index")
    if request.user:
        flash("Already logged in")
        return redirect(return_url)

    if request.method == "GET":
        return render_template("login.html")

    name, password = map(request.form.get, ("user", "password"))
    error = False
    if not name:
        flash("Missing user name")
        error = True
    if not password:
        flash("Missing password")
        error = True

    if not error:
        user = UserManager.try_auth(name, password)
        if user:
            logger.info("Logged user %s (IP: %s)", name, request.remote_addr)
            session["userid"] = str(user.id)
            flash("Logged in!")
            return redirect(return_url)
        else:
            logger.error(
                "Failed login attempt for user %s (IP: %s)", name, request.remote_addr
            )
            flash("Wrong username or password")

    return render_template("login.html")


@frontend.route("/user/logout")
def logout():
    session.clear()
    flash("Logged out!")
    return redirect(url_for("frontend.login"))
