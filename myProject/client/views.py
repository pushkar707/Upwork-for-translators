from flask import redirect,url_for,render_template,request,Blueprint,session,current_app
import logging
from myProject.models import Client, GlossaryPair,Translation,Status,Bot
from myProject.forms import LoginForm,RegisterationForm,ForgotPassForm,ChangePassForm,TranslationForm,GetPriceForm, GlossaryPairForm
from myProject import db
from flask_login import login_user, logout_user, current_user
from werkzeug.security import generate_password_hash
from datetime import datetime, timedelta
from pytz import timezone
from ..utilities import languageChecker
from myProject.client.mails import forgotPassMail,makeRequestNativeMail,makeRequestBotMail,ratingMail


grace_period = 10
site_admin = 'pcktlwyr@gmail.com'
site_title = "IT Translate"

client = Blueprint('client',__name__)
my_translation = None
@client.route('/',methods=['GET','POST'])
def home():
    if not session.get('page'):
        session['page'] = 'login'
    # REGISTERATION FORM
    registerForm = RegisterationForm()
    if registerForm.validate_on_submit():
        try:
            user = Client(name=registerForm.name.data,
                    email=registerForm.email.data,
                    password=registerForm.password.data)

            db.session.add(user)
            db.session.commit()
            if(session.get('email-exists')):
                session['email-exists'] = False
            session['page'] = 'login'
        except:
            session['email-exists'] = True
            return redirect(url_for('client.home'))

    # LOGIN FORM
    loginForm = LoginForm()
    if loginForm.validate_on_submit():
        user = Client.query.filter_by(email=loginForm.email.data).first()

        if user is not None and user.check_password(loginForm.password.data):
            login_user(user)

            next = request.args.get('next')
            if next == None or not next[0] == '/':
                next = url_for('client.home')

            session['trans-page'] = 'create'
            session['user'] = 'client'
            if(session.get('invalid-login')):
                session['invalid-login'] = False
            return redirect(next)
        else:
            session['invalid-login'] = True
            return redirect(url_for('client.home'))

    # Change Password Form
    forgotPassForm = ForgotPassForm()
    if forgotPassForm.validate_on_submit():
        user = Client.query.filter_by(email=forgotPassForm.email.data).first()
         
        if user is not None:
            id = user.changePassLink()
            db.session.commit()
            forgotPassMail(user.email)
            return redirect(url_for('client.home'))
    # USERS TABLE
    users = Client.query.all()    
    
    # TRANSLATIONS TABLE
    try:
        translations = Client.query.filter_by(id=current_user.id).first().translations
    except:
        translations = []
    lang_list_langdetect = ['af', 'an', 'ar', 'ast', 'az', 'bg', 'bn', 'br', 'bs', 'ca', 'ceb', 'cs', 'cy', 'da', 'de', 'el', 'en', 'eo', 'es', 'et', 'eu', 'fa', 'fi', 'fr', 'ga', 'gl', 'gu', 'he', 'hi', 'hr', 'ht', 'hu', 'hy', 'id', 'is', 'it', 'ja', 'jv', 'ka', 'kk', 'km', 'kn', 'ko', 'ku', 'ky', 'la', 'lb', 'lo', 'lt', 'lv', 'mg', 'mhr', 'mi', 'mk', 'ml', 'mn', 'mr', 'mrj', 'ms', 'mt', 'my', 'ne', 'nl', 'nn', 'no', 'oc', 'pa', 'pap', 'pl', 'ps', 'pt', 'ro', 'ru', 'si', 'sk', 'sl', 'sq', 'sr', 'su', 'sv', 'sw', 'ta', 'te', 'tg', 'th', 'tl', 'tr', 'tt', 'uk', 'ur', 'uz', 'vi', 'vo', 'war', 'xh', 'yi', 'zh-cn', 'zh-tw']
    return render_template('client.html',registerForm=registerForm,loginForm=loginForm,forgotPassForm=forgotPassForm,users=users,translations=translations,translation=my_translation,langs=lang_list_langdetect)

