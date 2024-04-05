from io import BytesIO
from scipy.io import wavfile
from openai import OpenAI
import base64
from dotenv import load_dotenv
import os
from pymongo import MongoClient
from datetime import datetime
import logging
import random
import openai
# Basic startup
load_dotenv()

# Setup MongoDB
client = MongoClient(os.getenv("MONGO_URI"))
db = client.fortune_teller
# Setup OpenAI
openai_client = OpenAI()

DEFAULT_PRE_PROMPT = "You are a fortune teller. Please respond with an insightful unique fortune. Respond with only english under 50 words."

GENRES = [
    "Predict their career success and the path that will lead them there.",
    "Share a fortune about their future love life and potential soulmate.",
    "Tell them what challenges they will face in the coming year and how to overcome them.",
    "Predict their financial stability and possibility of wealth in the future.",
    "Give them insights about their family relationships and potential changes.",
    "Tell a fortune about their health and possible improvements or concerns.",
    "Share a fortune about their upcoming travels and adventures.",
    "Predict their personal growth and potential milestones in the next decade.",
    "Tell them what impact their choices and decisions will have on their life.",
    "Share a fortune about their spiritual journey and inner peace.",
    "Tell me a forecast about the weather.",
    "Tell me a fortune about the future of the world.",
]

def create_fortune_text(query, pre_prompt,tags=[]):
    prompt_genre = random.choice(GENRES)
    input_prompt=[
        {"role": "system", "content": pre_prompt},
        {"role": "system", "content": prompt_genre},
        {"role": "user", "content": query}
    ]
    response = openai.chat.completions.create(
        model="gpt-4-0125-preview",
        messages=input_prompt,
        temperature=1.0,
    )
    text = response.choices[0].message.content
    return text

VOICES = ['alloy', 'echo', 'fable', 'onyx', 'nova', 'shimmer']
def create_fortune(query,pre_prompt,tags=[],voice=None,name=""):
    prompt_genre = random.choice(GENRES)    
    text = create_fortune_text(query,pre_prompt,tags)
    if voice is None:
        voice = random.choice(VOICES)
    response = openai_client.audio.speech.create(
        model="tts-1",
        voice=voice,
        input=text,
        response_format='wav'
    )
    wav_bytes = response.read()
    audio_string = base64.b64encode(wav_bytes).decode('UTF-8')
    fortune = {
        "prompt_character": pre_prompt,
        "prompt_genre": prompt_genre,
        "prompt_query": query,
        "fortune": text,
        "time_created": datetime.now(),
        "last_viewed": datetime.now(),
        "views": 0,
        "response": None,
        "voice": voice,
        "audio_string": audio_string,
        "tags": tags,
        "name": name,
    }
    result = db.fortunes.insert_one(fortune)
    return text,audio_string

