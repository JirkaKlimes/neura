from src.assistant import Assistant
from src.location import IPLocation

import os
import logging

# logging.basicConfig(filename='example.log', encoding='utf-8', level=logging.DEBUG)

assistant = Assistant(os.getenv("OPENAI_API_KEY"), location=IPLocation())
assistant.main_loop()
