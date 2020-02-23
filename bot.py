from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
from crawler import parse
import logging, threading
from functools import partial
from selenium.common.exceptions import InvalidArgumentException
import random as rnd
import string as STR
from db import DB
import cfg

lock = threading.Lock()

updater = Updater(token=cfg.TOKEN, use_context=True)
dispatcher = updater.dispatcher
db = DB(cfg.DB_NAME)

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
					level=logging.INFO)

def start(update, context):
	context.bot.send_message(chat_id=update.effective_chat.id, text="Help info")

def msgCallback(update, context):
	global lock, db
	args = update.message.text.split()
	url = None

	for arg in args:
		if cfg.DEFAULT_ASSET_HOST in args[0] and len(args[0].split("/")) > 5:
			url = args[0]
			break

	if url:
		with lock:
			asset = db.getArt(url.split("/")[-1])

		if asset:
			return context.bot.send_photo(chat_id=update.effective_chat.id, 
					photo=open(cfg.ASSET_FOLDER+asset[1]+".jpg", "rb"))

		t1 = threading.Thread(target=partial(parseThread, url, update, context))
		t1.daemon = True
		return t1.start()

	else:
		return context.bot.send_message(chat_id=update.effective_chat.id, text="Wrong url")

def parseThread(url, update, context):
	global lock, db

	context.bot.send_message(chat_id=update.effective_chat.id, text="Processing...")
	blobs_folder = ''.join([rnd.choice(STR.ascii_letters+STR.digits) for i in range(6)])
	try:
		ret, file_name = parse(url, 12000, True, blobs_folder)
	except (InvalidArgumentException, ZeroDivisionError):
		return context.bot.send_message(chat_id=update.effective_chat.id, text="Wrong url")
	except OSError:
		return context.bot.send_message(chat_id=update.effective_chat.id, text="Sorry, cannot download this item.")


	if ret:
		context.bot.send_photo(chat_id=update.effective_chat.id, 
			photo=open(cfg.ASSET_FOLDER+file_name, "rb"))

		with lock:
			db.addArt(file_name.split(".")[0])
			
	else:
		return context.bot.send_photo(chat_id=update.effective_chat.id, text="ERROR")


start_handler = CommandHandler('start', start)
dispatcher.add_handler(start_handler)

msg_handler = MessageHandler(Filters.text, msgCallback)
dispatcher.add_handler(msg_handler)

updater.start_polling()
updater.idle()