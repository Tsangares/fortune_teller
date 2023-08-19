# Description: This file is the main server file for the application.
import flask 
from flask import Flask, render_template, request, redirect, url_for, jsonify
from datetime import datetime
from flask_pymongo import PyMongo
from dotenv import load_dotenv
from TTS.api import TTS
from io import BytesIO
from scipy.io import wavfile
import numpy as np
import base64
import random
import openai
import os
import logging


# Basic startup
load_dotenv()
app = Flask(__name__)

# Setup OpenAI
openai.api_key = os.getenv("OPENAI_API_KEY")

# Setup MongoDB
app.config["MONGO_URI"] = os.getenv("MONGO_URI")
mongo = PyMongo(app)

# Setup TTS
SAMPLE_RATE = 16_000
model_name="tts_models/en/ljspeech/tacotron2-DCA"
tts = TTS(model_name)


fortunes = [
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
]

def text_to_base64wav(text):
    if tts.speakers is None and tts.languages is None:
        wav = tts.tts(text)
    else:
        wav = tts.tts(text, speaker=tts.speakers[0], language=tts.languages[0])
    wav = np.array(wav)
    sample_rate = tts.synthesizer.output_sample_rate
    wav_norm = wav * (32767 / max(0.01, np.max(np.abs(wav))))
    bytes_wav = bytes()
    byte_io = BytesIO(bytes_wav)
    wavfile.write(byte_io, sample_rate, wav_norm.astype(np.int16))
    wav_bytes = byte_io.read()
    audio_data = base64.b64encode(wav_bytes).decode('UTF-8')
    return audio_data

def get_fortune(query="Tell me a fortune.",random_fortune=False):
    fortune = {
        "prompt_character": "You are a fortune teller. Please respond with an insightful unique fortune. Respond with only english under 50 words.",
    }
    input_prompt=[
        {"role": "system", "content": fortune["prompt_character"]},
    ]
    if random_fortune:
        prompt_genre = random.choice(fortunes)
        input_prompt.append({"role": "system", "content": prompt_genre})
        fortune["prompt_genre"] = prompt_genre
    
    input_prompt.append({"role": "user", "content": query})
    fortune["prompt_query"] = query

    response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=input_prompt,
                temperature=1.0,
                )
    text = response['choices'][0]['message']['content']
    fortune["fortune"] = text
    fortune["response"] = response
    fortune["time_created"] = datetime.now()

    # Convert to audio
    audio_string = text_to_base64wav(text)
    fortune["audio_string"] = audio_string

    # Logging to mongodb
    mongo.db.fortunes.insert_one(fortune)

    return audio_string

@app.route('/generate/')
def generate_new_fortune():
    string = request.args.get('text','Tell me a fortune.')
    try:
        get_fortune(string,random_fortune=True)
    except Exception as e:
        logging.error(e)
        return {'success': False, 'exception': str(e), 'exception_type': type(e).__name__}
    return {'success': True}

def get_last_cached_fortune():
    fortune = mongo.db.fortunes.find_one({},sort=[('time_created',-1)])
    return fortune


@app.route('/speak/')
def speak():
    string = request.args.get('text','This is a test.')
    audio_data = text_to_base64wav(string)
    return f'<audio controls src="data:audio/wav;base64, {audio_data}"></audio>'

@app.route('/ask/')
def ask_fortune():
    string = request.args.get('text','Tell me a fortune')
    audio_data = get_fortune(string,random_fortune=False)
    return f'<audio controls src="data:audio/wav;base64, {audio_data}"></audio>'

@app.route('/')
def index():
    fortune = get_last_cached_fortune()
    entropy = random.random()
    return render_template('/pages/fortune.html',entropy=entropy,**fortune)


if __name__ == '__main__':
    app.run(host="127.0.0.1",port="8666",debug=False)
