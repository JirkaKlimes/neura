from .google_scraper import Scrapper
from .location import Location

import json
import openai
from datetime import datetime
from typing import Optional
import logging
from colorama import Fore, Style
import toml
import tiktoken
import time


class Assistant:
    def __init__(
        self, openai_api_key: str, location: Location,
        name: str = "Neura", max_tokens: int = 512, 
        temperature: float = 0.7, model: str = "gpt-3.5-turbo-0301",
        max_model_tokens: int = 3500
        ):
        
        openai.api_key = openai_api_key
        self.name = name
        self.__location = location
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.model = model
        self.max_model_tokens = max_model_tokens
        
        self.__init_attrs()
    
    def __init_attrs(self):
        self.__load_assests()
        self.__load_user_data()
        self.__scraper = Scrapper()
        
        self.used_tokens = 0
    
    def __load_assests(self):
        with open('./assets/system_msg.md', 'r', encoding='utf-8') as f:
            self.__system_msg_template = f.read()
        
        with open('./assets/message_footer.md', 'r', encoding='utf-8') as f:
            self.__message_footer = f.read()
            
        with open('./assets/shorten_msg.md', 'r', encoding='utf-8') as f:
            self.__shorten_msg = f.read()
        
        with open('./assets/conversation_primer.json', 'r', encoding='utf-8') as f:
            self.__conversation_primer = json.load(f)
 
    def __load_user_data(self):
        with open('./data/conversation.json', 'r', encoding='utf-8') as f:
            self.__conversation = json.load(f)
        
        self.__config = toml.load("./data/config.toml")
    
    def __save_conversation(self):
        with open('./data/conversation.json', 'w', encoding='utf-8') as f:
            json.dump(self.__conversation, f, sort_keys=False, indent=4)
    
    def __generate_system_msg(self) -> dict:
        self.__location.update()
        msg = self.__system_msg_template

        date_and_time = str(datetime.now())

        msg = msg.replace('__ASSISTANT_NAME__', self.name) \
                 .replace('__DATETIME__', date_and_time) \
                 .replace('__LOCATION__', self.__location.address) \
        
        for key, val in self.__config['user'].items():
            msg += f"\n{key}: {val}"
        
        return {
            "role": "system",
            "content": msg
            }

    @property
    def logit_bias(self):
        # ids for "I'm sorry, as an AI language model, I do not have access to real-time"
        ids = [40, 1101, 7926, 11, 355, 281, 9552, 3303, 2746, 11, 314, 466, 407, 423, 1895, 284, 1103, 12, 2435]
        
        # ids for "As of my knowledge cutoff date of"
        ids += [1722, 286, 616, 3725, 45616, 3128, 286]
        
        # ids for "According according"
        ids += [4821, 38169]
        
        logit_bias = {id: -10 for id in ids}
        
        # bias for "query"
        logit_bias.update({22766: 20})

        return logit_bias

    def __get_completion(self, conversation: list[str]) -> tuple[int, str] | None:
        system_msg = self.__generate_system_msg()
        
        messages = conversation.copy()
        messages = self.__conversation_primer.copy() + messages
        messages.insert(0, system_msg)
        self.__shorten_messages(messages)

        logging.debug("MESSAGES")
        logging.debug(json.dumps(messages, indent=2))

        print(f"{Fore.BLUE}Thinking...{Style.RESET_ALL}".ljust(100, " "), end='\r')
        logging.debug("GENERATING COMPLETION")
        completion = openai.ChatCompletion.create(
            model= self.model, 
            messages = messages,
            logit_bias = self.logit_bias,
            temperature = self.temperature,
            max_tokens = self.max_tokens,
        )
        logging.debug("COMPLETION GENERATED")
        print(f"".ljust(100, " "), end='\r')
        
        
        return completion
    
    def num_tokens_from_string(self, string: str) -> int:
        encoding = tiktoken.get_encoding('cl100k_base')
        num_tokens = len(encoding.encode(string))
        return num_tokens
    
    def __num_conversation_tokens(self, conversation: list) -> int:
        return sum(
            map(
                lambda m: self.num_tokens_from_string(m['content']),
                conversation
                )
            )
    
    def __shorten_messages(self, messages: list, max_tokens: Optional[int] = None):
        max_tokens = self.max_model_tokens - self.max_tokens
            
        while self.__num_conversation_tokens(messages) > max_tokens:
            messages.pop(0)
    
    def __query_from_msg(self, completion: str) -> str | None:
        lines = completion.split("\n")
        for line in lines:
            words = line.split(' ')
            if 'query' in words[0].lower():
                return ' '.join(words[1:])

        return
    
    def __add_online_data(self, q: str, conversation: list[dict]):
        print(f"{Fore.RED}Querying:{Style.RESET_ALL} {q}".ljust(100, " "), end='\r')
        online_data = self.__scraper.get(
            q,
            params={'gl': self.__location.country_code,
                    'hl': 'en'}
            )

        logging.debug("ONLINE DATA")
        logging.debug(online_data)
            
        conversation.append({
            "role": "user",
            "content": str(online_data)
        })
    
    def __extend_conversation(self, conversation: list[dict], used_tokens: int = 0) -> int:
        completion = self.__get_completion(conversation)
        response = completion['choices'][0]

        match response['finish_reason']:

            case 'stop':
                logging.debug("FINISH REASON: stop")
                msg = response['message']['content']
                query = self.__query_from_msg(msg)
                conversation.append({
                        "role": "assistant",
                        "content": msg
                    })
                if query is None:
                    logging.debug("No Query")    
                    return used_tokens + completion['usage']['completion_tokens']
                logging.debug("Yes Query")
                self.__add_online_data(query, conversation)
                return self.__extend_conversation(conversation, used_tokens + completion['usage']['completion_tokens'])

            case 'length':
                logging.debug("FINISH REASON: lenght")
                new_msg = {
                    "role": "user",
                    "content": self.__shorten_msg
                }
                conversation.append(new_msg)
                return self.__extend_conversation(conversation, used_tokens)
       
        raise Exception(f"Unhadled finish reason: {response['finish_reason']}")
    
    def send_msg(self, msg: str) -> str:
        conversation = self.__conversation.copy()
        new_msg = {
            "role": "user",
            "content": msg
        }
        conversation.append(new_msg)
        tokens = self.__extend_conversation(conversation)
        logging.debug(f"USED_TOKENS: {tokens}")
        
        self.__conversation = conversation
    
        return conversation[-1]['content'], tokens
    
    def main_loop(self):
        while True:
            inp = input(f"{Fore.GREEN}You:{Style.RESET_ALL} ")
            print()
            if inp == 'exit':
                break
            
            if inp == 'tokens':
                print(f"{Fore.MAGENTA}System: {Style.RESET_ALL}{Fore.YELLOW}({self.used_tokens}T){Style.RESET_ALL} ≈ {self.used_tokens/1000*0.002:.2f} $\n")
                continue
            
            response, tokens = self.send_msg(inp)
            self.used_tokens += tokens

            print(f"{Fore.BLUE}{self.name} {Fore.YELLOW}({tokens}T){Style.RESET_ALL}{Fore.BLUE}:{Style.RESET_ALL} ", end='')
            for char in response:
                print(char, end='', flush=True)
                time.sleep(0.005)
            print("\n")


    