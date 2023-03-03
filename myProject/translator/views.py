from flask import redirect,url_for,render_template,request,Blueprint,session
from myProject.models import Translation,Translator,Service
from myProject.forms import LoginForm,ForgotPassForm,ChangePassForm,RegisterTranslator,AddServiceForm,SubmitTranslationForm
from myProject import db,mail
from flask_login import login_user, logout_user, current_user
from flask_mail import Message
from werkzeug.security import generate_password_hash
from datetime import datetime, timedelta
from pytz import timezone


site_time_zone = 'Europe/Berlin'
translator = Blueprint('translator',__name__,url_prefix='/translator')
myUser = None
@translator.route('/',methods=['GET','POST'])
def home():
    if not session.get('page'):
        session['page'] = 'login'

    # REGISTERATION FORM
    registerForm = RegisterTranslator()
    if registerForm.validate_on_submit():
        try:
            user = Translator(name=registerForm.name.data,
                    email=registerForm.email.data,
                    password=registerForm.password.data,
                    is_human=True)        

            db.session.add(user)
            db.session.commit()
            if(session.get('email-exists')):
                session['email-exists'] = False
            session['page'] = 'login'
        except:
            session['email-exists'] = True
        return redirect(url_for('translator.home'))

    # LOGIN FORM
    loginForm = LoginForm()
    if loginForm.validate_on_submit():
        global myUser
        user = Translator.query.filter_by(email=loginForm.email.data).first()

        if user is not None and user.check_password(loginForm.password.data):
            login_user(user)
            myUser = user
            session['translatorId'] = current_user.id
            next = request.args.get('next')
            if next == None or not next[0] == '/':
                next = url_for('translator.home')

            session['user'] = 'translator'
            if(session.get('translator_page')!='accept'):
                session['translator_page']='services'
            if(session.get('invalid-login')):
                session['invalid-login'] = False
            return redirect(next)
        else:
            session['invalid-login'] = True
            return redirect(url_for('translator.home'))

    # Change Password Form
    forgotPassForm = ForgotPassForm()
    if forgotPassForm.validate_on_submit():
        user = Translator.query.filter_by(email=forgotPassForm.email.data).first()

        if user is not None:
            id = user.changePassLink()
            db.session.commit()
            print(id)
            msg = Message(
                'Hello',
                sender ='pcktlwyr@gmail.com',
                recipients = [user.email]
            )
            msg.body = f'Click the link below to change your password:  {request.base_url}/change/{id}'
            mail.send(msg)
            return redirect(url_for('translator.home'))

    # ADD SERVICE FORM
    addServiceForm = AddServiceForm()
    if addServiceForm.validate_on_submit():
        try:
            service = Service(l_from=addServiceForm.language_from.data,
                        l_to=addServiceForm.language_to.data,
                        min_price=addServiceForm.min_price.data,
                        target_price=addServiceForm.target_price.data,
                        deadline=addServiceForm.deadline.data,
                        translator=session.get('translatorId'))
            db.session.add(service)
            db.session.commit()
            if(session.get('service-exists')):
                session['service-exists'] = False
        except:
            session['service-exists'] = True
            return redirect(url_for('translator.home'))

    # SUBMIT TRANSLATION FORM
    submitTranslationForm = SubmitTranslationForm()
    if(submitTranslationForm.validate_on_submit()):
        translation = Translation.query.get(session['trans-page'].id)
        translation.translation = submitTranslationForm.translation.data 
        translation.submittedAt = datetime.now(timezone('CET'))
        onTime = (translation.deadline_time + timedelta(minutes=15))>translation.submittedAt
        print(onTime)
        translation.onTime = onTime
        db.session.commit()
        msg = Message(
                'Translation submitted by the translator',
                sender ='pcktlwyr@gmail.com',
                recipients = [translation.client.email]
            )
        msg.html = f'''
        <h3>Source text: </h3>
        <p>{translation.text}</p>
        <h3> More Details: </h3>
        Translator's email: {translation.translator.email} <br>
        Translation: {translation.language_from} to {translation.language_to} <br>
        Price: {translation.price}<br>
        Words: {translation.words}<br>
        '''
        mail.send(msg)
        return redirect(url_for('translator.show_translation',id=translation.id))
    # USERS TABLE
    users = Translator.query.all()

    # SERVICES
    try:
        services = Translator.query.filter_by(id=session.get('translatorId')).first().services
    except:
        services = []
    
    return render_template('translator.html',registerForm=registerForm,loginForm=loginForm,forgotPassForm=forgotPassForm,users=users,user=myUser,services=services,addServiceForm=addServiceForm,submitTranslationForm=submitTranslationForm)