@client.route('/logout')
def logout():
    logout_user()
    session['user'] = None
    if(session.get('error')):
        session['error'] = None
    return redirect(url_for('client.home'))

@client.route('/forgot')
def forgot():
    session['page'] = 'forgot'
    if(session.get('invalid-login')):
        session['invalid-login'] = False
    return redirect(url_for('client.home'))

@client.route('/login')
def login():
    session['page'] = 'login'
    return redirect(url_for('client.home'))

@client.route('/register')
def register():
    session['page'] = 'register'
    session['email-exists'] = False
    if(session.get('invalid-login')):
        session['invalid-login'] = False
    return redirect(url_for('client.home'))

# @client.route('/price-popup')
# def price_pop():
#     session['popup'] = True
#     return redirect(url_for('client.home'))

@client.route('/remove-popup/<id>')
def remove_price_pop(id):
    session['popup'] = False
    translation = Translation.query.get(id)
    session['popup_close'] = True
    db.session.delete(translation)
    db.session.commit()
    return redirect(url_for('client.home'))

@client.route('/change/<id>',methods=['GET','POST'])
def change(id):
    user = Client.query.filter_by(change_pass=id).first()
    if user is not None:
        changePassForm = ChangePassForm()
        if changePassForm.validate_on_submit():
            password = generate_password_hash(changePassForm.password.data)
            user.password = password
            db.session.commit()
            session['page'] = 'login'
            return redirect(url_for('client.home'))
        return render_template('change-pass.html',changePassForm=changePassForm,user=user)
    else:
        return "Page Not Found"

# TRANSLATIONS
my_translation = None
@client.route('/create-translation',methods=['GET','POST'])
def create_translation():
    if request.method == "GET":
        session['trans-page'] = "create"
        session['glossary-pairs'] = 6
        session['error_translation'] = None
        session['error'] = None
        if(session.get('popup_close')):
            session['popup_close'] = None
        return redirect(url_for('client.home'))
    
    # ADD TRANSLATION FORM

    elif request.method == "POST":
        deadline = request.form['deadline']
        translation_type = request.form['translation-type']
        target_language = request.form['target_language']
        glossaryPairs = []
        for i in range(6):
            source = request.form[f"glossary-source-{i+1}"]
            target = request.form[f"glossary-target-{i+1}"]
            glossaryPairs.append({'source':source,"target":target})

        text = request.form['text']
        words = len(text.split(" "))
        # TO BE USED TO REFILL THE FORM IF THERE IS ERROR OR POPUP IS CLOSED
        session['error_translation'] = {'target_language':target_language,
                                        'deadline':deadline,
                                        'text' : text,
                                        'translation_type': translation_type,
                                        'glossary_pairs':glossaryPairs}
        if(words > 500 or words < 50):
            session['error'] = f"Word limit is 50 to 500 words. You entered {words} words."
        else:
            status = Status('new') 
            db.session.add(status)
            db.session.commit()
            translation = Translation(client_id=current_user.id,
                                      l_to=target_language,
                                      deadline=int(deadline),
                                      text=text,
                                      words=words,
                                      statusId=status.id)
            db.session.add(translation)
            db.session.commit()
            for i in range(6):
                pair = GlossaryPair(sourceText=request.form[f"glossary-source-{i+1}"],
                                    targetText=request.form['target_language'],
                                    translationId=translation.id)
                db.session.add(pair)
                db.session.commit()
            session['popup'] = True
            session['error'] = None
            session['avg_price'] = "{:.2f}".format(0.08*words) #this will come from DB
            min_word_price = current_app.config["MIN_WORD_PRICE"]
            site_time_zone = 'CET' if not current_app.config["SITE_TIMEZONE"] else current_app.config["SITE_TIMEZONE"]
            grace_period = 10
            session['min_price'] = "{:.2f}".format(min_word_price*words)
            now = datetime.now(timezone(site_time_zone))
            session['deadline_as_time'] = (datetime.now(timezone(site_time_zone)) + timedelta(minutes=int(grace_period) + int(deadline))).strftime("%H:%M")
            source_langauge = languageChecker(text)
            print(source_langauge)
            my_translation = {'id': translation.id,'language_from':source_langauge,'language_to':translation.language_to,"deadline":translation.deadline,"text":translation.text,"words":words,"glossaryPairs":glossaryPairs}
            session['popup_trans'] = my_translation
        return redirect(url_for('client.home'))
    
