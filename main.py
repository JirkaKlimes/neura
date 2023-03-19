from src.assistant import Assistant
from src.location import IPLocation

import logging

with open('./api_token', 'r') as f:
    openai_api_key = f.read()
    
# logging.basicConfig(filename='example.log', encoding='utf-8', level=logging.DEBUG)

assistant = Assistant(openai_api_key, location=IPLocation())
assistant.main_loop()
