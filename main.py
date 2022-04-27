from bot import run_bot
from balancePoller import recreate_tasks
from instances import *

loop.run_until_complete(recreate_tasks())
run_bot()