@client.route('/add-price-form',methods=['GET','POST'])
def makeRequest():
    if request.method == 'POST':
        price = request.form['price']
        source_language = request.form['source_language']
        translation_type = session['error_translation']['translation_type']
        site_time_zone = 'CET' if not current_app.config["SITE_TIMEZONE"] else current_app.config["SITE_TIMEZONE"]
        if(translation_type == "native"):
            """if at or above threshold call humans"""
            translation = Translation.query.get(session['popup_trans']['id'])
            translation.postProcess(price)
            deadline = datetime.now(timezone(site_time_zone)) + timedelta(minutes=int(grace_period) + int(session['popup_trans']['deadline']))
            translation.deadline_time = deadline.astimezone(timezone('CET'))
            translation.language_from = source_language
            db.session.commit()
            makeRequestNativeMail()
            if(session.get('popup_close')):
                session['popup_close'] = None
        else:
            """Call bot; Prepare DB first"""
            bot = Bot.query.get(1) #1 DB
            l_to = session['popup_trans']['language_to']
            l_from = session['popup_trans']['language_from']
            logging.debug(session['popup_trans']['glossaryPairs'])

            #FIX GLOSSARY PAIRS
        #             {
        #   "sourceText": "jeweler",
        #   "translatedText": "Uhrmacher",
        #   "exact": false
        # }
            
            obj = {'l_to':l_to,'text':session['popup_trans']['text']}
            try:
                # THIS OBJ MUST ALSO CONTAIN GLOSSARY ENTRIES
                res = bot.translate(obj)
            except:
                # return error from API
                res = '''Please contact the help desk on {site_admin}'''

            translation = Translation.query.get(session['popup_trans']['id'])
            translation.botId = bot.id
            translation.postProcess(price)
            translation.translation = res
            translation.acceptedAt=datetime.now(timezone(site_time_zone))
            translation.submittedAt=datetime.now(timezone(site_time_zone))
            translation.language_from = l_from
            db.session.commit()
            if(session.get('popup_close')):
                session['popup_close'] = None
            makeRequestBotMail()

        session['popup'] = False
        return redirect(url_for('client.show_translation',id=session['popup_trans']['id']))

@client.route('/translation/<id>')
def show_translation(id):
    translation = Translation.query.filter_by(id=id).first()
    if(session.get('error')):
        session['error'] = None
    try:
        if(translation.translator):
            translation.email = translation.translator.email
        elif(translation.Bot):
            translation.email = translation.Bot.email
    except:
        translation.email = None
    session['trans-page'] = translation
    return redirect(url_for('client.home'))

@client.route('/rating/<id>',methods=['GET','POST'])
def submit_review(id):
    translation = Translation.query.get(id)
    rating = int(request.form.get('rating'))
    translation.rating = rating
    if(translation.translator):
        translator_rating = translation.translator.rating or 0
        rating_count = translation.translator.rating_count or 0
        translation.translator.rating_count=rating_count+1
        new_rating = (translator_rating + rating)/(rating_count+1)
        translation.translator.rating = new_rating
        ratingMail(id)
    elif (translation.Bot):
        bot_rating = translation.Bot.rating or 0
        rating_count = translation.Bot.rating_count or 0
        translation.Bot.rating_count=rating_count+1
        new_rating = (bot_rating + rating)/(rating_count+1)
        translation.Bot.rating = new_rating
    db.session.commit()
    
    return redirect(url_for('client.show_translation',id=translation.id))