@translator.route('/logout')
def logout():
    session['user'] = None
    session['page'] = 'login'
    session['translator_page'] = None
    session['translations'] = None
    session['service-exists'] = False
    logout_user()
    session[id] = None
    return redirect(url_for('translator.home'))

@translator.route('/forgot')
def forgot():
    session['page'] = 'forgot'
    if(session.get('invalid-login')):
        session['invalid-login'] = False
    return redirect(url_for('translator.home'))

@translator.route('/login')
def login():
    session['page'] = 'login'
    return redirect(url_for('translator.home'))

@translator.route('/register')
def register():
    session['page'] = 'register'
    session['email-exists'] = False
    if(session.get('invalid-login')):
        session['invalid-login'] = False
    return redirect(url_for('translator.home'))


@translator.route('/change/<id>',methods=['GET','POST'])
def change(id):
    user = Translator.query.filter_by(change_pass=id).first()
    if user is not None:
        changePassForm = ChangePassForm()
        if changePassForm.validate_on_submit():
            password = generate_password_hash(changePassForm.password.data)
            user.password = password
            db.session.commit()
            session['page'] = 'login'
            return redirect(url_for('translator.home'))
        return render_template('change-pass.html',changePassForm=changePassForm,user=user)
    else:
        return "Page Not Found"

@translator.route('/accept-page/<translationId>',methods=['GET','POST'])
def accept_page(translationId):
    translation = Translation.query.get(translationId)
    time_diff = translation.deadline_time.astimezone(timezone('CET')) - datetime.now(timezone('CET'))
    # deadline_in_minutes = str(time_diff.total_seconds() / 60)
    # deadline_in_minutes = datetime.now(timezone('CET'))
    if(translation.translatorId):
        return "Sorry, translation has already been assigned"
    else:
        # WAIT! We do not want client.id == translator.id
        session['translation'] = {"id":translation.id,"language_from":translation.language_from,"language_to":translation.language_to,'price':translation.price,"deadline":translation.deadline_time,"text":translation.text}
        # session['translation'].append({"deadline_in_minutes": deadline_in_minutes})
        session['translator_page'] = 'accept'
        return redirect(url_for('translator.home'))

@translator.route('/accept/<translationId>/<translatorId>')
def accept_translation(translationId,translatorId):
    translation = Translation.query.get(translationId)
    translation.translatorId=translatorId
    translation.acceptedAt=datetime.now(timezone('CET'))
    db.session.commit()
    session['translator_page'] = 'translations'
    session['translation'] = None
    msg = Message(
                'Translation accepted by translator',
                sender ='pcktlwyr@gmail.com',
                recipients = [translation.client.email]
    )
    msg.html = f'''
    <h3>Text: </h3>
    <p>{translation.text}</p>
    <h3>More Details: </h3>
    Transaltor's Email: {translation.translator.email} <br>
    Translation: {translation.language_from} to {translation.language_to} <br>
    Price: {translation.price}<br>
    Words: {translation.words}<br>
    <br>
    '''
    mail.send(msg)
    return redirect(url_for('translator.translations'))

@translator.route('/reject')
def reject_translation():
    session['translator_page'] = 'translations'
    session['translation'] = None
    return redirect(url_for('translator.translations'))

@translator.route('/translations')
def translations():
    session['service-exists'] = False
    id = session.get('translatorId')
    translations = Translator.query.get(id).translations
    if(len(translations)>0):
        session['trans-page'] = translations[0]
        session['translator_page']='translations'
    else:
        session['translator_page'] = 'services'
    my_translations = []
    for translation in translations:
        my_translations.append({"id":translation.id,"language_from":translation.language_from,"language_to":translation.language_to,'price':translation.price,"text":translation.text})
    
    session['translations'] = my_translations
    return redirect(url_for('translator.home'))

@translator.route('/translation/<id>')
def show_translation(id):
    translation = Translation.query.filter_by(id=id).first()
    session['trans-page'] = translation
    return redirect(url_for('translator.home'))

@translator.route('/services')
def services():
    session['translator_page']='services'
    session['translations'] = None
    return redirect(url_for('translator.home'))

@translator.route('/delete-service/<id>')
def del_service(id):
    service = Service.query.get(id)
    db.session.delete(service)
    db.session.commit()
    return redirect(url_for('translator.home'))