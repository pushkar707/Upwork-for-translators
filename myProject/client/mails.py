from flask_babel import gettext
from flask import current_app,request,session
from flask_login import current_user
from flask_mail import Message
from myProject import mail
from datetime import datetime,timedelta
from pytz import timezone
import os
from jinja2 import Template,FileSystemLoader,Environment
from myProject.models import Bot,Translation


site_admin = 'pcktlwyr@gmail.com'
site_title = "IT Translate"
grace_period = 10

def nonempty(value):
    return value.strip() != ' -> '

## JINJA2 using template not inline HTML
project_root = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
pathToTemplates = os.path.join(project_root, 'templates')
template_env = Environment(loader=FileSystemLoader(pathToTemplates))
template_env.filters['nonempty'] = nonempty
def render_template2(template_filename, **context):
    return template_env.get_template(template_filename).render(**context)

def forgotPassMail(reciever):
    basicGreeting = gettext("Hello from")
    subject = "{} {}".format(basicGreeting, site_title)
    sender = "{}".format(site_admin) 
    msg = Message(
        subject,
        sender =sender,
        recipients = [reciever]
    )
    changePasswordPrompt = gettext('Click the link below to change your password')
    msg.body = f"{changePasswordPrompt}: {request.base_url}change/{id}"
    mail.send(msg)
    

def makeRequestNativeMail():
    with current_app.app_context():
        beta_testers = ['exitnumber3@mail.ru']
        candidates = ['publicvince102@gmail.com','deruen@proton.me', 'exitnumber3@mail.ru', 'publicvince103@gmail.com',"bansalpushkar100@gmail.com"]
        #new_candidates = list(set(beta_testers + candidates)) #use later
        if current_user.email in candidates:
            candidates.remove(current_user.email)
        site_time_zone = 'CET' if not current_app.config["SITE_TIMEZONE"] else current_app.config["SITE_TIMEZONE"]
        site_currency = current_app.config["SITE_CURRENCY"]
        wordCount= len(session['popup_trans']['text'].split(' '))
        srcText = session['popup_trans']['text']
        currUserEmail = current_user.email
        fromLang = session['popup_trans']['language_from']
        toLang = session['popup_trans']['language_to']
        now = datetime.now(timezone(site_time_zone))
        formPriceData = request.form['price']
        timeNow = now.strftime("%H:%M")
        deadline = datetime.now(timezone(site_time_zone)) + timedelta(minutes=int(grace_period) + int(session['popup_trans']['deadline']))
        deadline = deadline.strftime("%H:%M")
        glossaryPairs = session['popup_trans']['glossaryPairs']
        fGlossaryPairs= [item for item in glossaryPairs if item != ' -> ']
        print(type(glossaryPairs))
        print(glossaryPairs)
        # hrefString = "{request.base_url}translator/accept-page/{session['popup_trans']['id']}"
        hrefString = "{}/translator/accept-page/{}".format(request.base_url, session['popup_trans']['id'])
        msg_site_title = "A new Job offer from {}".format(site_title)
        site_admin = 'pcktlwyr@gmail.com'
        msg = Message(
            msg_site_title,
            sender = site_admin,
            bcc = candidates
            )
        msg.html = render_template2('client2candidates.html', srcText=srcText, currUserEmail=currUserEmail, fromLang=fromLang, toLang=toLang, siteCurrency=site_currency, formPriceData=formPriceData,wordCount=wordCount, timeNow=timeNow, deadline=deadline, glossaryPairs= fGlossaryPairs, hrefString=hrefString)
        mail.send(msg)

def makeRequestBotMail():
    with current_app.app_context():
        msg = Message(
            'A translation has been submitted by a Translator',
            sender ='pcktlwyr@gmail.com',
            recipients = [current_user.email]
        )
        bot = Bot.query.get(1)
        price = request.form['price']
        msg.html = f'''
        <div style="color:black">
        <h3>Source text</h3>
        <p>{session['popup_trans']['text']}</p>
        <h3>More details: </h3>
        Translator's email: {bot.email} <br>
        Translation: {session['popup_trans']['language_from']} to {session['popup_trans']['language_to']} <br>
        Price: {price} <br>
        Total words: {session['popup_trans']['words']} <br>
        <h4>Glossary Pairs</h4>
        {",".join([f"{i['source']} -> {i['target']}" for i in session['popup_trans']['glossaryPairs']])}
        <br>
        Click HERE to view and review the translation.
        </div>
        '''
        mail.send(msg)

def ratingMail(id):
    translation = Translation.query.get(id)
    msg = Message(
                    'A Translation has been reviewed and accepted by a Client',
                    sender ='pcktlwyr@gmail.com',
                    recipients = [translation.translator.email]
                )
    msg.html = f'''
    <h3>Text: </h3>
    <p>{translation.text}</p>
    <h3>More Details: </h3>
    Client's Email: {translation.client.email} <br>
    Translation: {translation.language_from} to {translation.language_to} <br>
    Price: {translation.price}<br>
    Words: {translation.words}<br>
    Rating: {translation.rating}
    <br>
    '''
    mail.send(msg)