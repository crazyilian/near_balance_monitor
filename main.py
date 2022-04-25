import asyncio
from bot import run_bot
from balancePoller import run_balance
from instances import *

loop.create_task(run_balance())
run_bot()
