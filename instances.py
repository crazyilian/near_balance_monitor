import dataBase
import accountQueue
import logging
import os
import aiogram
import asyncio
import datetime


logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

BOT_TOKEN = os.environ['BOT_TOKEN']
bot = aiogram.Bot(BOT_TOKEN)
botdp = aiogram.Dispatcher(bot, loop=loop)
db = dataBase.DataBase('db.json')
Q = accountQueue.AccountQueue(db)

REQUESTS_COUNTER = 0
START_DATE = datetime.datetime.now()
