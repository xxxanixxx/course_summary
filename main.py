import numpy as np
from flask import Flask, render_template, request, redirect, flash, url_for
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from flask_login import UserMixin
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
from sqlalchemy import delete
from collections import Counter
import matplotlib.pyplot as plt
import base64
from io import BytesIO

app = Flask(__name__)
app.secret_key = 'some secret salt'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///parachute.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
login_manager = LoginManager(app)


class Users(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    login = db.Column(db.String(15), nullable=True, unique=True)
    password = db.Column(db.String(500), nullable=True)
    email = db.Column(db.String(30), nullable=True, unique=True)


class Insurance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    period = db.Column(db.Integer, nullable=True)
    cost = db.Column(db.Integer, nullable=True)


class UsersPersonalInfo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(20), nullable=True)
    surname = db.Column(db.String(30), nullable=True)
    passport = db.Column(db.String(10), nullable=True, unique=True)
    id_users_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)


class UsersConfirmed(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    id_users = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    id_personal_info = db.Column(db.Integer, db.ForeignKey('users_personal_info.id'), nullable=True)
    id_insurance = db.Column(db.Integer, db.ForeignKey('insurance.id'), nullable=True)
    date_buy = db.Column(db.DateTime, nullable=True)


##################


class Airplane(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(20), nullable=True)


class Up(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    number = db.Column(db.Integer, nullable=True)


class TypeOfFly(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(30), nullable=True)
    cost = db.Column(db.Integer, nullable=True)
    height = db.Column(db.Integer, nullable=True)


class Flights(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    id_airplane = db.Column(db.Integer, db.ForeignKey('airplane.id'), nullable=True)
    id_up = db.Column(db.Integer, db.ForeignKey('up.id'), nullable=True)
    flag = db.Column(db.Integer, nullable=True, default=0)


class PeopleOnBoard(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(30), nullable=True)
    surname = db.Column(db.String(30), nullable=True)
    id_flights = db.Column(db.Integer, db.ForeignKey('flights.id'), nullable=True)
    id_type_of_fly = db.Column(db.Integer, db.ForeignKey('type_of_fly.id'), nullable=True)
    id_users_confirmed = db.Column(db.Integer, db.ForeignKey('users_confirmed.id'), nullable=True)
    date_of_fly = db.Column(db.Date, nullable=True, default=date.today())


with app.app_context():
    db.create_all()


@login_manager.user_loader
def load_user(user_id):
    return Users.query.get(user_id)


@app.route("/")
def home():
    today = date.today()
    if PeopleOnBoard.query.first():
        if PeopleOnBoard.query.all()[-1].date_of_fly < today:
            for i in Flights.query.all():
                i.flag = 0
                db.session.commit()

    return render_template('home.html')


@app.route("/login", methods=['POST', 'GET'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('personal_area'))
    else:
        if request.method == 'POST':
            log_in = request.form.get('login').lower()
            password_in = request.form.get('password')
            if log_in and password_in:
                user = Users.query.filter_by(login=log_in).first()

                if user and check_password_hash(user.password, password_in):
                    login_user(user)
                    return redirect(url_for('personal_area'))
                    # return render_template('personal_area.html', current_user=current_user)
                else:
                    flash('Логин или пароль некорректны.')
    return render_template('login.html')


@app.route("/logout", methods=['POST', 'GET'])
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))


@app.route("/signup", methods=['POST', 'GET'])
def signup():
    if request.method == 'POST':

        log_up = request.form.get('login_reg').lower()
        password_up = request.form.get('password_reg')
        email_up = request.form.get('email_reg').lower()

        if not (log_up or password_up or email_up):
            flash('Заполните все поля!')
        elif Users.query.filter_by(email=email_up).first():
            flash('Такая почта уже зарегистрирована!')
        elif Users.query.filter_by(login=log_up).first():
            flash('Такой логин уже зарегистрирован!')
        else:
            if len(log_up) > 20:
                flash('Длина логина должна быть до 20 символов!')
            elif ' ' in log_up:
                flash('Логин не должен содержать пробелы!')
            elif '@' not in email_up:
                flash('Некорректно указана почта!')
            else:
                hash = generate_password_hash(password_up)
                new_user = Users(login=log_up, password=hash, email=email_up)
                db.session.add(new_user)
                db.session.commit()
                return redirect(url_for('login'))
    return render_template('signup.html')


@app.route("/flights", methods=['POST', 'GET'])
@login_required
def flights():
    today = date.today()
    # if PeopleOnBoard.query.first():
    #     if datetime.date(PeopleOnBoard.query.all()[-1].date_of_fly) < today:
    #         pass

    first_airplane = Flights.query.all()[:10]
    second_airplane = Flights.query.all()[10:]
    couple_first_airplane = []
    couple_second_airplane = []
    people_1plane_1up = []
    people_1plane_2up = []
    people_2plane_1up = []
    people_2plane_2up = []

    count = 0
    for up in first_airplane:
        if (up.flag == 0 or up.flag == 1) and count < 2:
            couple_first_airplane.append(up)
            count += 1
    count = 0
    for up in second_airplane:
        if (up.flag == 0 or up.flag == 1) and count < 2:
            couple_second_airplane.append(up)
            count += 1

    for people_on_board in PeopleOnBoard.query.filter_by(date_of_fly=today).all():
        for i in couple_first_airplane:
            if people_on_board.id_flights == i.id:
                if i == couple_first_airplane[0]:
                    people_1plane_1up.append(people_on_board.name)
                    people_1plane_1up.append(people_on_board.surname)
                else:
                    people_1plane_2up.append(people_on_board.name)
                    people_1plane_2up.append(people_on_board.surname)
        for i in couple_second_airplane:
            if people_on_board.id_flights == i.id:
                if i == couple_second_airplane[0]:
                    people_2plane_1up.append(people_on_board.name)
                    people_2plane_1up.append(people_on_board.surname)
                else:
                    people_2plane_2up.append(people_on_board.name)
                    people_2plane_2up.append(people_on_board.surname)

    if request.method == 'POST':
        return render_template('flights.html', couple_first_airplane=couple_first_airplane,
                               couple_second_airplane=couple_second_airplane, people_1plane_1up=people_1plane_1up,
                               people_1plane_2up=people_1plane_2up, people_2plane_1up=people_2plane_1up,
                               people_2plane_2up=people_2plane_2up)

    return render_template('flights.html', couple_first_airplane=couple_first_airplane,
                           couple_second_airplane=couple_second_airplane, people_1plane_1up=people_1plane_1up,
                           people_1plane_2up=people_1plane_2up, people_2plane_1up=people_2plane_1up,
                           people_2plane_2up=people_2plane_2up)


@app.route("/personal", methods=['POST', 'GET'])
@login_required
def personal_area():
    if current_user.get_id() == '1':
        return redirect(url_for('settings'))

    name = request.form.get('name')
    surname = request.form.get('surname')
    passport = request.form.get('passport')
    flag = False
    confirmed = ""
    insurance = ""
    personal_info = ""
    date_end = ""
    type_ = ""
    up = ""
    pictures = ''
    count_jumps = ''
    today = datetime.today()
    month = datetime.today().month
    all_money = 0

    if UsersConfirmed.query.filter_by(id_users=current_user.id).first():
        count_jumps = PeopleOnBoard.query.filter_by(id_users_confirmed=UsersConfirmed.query.
                                                    filter_by(id_users=current_user.id).first().id).count()
        for i in PeopleOnBoard.query.filter_by(id_users_confirmed=UsersConfirmed.query.
                filter_by(id_users=current_user.id).first().id, date_of_fly=datetime.date(today)).all():
            all_money += TypeOfFly.query.filter_by(id=i.id_type_of_fly).first().cost
        dates = PeopleOnBoard.query.filter_by(id_users_confirmed=
                                              UsersConfirmed.query.filter_by(id_users=current_user.id).first().id).all()
        if dates:
            dates_date = []
            # dates_count = []
            for i in dates:
                if i.date_of_fly.month == month:
                    dates_date.append(i.date_of_fly.strftime('%Y.%m.%d'))
            coll = Counter(dates_date)

            plt.switch_backend('Agg')
            fig = plt.figure(figsize=(7, 9))
            plt.plot(coll.keys(), coll.values(), 'b.')
            plt.grid()
            plt.xticks(rotation=90)
            plt.yticks(np.arange(min(coll.values()), max(coll.values()) + 1))
            plt.ylabel('Количество записей', color='#211470', fontsize=15)
            plt.title('Записи на прыжки (текущий месяц)', fontsize=20, color='#211470')
            buf = BytesIO()
            fig.savefig(buf, format='png')
            pictures = base64.b64encode(buf.getbuffer()).decode('ascii')

    for i in UsersConfirmed.query.all():
        if current_user.get_id() == str(i.id_users):
            flag = True
            confirmed = UsersConfirmed.query.filter_by(id_users=current_user.get_id()).first()
            insurance = Insurance.query.filter_by(id=confirmed.id_insurance).first()
            personal_info = UsersPersonalInfo.query.filter_by(id=confirmed.id_personal_info).first()
            date_end = confirmed.date_buy + relativedelta(months=insurance.period)
            break

    types = TypeOfFly.query.all()
    flight = Flights.query.filter_by(flag=0).all()
    airplane = []
    for i in flight:
        airplane.append(Airplane.query.filter_by(id=i.id_airplane).first().name)

    list_up = []

    if request.method == 'POST':

        type_ = request.form.get('type')
        up = request.form.get('up')
        flag_up = False

        if name and surname and passport:
            if len(passport) != 10:
                flash('Номер паспорта должен содержать 10 символов!')
            elif UsersPersonalInfo.query.filter_by(id_users_by=current_user.id).first():
                flash('Вы уже отправили заявку! Дождитесь подтверждения администратором.')
                flash('*Если вы указали некорректные данные, то администратор удалит вашу заявку,'
                      ' и вам нужно будет отправить её еще раз*')
            else:
                flash('Заявка отправлена!')
                new_user_personal_info = UsersPersonalInfo(name=name, surname=surname, passport=passport,
                                                           id_users_by=current_user.get_id())
                db.session.add(new_user_personal_info)
                db.session.commit()
                return redirect(url_for('personal_area'))

        if type_ and up:
            if today < date_end:
                for i in PeopleOnBoard.query.filter_by(
                        id_users_confirmed=UsersConfirmed.query.filter_by(id_users=current_user.id).first().id).all():
                    if i.date_of_fly == datetime.date(today):
                        list_up.append(i.id_flights)

                for i in list_up:
                    if int(up) == i or int(up) == 10 + i:
                        flash('Вы уже записались на этот подъем!')
                        flash('*Нельзя записаться на один и тот же подъем, даже если самолеты разные*')
                        flag_up = True
                        break
                    if int(up) == i + 1 or int(up) == i - 1 or int(up) == i + 11 or int(up) == i + 9:
                        flash('Доступна запись только через один подъем.')
                        flash('*Нельзя записаться подряд , даже если самолеты разные*')
                        flag_up = True
                        break

                if not flag_up:
                    if (PeopleOnBoard.query.filter_by(id_flights=up, date_of_fly=datetime.date(today)).count() < 3
                        and int(up) < 11) or (PeopleOnBoard.query.filter_by(id_flights=up, date_of_fly=
                    datetime.date(today)).count() < 10 and int(up) >= 11):
                        new_people_on_board = PeopleOnBoard(
                            name=UsersPersonalInfo.query.filter_by(id_users_by=current_user.id).first().name,
                            surname=UsersPersonalInfo.query.filter_by(id_users_by=current_user.id).first().surname,
                            id_flights=up, id_type_of_fly=type_,
                            id_users_confirmed=UsersConfirmed.query.filter_by(id_users=current_user.id).first().id)
                        db.session.add(new_people_on_board)
                        db.session.commit()
                        flash('Вы успешно записались!')
                    else:
                        flash('К сожалению, на борту нет мест.')
                        flash('Запишитесь на другой подъем!')
            else:
                flash('Ваша страховка просрочена! Вы не можете записаться на подъем.')
                flash('Обратитесь на манифест за продлением.')

    return render_template('personal_area.html', current_user=current_user, flag=flag, confirmed=confirmed,
                           insurance=insurance, personal_info=personal_info, date_end=date_end, types=types,
                           flight=flight, airplane=airplane, count_jumps=count_jumps, pictures=pictures, today=today,
                           all_money=all_money)


@app.after_request
def redirect_to_login(response):
    if response.status_code == 401:
        return redirect((url_for('login') + '?next=' + request.url))
    return response


@app.route("/settings")
@login_required
def settings():
    if current_user.get_id() == '1':
        return render_template('settings.html', current_user=current_user)
    else:
        flash('У вас нет доступа к данной странице')
        return render_template('settings.html')


@app.route("/settings/insurance", methods=['POST', 'GET'])
@login_required
def settings_insurance():
    list_insurance = Insurance.query.order_by('period').all()
    list_conf_users = UsersConfirmed.query.all()
    list_personal_info = []
    list_date_end = []

    for i in range(len(list_conf_users)):
        list_personal_info.append(UsersPersonalInfo.query.filter_by(id=list_conf_users[i].id_personal_info).first())
        list_date_end.append(list_conf_users[i].date_buy +
                             relativedelta(
                                 months=Insurance.query.filter_by(id=list_conf_users[i].id_insurance).first().period))

    today = datetime.today()

    if request.method == 'POST':
        id_users = request.form.get('id_users')
        id_insurance = request.form.get('id_insurance')
        date_buy = request.form.get('date_buy')

        if id_users and id_insurance and date_buy:
            date_buy = datetime.strptime(date_buy, '%Y-%m-%d')
            rows = UsersConfirmed.query.filter_by(id=id_users).first()
            if rows and int(id_insurance) <= 5 and date_buy <= datetime.today():
                rows.id_insurance = id_insurance
                rows.date_buy = date_buy
                db.session.commit()
                return redirect(url_for('settings_insurance'))
            else:
                flash('Проверьте корректность:')
                flash('-такой пользователь существует')
                flash('-такая страховка имеется в наличии')
                flash('-введенная дата корректна (не позже сегодня)')

    return render_template('settings_insurance.html', list_insurance=list_insurance, list_conf_users=list_conf_users,
                           list_personal_info=list_personal_info, list_date_end=list_date_end, today=today)


@app.route("/settings/users", methods=['POST', 'GET'])
@login_required
def settings_users():
    list_users = Users.query.all()
    return render_template('settings_users.html', list_users=list_users)


@app.route("/settings/delete_personal_info", methods=['POST', 'GET'])
@login_required
def settings_delete_personal_info():
    list_confirmed = []
    list_personal = UsersPersonalInfo.query.all()
    list_confirmed1 = UsersConfirmed.query.all()

    for i in range(len(list_personal)):
        flag = False
        if list_confirmed1:
            for j in range(len(list_confirmed1)):
                if list_personal[i].id == list_confirmed1[j].id_personal_info:
                    flag = True
                    break
        if not flag:
            list_confirmed.append(list_personal[i])
    list_users = []
    for i in list_confirmed:
        list_users.append(Users.query.filter_by(id=i.id_users_by).first().login)

    id_personal_info = request.form.get('id_personal_info')

    if request.method == 'POST':
        if id_personal_info:
            if UsersPersonalInfo.query.filter_by(id=id_personal_info).first() and \
                    not UsersConfirmed.query.filter_by(id_personal_info=id_personal_info).first():
                UsersPersonalInfo.query.filter_by(id=id_personal_info).delete()
                db.session.commit()
                return redirect(url_for('settings_delete_personal_info'))
            else:
                flash('Такой заявки нет!')
                flash('Либо вы пытаетесь удалить уже привязанную заявку к пользователю.')

    return render_template('settings_delete_personal_info.html', list_confirmed=list_confirmed, list_users=list_users)


@app.route("/settings/users_confirmed", methods=['POST', 'GET'])
@login_required
def settings_confirmed_users():
    list_confirmed = []
    list_personal = UsersPersonalInfo.query.all()
    list_confirmed1 = UsersConfirmed.query.all()

    for i in range(len(list_personal)):
        flag = False
        if list_confirmed1:
            for j in range(len(list_confirmed1)):
                if list_personal[i].id == list_confirmed1[j].id_personal_info:
                    flag = True
                    break
        if not flag:
            list_confirmed.append(list_personal[i])

    list_users = []
    for i in list_confirmed:
        list_users.append(Users.query.filter_by(id=i.id_users_by).first().login)

    list_insurance = Insurance.query.order_by('period').all()

    id_users = request.form.get('id_users')
    id_personal = request.form.get('id_personal')
    id_insurance = request.form.get('id_insurance')
    date_buy = request.form.get('date_buy')

    if request.method == 'POST':

        if id_users and id_personal and id_insurance and date_buy:

            date_buy = datetime.strptime(date_buy, '%Y-%m-%d')

            if date_buy <= datetime.today() and int(id_insurance) <= 5 and \
                    not UsersConfirmed.query.filter_by(id_personal_info=id_personal).first() and \
                    not UsersConfirmed.query.filter_by(id_users=id_users).first() and \
                    Users.query.filter_by(id=id_users).first() and \
                    UsersPersonalInfo.query.filter_by(id_users_by=id_users).first() and \
                    int(id_users) == UsersPersonalInfo.query.filter_by(id=id_personal).first().id_users_by:

                user_confirmed = UsersConfirmed(id_users=id_users, id_personal_info=id_personal,
                                                id_insurance=id_insurance,
                                                date_buy=date_buy)
                db.session.add(user_confirmed)
                db.session.commit()
                return redirect(url_for('settings'))
            else:
                flash('Проверьте корректность:')
                flash('-данная заявка актуальна (представлена выше)')
                flash('-заявка поступила от данного пользователя')
                flash('-указан корректный номер пользователя')
                flash('-такая страховка имеется в наличии')
                flash('-введена корректная дата (не позднее сегодняшнего дня)')

    return render_template('settings_confirmed_users.html', list_confirmed=list_confirmed, list_users=list_users,
                           list_insurance=list_insurance)


@app.route("/settings/flights", methods=['POST', 'GET'])
@login_required
def settings_flights():
    list_flights = Flights.query.all()
    list_airplane = []
    for i in list_flights:
        list_airplane.append(Airplane.query.filter_by(id=i.id_airplane).first())
    id_flights = request.form.get('id_flights')
    flag = request.form.get('flag')

    if request.method == "POST":
        if id_flights and flag:
            if int(id_flights) <= 20 and (flag == '0' or flag == '1' or flag == '2' or flag == '3'):
                rows = Flights.query.filter_by(id=id_flights).first()
                rows.flag = flag
                db.session.commit()
            else:
                flash('Проверьте корректность:')
                flash('-такой подъем существует')
                flash('-указан корректный статус борта')

    return render_template('settings_flights.html', list_flights=list_flights, list_airplane=list_airplane)


if __name__ == '__main__':
    app.run(debug=True, port=2022)
