#run.py

import prunbot
import os
from dotenv import load_dotenv

load_dotenv()

prunbot.run(os.environ['TOKEN'])