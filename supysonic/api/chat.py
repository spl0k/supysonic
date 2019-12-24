# coding: utf-8
#
# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2013-2018 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

from flask import request

from ..db import ChatMessage, User
from . import api


@api.route("/getChatMessages.view", methods=["GET", "POST"])
def get_chat():
    since = request.values.get("since")
    since = int(since) / 1000 if since else None

    query = ChatMessage.select().order_by(ChatMessage.time)
    if since:
        query = query.filter(lambda m: m.time > since)

    return request.formatter(
        "chatMessages", dict(chatMessage=[msg.responsize() for msg in query])
    )


@api.route("/addChatMessage.view", methods=["GET", "POST"])
def add_chat_message():
    msg = request.values["message"]
    ChatMessage(user=request.user, message=msg)

    return request.formatter.empty
