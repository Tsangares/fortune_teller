# Description: This file is the main server file for the application.
import flask 
from flask import Flask, render_template, request, redirect, url_for, jsonify
from datetime import datetime
from flask_pymongo import PyMongo
from dotenv import load_dotenv
from TTS.api import TTS
from TTS.utils.synthesizer import Synthesizer
from TTS.utils.io import load_checkpoint
from TTS.tts.models.vits import Vits
from TTS.tts.configs.shared_configs import BaseDatasetConfig, CharactersConfig
from TTS.tts.configs.vits_config import VitsConfig
from TTS.tts.datasets import load_tts_samples
from TTS.tts.models.vits import Vits, VitsArgs, VitsAudioConfig
from TTS.tts.utils.speakers import SpeakerManager
from TTS.tts.utils.text.tokenizer import TTSTokenizer
from TTS.utils.audio import AudioProcessor
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
#tts = TTS(model_name)
tts=None
#Load Trump Synthesizer
trump = Synthesizer(
        tts_config_path="./models/trump/config.json",
        tts_checkpoint="./models/trump/trump.pth",
        use_cuda=False,
    )
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

def trump_to_base64wav(text):
    wav = trump.tts(text)
    wav = np.array(wav)
    sample_rate = 22050
    wav_norm = wav * (32767 / max(0.01, np.max(np.abs(wav))))
    bytes_wav = bytes() 
    byte_io = BytesIO(bytes_wav)
    wavfile.write(byte_io, sample_rate, wav_norm.astype(np.int16))
    wav_bytes = byte_io.read()
    audio_data = base64.b64encode(wav_bytes).decode('UTF-8')
    return audio_data

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

#DEFAULT_PRE_PROMPT = "You are a fortune teller. Please respond with an insightful unique fortune. Respond with only english under 50 words."
DEFAULT_PRE_PROMPT = "You are Donald trump and you make predictions like you are giving a campaign speech. Please announce a fortune in 2 sentences."
def get_custom_fortune(pre_prompts=None,prompt="Tell me a fortune",post_prompts=[]):
    if pre_prompts is None:
        pre_prompts = [DEFAULT_PRE_PROMPT]
    input_prompt=[]
    for pre_prompt in pre_prompts:
        if pre_prompt=="": continue
        input_prompt.append({"role": "system", "content": pre_prompt})
    input_prompt.append({"role": "system", "content": prompt})
    for post_prompt in post_prompts:
        if pre_prompt=="": continue
        input_prompt.append({"role": "system", "content": post_prompt})
    # Get response using chatgpt3.5
    response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=input_prompt,
                temperature=1.0,
                )
    text = response['choices'][0]['message']['content']
    return text


def get_fortune(query="Tell me a fortune.",random_fortune=False):
    fortune = {
        "prompt_character": DEFAULT_PRE_PROMPT,
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
    audio_string = trump_to_base64wav(text)
    fortune['trump'] = True
    fortune["audio_string"] = audio_string

    # Logging to mongodb
    result = mongo.db.fortunes.insert_one(fortune)
    if result.acknowledged:
        logging.warning("Successfully logged fortune.")
    else: 
        logging.error("Failed to log fortune.")
    return audio_string

@app.route('/generate/')
def generate_new_fortune():
    string = request.args.get('text','Tell me a fortune.')
    try:
        get_fortune(string,random_fortune=True)
    except NameError as e:
        logging.error(f"Error Generating new fortune. {e} {type(e).__name__}")
        #raise e
        return {'success': False, 'exception': str(e), 'exception_type': type(e).__name__}
    except Exception as e:
        logging.error(f"Error Generating new fortune. {e} {type(e).__name__}")
        return {'success': False, 'exception': str(e), 'exception_type': type(e).__name__}
    return {'success': True}

def get_last_cached_fortune():
    fortune = mongo.db.fortunes.find_one({"trump": True},sort=[('time_created',-1)])
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

@app.route('/calibrate/', methods=['GET'])
def calibrate_fortune_teller():
    return render_template('/pages/calibrate.html',default_pre_prompt=DEFAULT_PRE_PROMPT)

@app.route('/calibrate/', methods=['POST'])
def calibrate_fortune_teller_custom():
    pre_prompt = request.form.get('pre_prompt',DEFAULT_PRE_PROMPT)
    extra_prompt = request.form.get('extra_prompt',"")
    prompt = request.form.get('prompt',"Tell me a fortune")
    fortune = get_custom_fortune([pre_prompt,extra_prompt],prompt)
    return render_template('/pages/calibrate.html',fortune=fortune,pre_prompt=pre_prompt,extra_prompt=extra_prompt,prompt=prompt)

@app.route('/calibrate/save', methods=['POST'])
def save_calibration():
    response = mongo.db.prompts.insert_one(dict(request.form))
    return "<h3>Prompt Saved! Go to archive to see all saved prompts.</h3>"

@app.route('/calibrate/all', methods=['GET'])
def calibration_see_all():
    cursor = mongo.db.prompts.find({})
    prompts = [p for p in cursor]
    return render_template("/pages/calibrate_all.html",prompts=prompts)

@app.route('/')
def index():
    fortune = get_last_cached_fortune()
    entropy = random.random()
    return render_template('/pages/fortune.html',entropy=entropy,**fortune)


if __name__ == '__main__':
    app.run(host="127.0.0.1",port="8666",debug=True)
