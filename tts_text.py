from TTS.api import TTS
from TTS.utils.synthesizer import Synthesizer
from TTS.utils.io import load_checkpoint
from TTS.tts.datasets import load_tts_samples
from io import BytesIO
from scipy.io import wavfile
import numpy as np
import openai
import base64
from dotenv import load_dotenv
import os
from pymongo import MongoClient
from datetime import datetime
import logging
import random



# Basic startup
load_dotenv()

# Setup MongoDB
client = MongoClient(os.getenv("MONGO_URI"))
db = client.fortune_teller
# Setup OpenAI
openai.api_key = os.getenv("OPENAI_API_KEY")


# Setup TTS
SAMPLE_RATE = 16_000
#model_name="tts_models/en/ljspeech/tacotron2-DCA"
#tts = TTS(model_name)
#Load Trump Synthesizer
tts = None
def load_voice_trump(): 
    trump = Synthesizer(
            tts_config_path="./models/trump/config.json",
            tts_checkpoint="./models/trump/trump.pth",
            use_cuda=False,
        )
    return trump

def load_voice_default(): 
    model_name="tts_models/en/ljspeech/tacotron2-DCA"
    tts = TTS(model_name)  
    return tts

def text_to_wav(text,voice="default"):
    global tts
    if voice == "default" and tts is None:
        tts = load_voice_default()
    elif voice == "trump" and tts is None:
        tts = load_voice_trump()
    wav = tts.tts(text)
    wav = np.array(wav)
    
    sample_rate = tts.output_sample_rate if isinstance(tts,Synthesizer) else tts.synthesizer.output_sample_rate
    wav_norm = wav * (32767 / max(0.01, np.max(np.abs(wav))))
    bytes_wav = bytes()
    byte_io = BytesIO(bytes_wav)
    wavfile.write(byte_io, sample_rate, wav_norm.astype(np.int16))
    ##wav_bytes = byte_io.read()
    #audio_data = base64.b64encode(wav_bytes).decode('UTF-8')
    return audio_data
if __name__ == "__main__":
    text = open('text.txt').read()
    audio_string = text_to_wav(text,'trump')
