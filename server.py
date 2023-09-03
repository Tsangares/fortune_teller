# Description: This file is the main server file for the application.
import flask 
from flask import Flask, render_template, request, redirect, url_for, jsonify
from datetime import datetime
from flask_pymongo import PyMongo
from dotenv import load_dotenv
import random
import os
import logging
from fortune import create_fortune, text_to_wav, DEFAULT_PRE_PROMPT

# Basic startup
load_dotenv()
app = Flask(__name__)

# Setup MongoDB
app.config["MONGO_URI"] = os.getenv("MONGO_URI")
mongo = PyMongo(app)


@app.route('/generate/')
def generate_new_fortune(**kwargs):
    return {'success': None}


@app.route('/generate/trump')
def generate_new_trump_fortune(**kwargs):
    return {'success': None}


@app.route('/speak/')
def speak():
    string = request.args.get('text','This is a test.')
    audio_data = text_to_wav(string)
    return f'<audio controls src="data:audio/wav;base64, {audio_data}"></audio>'

@app.route('/calibrate/', methods=['GET'])
def calibrate_fortune_teller():
    return render_template('/pages/calibrate.html',default_pre_prompt=DEFAULT_PRE_PROMPT)

@app.route('/calibrate/', methods=['POST'])
def calibrate_fortune_teller_custom():
    pre_prompt = request.form.get('pre_prompt',DEFAULT_PRE_PROMPT)
    prompt = request.form.get('prompt',"Tell me a fortune")
    fortune = create_fortune(query=prompt,pre_prompt=pre_prompt)
    return render_template('/pages/calibrate.html',fortune=fortune,pre_prompt=pre_prompt,prompt=prompt)

@app.route('/calibrate/save', methods=['POST'])
def save_calibration():
    response = mongo.db.prompts.insert_one(dict(request.form))
    return "<h3>Prompt Saved! Go to archive to see all saved prompts.</h3>"

@app.route('/calibrate/all', methods=['GET'])
def calibration_see_all():
    cursor = mongo.db.prompts.find({})
    prompts = [p for p in cursor]
    return render_template("/pages/calibrate_all.html",prompts=prompts)

def get_fortune(**kwargs):
    fortune = mongo.db.fortunes.find_one({}|kwargs,sort=[('last_viewed',1)])
    mongo.db.fortunes.update_one({'_id': fortune['_id']},{'$inc': {'views': 1}, '$set': {'last_viewed': datetime.now()}})
    return fortune

@app.route('/trump/')
def fortune_teller_trump():
    fortune = get_fortune(voice="trump")
    entropy = random.random()
    return render_template('/pages/fortune.html',entropy=entropy,**fortune)

@app.route('/')
def index():
    fortune = get_fortune(voice="default")
    entropy = random.random()
    return render_template('/pages/fortune.html',entropy=entropy,**fortune)


if __name__ == '__main__':
    app.run(host="127.0.0.1",port="8666",debug=True)
