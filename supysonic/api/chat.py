# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2013-2026 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

from flask import request

from ..db import ChatMessage
from ._blueprint import api_routing
from ._helpers import MAX_TIMESTAMP_MS, get_int


@api_routing("/getChatMessages")
def get_chat():
    since = get_int("since", min=0, max=MAX_TIMESTAMP_MS)
    since = since / 1000 if since else None

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
