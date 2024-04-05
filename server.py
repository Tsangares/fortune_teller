# Description: This file is the main server file for the application.
import flask 
from flask import Flask, render_template, request, redirect, url_for, jsonify
from datetime import datetime
from flask_pymongo import PyMongo
from dotenv import load_dotenv
import random
import os
import logging
import json
from fortune import DEFAULT_PRE_PROMPT,create_fortune_text, create_fortune
# Basic startup
load_dotenv()
app = Flask(__name__)

# Setup MongoDB
app.config["MONGO_URI"] = os.getenv("MONGO_URI")
mongo = PyMongo(app)

"""
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
"""

@app.route('/calibrate/', methods=['GET'])
def calibrate_fortune_teller():
    pre_prompt = request.args.get("pre_prompt",DEFAULT_PRE_PROMPT)
    prompt = request.args.get("prompt", None)
    name = request.args.get('name','')
    tags = request.args.get('tags','')
    if tags != '':
        tags = ', '.join(json.loads(tags.replace("'",'"')))
    return render_template('/pages/calibrate.html',pre_prompt=pre_prompt,prompt=prompt,name=name,tags=tags)

@app.route('/calibrate/', methods=['POST'])
def calibrate_fortune_teller_custom():
    pre_prompt = request.form.get('pre_prompt',DEFAULT_PRE_PROMPT)
    prompt = request.form.get('prompt',"Tell me a fortune")
    name = request.form.get('name','')
    tags = request.form.get('tags',[])
    if tags != []:
        tags = [tag.strip() for tag in tags.split(',')]
    tags += ['calibrate','general']
    fortune_text,audio_string = create_fortune(query=prompt,pre_prompt=pre_prompt,tags=tags,name=name)
    tags = ', '.join(tags)
    return render_template('/pages/calibrate.html',fortune=fortune_text,audio_string=audio_string,pre_prompt=pre_prompt,prompt=prompt,name=name,tags=tags)

@app.route('/calibrate/save', methods=['POST'])
def save_calibration():
    tags = request.form.get('tags',[])
    if tags != []:
        tags = [tag.strip() for tag in tags.split(',')]
    oracle = dict(request.form)
    oracle['tags'] = tags
    response = mongo.db.prompts.insert_one(oracle)
    return "<h3>Prompt Saved! Go to archive to see all saved prompts.</h3>"

@app.route('/calibrate/all', methods=['GET'])
def calibration_see_all():
    cursor = mongo.db.prompts.find({})
    prompts = reversed([p for p in cursor])
    return render_template("/pages/calibrate_all.html",prompts=prompts)

def get_last_modified_random_fortune(**kwargs):
    query = [
        {'$match': kwargs}, 
        {'$sort': {'last_viewed': 1}},
        {'$limit': 10},
        {'$sample': {'size': 1}},
    ]
    fortune = mongo.db.fortunes.aggregate(query).next()
    mongo.db.fortunes.update_one({'_id': fortune['_id']},{'$inc': {'views': 1}, '$set': {'last_viewed': datetime.now()}})
    return fortune

def get_fortune(**kwargs):
    #fortune = mongo.db.fortunes.find_one({}|kwargs,sort=[('last_viewed',1)])
    #mongo.db.fortunes.update_one({'_id': fortune['_id']},{'$inc': {'views': 1}, '$set': {'last_viewed': datetime.now()}})
    #return fortune
    return get_last_modified_random_fortune(**kwargs)

@app.route('/trump/')
def fortune_teller_trump():
    fortune = get_fortune(voice="trump")
    entropy = random.random()
    return render_template('/pages/fortune.html',entropy=entropy,**fortune)

@app.route('/weather/')
def get_trump_weather():
    fortune = get_fortune(voice="trump",tags={"$in": ["weather","north carolina"]})
    entropy = random.random()
    return render_template('/pages/fortune.html',entropy=entropy,**fortune)


@app.route('/')
def index():
    fortune = get_fortune(voice="default")
    entropy = random.random()
    return render_template('/pages/fortune.html',entropy=entropy,**fortune)


if __name__ == '__main__':
    app.run(host="127.0.0.1",port="8666",debug=True)
