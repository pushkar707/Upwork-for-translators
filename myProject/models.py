from myProject import db,login_manager
import logging
from flask_login import UserMixin
from werkzeug.security import generate_password_hash,check_password_hash
import uuid
from datetime import datetime
from pytz import timezone
import os
import requests
import json
import subprocess
from enum import Enum

# Configure the logger
logging.basicConfig(filename="app.log", level=logging.INFO, format="%(asctime)s %(message)s", datefmt="%d %M %Y-%H:%M:%S")


@login_manager.user_loader
def load_user(user_id):
    return Client.query.get(user_id)

class GlossaryPair(db.Model,UserMixin):
    """
    A database table to track glossary entries made on the Create Translation form
    Thru translationsId can track back to client or put clientID in table
    keep the terms in a database to allow for client to build custom vocab over several projects
    Each src target pair needs to be sent with a particualr translation and applies for a partocular language from to only
    """
    __tablename__ = 'glossary_pairs'
    
    id = db.Column(db.Integer,primary_key=True)
    sourceText=db.Column(db.String(255),nullable=True)
    targetText=db.Column(db.String(255),nullable=True)
    translationId = db.Column(db.Integer,db.ForeignKey('translations.id'))

    def __init__(self,sourceText,targetText,translationId):
        # Each (src, tar) pair goes into the glossaryPairs list to be sent for MT /client email
        self.sourceText = sourceText
        self.targetText = targetText
        self.translationId = translationId

class Client(db.Model,UserMixin):
    
    __tablename__ = 'clients'

    id = db.Column(db.Integer,primary_key=True)
    name = db.Column(db.String)
    email = db.Column(db.String, unique=True,index=True)
    password = db.Column(db.String)
    change_pass = db.Column(db.String,unique=True)

    translations = db.relationship('Translation',backref='client',lazy=True)
    
    def __init__(self,name,email,password):
        self.name = name
        self.email = email
        self.password = generate_password_hash(password)

    def check_password(self,password):
        return check_password_hash(self.password,password)

    def changePassLink(self):
        id = str(uuid.uuid4())
        self.change_pass = id
        return id
    
# class Language(Enum):
#     de = 1
#     en = 2
#     ru = 3


'''
This needs to be renamed Job  bc that is what it is
A single Client issues a Job, A Job can be a Translation or a Proofread(manual | MTPE)
Then the Job has a Type enum
'''

class Translation(db.Model,UserMixin):

    __tablename__ = 'translations'
    clients = db.relationship(Client)
    id = db.Column(db.Integer,primary_key=True)
    client_id = db.Column(db.Integer,db.ForeignKey('clients.id'),nullable=False)
    language_from = db.Column(db.String)
    language_to = db.Column(db.String)
    deadline = db.Column(db.Integer)
    deadline_time = db.Column(db.DateTime)
    text = db.Column(db.String)
    words = db.Column(db.Integer)
    statusId = db.Column(db.Integer,db.ForeignKey('status.id'),nullable=False)
    price = db.Column(db.Integer)
    translation = db.Column(db.String)
    translatorId = db.Column(db.Integer,db.ForeignKey('translators.id'))
    rating = db.Column(db.Float())
    createdAt = db.Column(db.DateTime,default=datetime.now(timezone('CET')))
    acceptedAt = db.Column(db.DateTime)
    submittedAt = db.Column(db.DateTime)
    onTime = db.Column(db.Boolean)
    rejectCriteria = db.Column(db.Integer,default=1)
    botId=db.Column(db.Integer,db.ForeignKey('bots.id'))
    glosssaryPairs = db.relationship('GlossaryPair',backref="translation",lazy=True)

    def __init__(self,client_id,l_to,deadline,text,statusId,words):
        self.client_id = client_id
        self.language_to = l_to
        self.deadline = deadline
        self.text = text
        self.words = words
        self.statusId = statusId

    def postProcess(self,price):
        self.price = price

class Status(db.Model,UserMixin):
    __tablename__ = 'status'
    # choices=[('new', 'new'), ('notpaid', 'AwaitingPayment'), ('pending', 'PendingTranslatorAcceptance'),('accepted', 'TranslatorAccepted'), ('submitted', 'TranslatorSubmitted'), ('completed', 'TranslationRated'),('error', 'SomeError')]
    id = db.Column(db.Integer,primary_key=True)
    name = db.Column(db.String, db.Enum("new", "notpaid", "pending", "accepted", "submitted", "completed", "error"))

    def __init__(self,name):
        self.name = name


