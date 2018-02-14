# coding: utf-8

# This file is part of Supysonic.
#
# Supysonic is a Python implementation of the Subsonic server API.
# Copyright (C) 2013-2018  Alban 'spl0k' Féron
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from flask import request

from ..db import ChatMessage, User
from ..py23 import dict
from . import api

@api.route('/getChatMessages.view', methods = [ 'GET', 'POST' ])
def get_chat():
    since = request.values.get('since')
    try:
        since = int(since) / 1000 if since else None
    except ValueError:
        return request.formatter.error(0, 'Invalid parameter')

    query = ChatMessage.select().order_by(ChatMessage.time)
    if since:
        query = query.filter(lambda m: m.time > since)

    return request.formatter('chatMessages', dict(chatMessage = [ msg.responsize() for msg in query ] ))

@api.route('/addChatMessage.view', methods = [ 'GET', 'POST' ])
def add_chat_message():
    msg = request.values.get('message')
    if not msg:
        return request.formatter.error(10, 'Missing message')

    ChatMessage(user = request.user, message = msg)

    return request.formatter.empty

