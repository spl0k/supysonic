# coding: utf-8

from flask import request
from web import app
from db import ChatMessage, session

@app.route('/rest/getChatMessages.view', methods = [ 'GET', 'POST' ])
def get_chat():
	since = request.args.get('since')
	try:
		since = int(since) / 1000 if since else None
	except:
		return request.error_formatter(0, 'Invalid parameter')

	query = ChatMessage.query.order_by(ChatMessage.time)
	if since:
		query = query.filter(ChatMessage.time > since)

	return request.formatter({ 'chatMessages': { 'chatMessage': [ msg.responsize() for msg in query ] }})

@app.route('/rest/addChatMessage.view', methods = [ 'GET', 'POST' ])
def add_chat_message():
	msg = request.args.get('message')
	if not msg:
		return request.error_formatter(10, 'Missing message')

	session.add(ChatMessage(user = request.user, message = msg))
	session.commit()
	return request.formatter({})

