# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2013-2022 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

from flask import request

from ..db import ChatMessage
from . import api_routing


@api_routing("/getChatMessages")
def get_chat():
    since = request.values.get("since")
    since = int(since) / 1000 if since else None

    query = ChatMessage.select().order_by(ChatMessage.time)
    if since:
        query = query.where(ChatMessage.time > since)

    return request.formatter(
        "chatMessages", {"chatMessage": [msg.responsize() for msg in query]}
    )


@api_routing("/addChatMessage")
def add_chat_message():
    msg = request.values["message"]
    ChatMessage.create(user=request.user, message=msg)

    return request.formatter.empty
