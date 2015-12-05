import contextio as c

CONSUMER_KEY = 'map3l6ci'
CONSUMER_SECRET = 'dFdFD0ykcfKhdsX9'

cio = c.ContextIO(
	consumer_key = CONSUMER_KEY,
	consumer_secret = CONSUMER_SECRET
)

accounts = cio.get_accounts()

print accounts

params = {'id': '565f46ffbf29598c0d8b4567'}
account = c.Account(cio, params)

account.get()