class Service(db.Model,UserMixin): 

    __tablename__ = 'services'

    id = db.Column(db.Integer,primary_key=True)
    language_from = db.Column(db.String)
    language_to = db.Column(db.String)
    min_price = db.Column(db.Integer)
    target_price = db.Column(db.Integer)
    deadline = db.Column(db.Integer)
    translatorId = db.Column(db.Integer,db.ForeignKey('translators.id'))
    botId = db.Column(db.Integer,db.ForeignKey('bots.id'))

    __table_args__=(db.UniqueConstraint('language_from',"language_to","translatorId",name="from_to"),)

    def __init__(self,l_from,l_to,min_price,target_price,translator,deadline):        
        self.language_from= l_from
        self.language_to = l_to
        self.min_price = min_price
        self.target_price = target_price
        self.translatorId=translator
        self.deadline = deadline

class Translator(db.Model,UserMixin):

    __tablename__ = 'translators'

    id = db.Column(db.Integer,primary_key=True)
    name = db.Column(db.String)
    email = db.Column(db.String, unique=True)
    password = db.Column(db.String)
    change_pass = db.Column(db.String,unique=True)
    is_human = db.Column(db.Boolean)
    translations = db.relationship('Translation',backref="translator",lazy=True)
    services = db.relationship('Service',backref="translator",lazy=True)
    rating = db.Column(db.Float(),default=0)
    rating_count = db.Column(db.Integer,default=0)

    def __init__(self,name,email,password,is_human):
        self.name = name
        self.email = email
        self.is_human = bool(is_human)
        self.password = generate_password_hash(password)

    def check_password(self,password):
        return check_password_hash(self.password,password)

    def changePassLink(self):
        id = str(uuid.uuid4())
        self.change_pass = id
        return id

    # def __repr__(self) :
    #     return f"Translator: {self.name}"

class Bot(db.Model,UserMixin):

    __tablename__ = 'bots'

    id = db.Column(db.Integer,primary_key=True)
    api=db.Column(db.String,unique=True)
    email=db.Column(db.String)
    translations = db.relationship('Translation',backref="Bot",lazy=True)
    services = db.relationship('Service',backref="Bot",lazy=True)
    rating = db.Column(db.Float(),default=0)
    rating_count = db.Column(db.Integer,default=0)

    def __init__(self,api,email):
        self.api = api
        self.email = email
    

    # API call will go to separate server 
    # yt(JSON) #!! 
    # translate will call API


    def translate(self,obj):
        target_language = obj['l_to']
        texts = [obj['text']]
        IAM_TOKEN=os.getenv('YANDEX_IAM_TOKEN')
        folder_id=os.getenv('YANDEX_FOLDER_ID')
        if (IAM_TOKEN == "" or not IAM_TOKEN) or (folder_id == "" or not folder_id):
            logging.error("No IAMTOKEN or folder....")

    # {
    #   "sourceLanguageCode": "en",
    #   "targetLanguageCode": "de",
    #   "format": "HTML",
    #   "texts": [
    #     "Once upon a time a young man bought an ex
    # pensive ring and requested that the following
    # engraving appear on it: “To Mary from Henry.”
    # The experienced jeweler advised the young fel
    # low that the inscription read “To my beloved from
    # Henry.”
    # You never know just what might happen!."
    #   ],
    #   "folderId": "b1g7mdqlta9umrhfcnbv",
    #   "glossaryConfig": {
    #     "glossaryData": {
    #       "glossaryPairs": [
    #         {
    #           "sourceText": "jeweler",
    #           "translatedText": "BUMp",
    #           "exact": false
    #         }
    #       ]
    #     }
    #   },
    #   "speller": true
    # }

        body = {
            "targetLanguageCode": target_language,
            "texts": texts,
            "folderId": folder_id,
            #"glossaryConfig": glossaryConfig,
            "speller": True
        }

        headers = {
            "Content-Type": "application/json",
            "Authorization": "Bearer {0}".format(IAM_TOKEN)
        }

        response = requests.post(self.api,
            json = body,
            headers = headers
        )
        print(json.loads(response.text))
        return json.loads(response.text)['translations'][0]['text']
    




    