@client.route('/test')
def delete_trans():
    translation = Translation.query.get(7)
    translation.translation = 'Lorem ipsum dolor sit, amet consectetur adipisicing elit. Dicta explicabo, quae facilis fugit deserunt error? Temporibus nobis veniam sed repellat at deleniti, alias laboriosam, vel, aspernatur laborum est! Eum, magnam repellat! Sunt alias repellat culpa ratione quod maxime, enim blanditiis expedita sequi sint quae tempora modi dolorem iste, mollitia debitis reiciendis? Quos illum eum mollitia odio libero ipsum? Rerum eaque quam corrupti inventore ipsa maxime modi voluptatibus doloribus eos error aspernatur neque commodi consectetur quae, vitae illum at a placeat voluptatem magni? Commodi, necessitatibus corrupti laboriosam ipsa sint quis perferendis aut dolorum non, nam soluta blanditiis natus. Dolorum fuga modi aut quisquam, possimus omnis eius excepturi aliquid et, enim vero architecto ipsum ipsam minima delectus ea iste sapiente voluptas veritatis recusandae unde commodi culpa iure. Quas, sit nesciunt mollitia expedita doloribus neque optio asperiores nulla iusto fuga commodi veritatis vel quae eos labore hic rem aperiam totam soluta? Aut voluptatibus nisi commodi officia itaque nihil nobis esse velit voluptates optio tempora vitae laboriosam sed magni obcaecati, quasi unde impedit reiciendis inventore, ratione porro consequuntur illum fuga cumque? Quam, possimus! Facere laboriosam esse odit quae quia dolore rerum sint aliquam pariatur quasi temporibus harum eveniet debitis praesentium quas enim eaque, autem, nostrum illo. Dolorum eaque dolore quam possimus eum quas minus reiciendis, nam pariatur beatae molestiae voluptatem quo nobis, hic explicabo unde, odio provident assumenda placeat? Sequi error dicta molestias debitis alias minus necessitatibus reprehenderit reiciendis temporibus nam molestiae porro, quas distinctio? Tempora excepturi provident nihil iusto fugiat dolores ducimus necessitatibus neque ipsum. Eligendi, quae? Quod dignissimos totam voluptate, aliquid molestiae modi iusto facere nulla nesciunt, at expedita nihil, in molestias officiis aliquam? Accusamus fugit reprehenderit, similique harum maxime repudiandae. Tempora repudiandae culpa libero consequatur, quos natus rerum. Quas laborum nihil magni vero porro natus dolorum magnam consequatur incidunt saepe distinctio recusandae quo fugiat esse sit harum tenetur, maiores eum aut autem! Non mollitia asperiores optio consequatur quidem molestiae, fuga eius odio in accusantium similique pariatur iste quod vero? Veritatis officia, quo magnam placeat magni reprehenderit voluptate dolore accusantium esse corrupti saepe. Sunt consequuntur officia corporis earum error doloremque tenetur accusamus'
    db.session.commit()
    return None

@client.route('/add-glossary-pair')
def addGlossary():
    num = session.get('glossary-pairs')
    if (num<10):
        session['glossary-pairs'] = num+1
    return redirect(url_for('client.home'))

"""
A route for allow new glossaryEntries to be added to the database while the form is being processed for the transaltion request
The create translation form
"""
# @client.route('/add_glossary_pair',methods=['POST'])
# def add_glossary_pair():
#     sourceText = request.form['sourceText']
#     targetText= request.form['targetText']
#     glossaryPair = GlossaryPair(sourceText=sourceText, targetText=targetText)
#     db.session.add(glossaryPair)
#     db.session.commit()
#     #where do we go after this? May need to add another one
#     return gettext("Glossary Pair submitted successfully!")