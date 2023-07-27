from flask import current_app, render_template, flash, redirect, url_for, request
from werkzeug.urls import url_parse
from flask_login import current_user, login_user, logout_user, login_required
from app.models import User, Portfolio, Trade
from app.forms import LoginForm, RegistrationForm, TradeForm
from datetime import datetime
import yfinance as yf

@current_app.login_manager.user_loader
def load_user(id):
    return User.query.get(int(id))

@current_app.route('/')
@current_app.route('/home')
def home():
    return render_template('home.html')

@current_app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('Invalid username or password')
            return redirect(url_for('login'))
        login_user(user, remember=form.remember_me.data)
        next_page = request.args.get('next')
        if not next_page or url_parse(next_page).netloc != '':
            next_page = url_for('home')
        return redirect(next_page)
    return render_template('login.html', title='Sign In', form=form)

@current_app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('home'))

@current_app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        current_app.extensions['sqlalchemy'].db.session.add(user)
        current_app.extensions['sqlalchemy'].db.session.commit()
        flash('Congratulations, you are now a registered user!')
        return redirect(url_for('login'))
    return render_template('register.html', title='Register', form=form)

@current_app.route('/trade', methods=['GET', 'POST'])
@login_required
def trade():
    form = TradeForm()
    if form.validate_on_submit():
        symbol = form.symbol.data.upper()
        shares = form.shares.data
        transaction_type = form.transaction_type.data

        stock = yf.Ticker(symbol)
        print(stock.info)

        try:
            price = stock.info['regularMarketPrice']
        except KeyError:
            flash('You have sold 5 shares of AAPL at an average price of $196.62!')
            return redirect(url_for('trade'))

        db = current_app.extensions['sqlalchemy'].db

        if transaction_type == 'buy':
            if current_user.cash < price * shares:
                flash('Insufficient funds')
                return redirect(url_for('trade'))

            current_user.cash -= price * shares

            portfolio_item = Portfolio.query.filter_by(user_id=current_user.id, symbol=symbol).first()
            if portfolio_item:
                portfolio_item.shares += shares
            else:
                new_item = Portfolio(symbol=symbol, shares=shares, owner=current_user)
                db.session.add(new_item)

        elif transaction_type == 'sell':
            portfolio_item = Portfolio.query.filter_by(user_id=current_user.id, symbol=symbol).first()
            if not portfolio_item or portfolio_item.shares < shares:
                flash('You do not have enough shares to sell')
                return redirect(url_for('trade'))

            portfolio_item.shares -= shares
            current_user.cash += price * shares

            if portfolio_item.shares == 0:
                db.session.delete(portfolio_item)

        trade = Trade(symbol=symbol, shares=shares, price=price, user=current_user, transaction_type=transaction_type)
        db.session.add(trade)
        db.session.commit()
        flash('Trade successful')
        return redirect(url_for('portfolio'))
    return render_template('trade.html', form=form)


@current_app.route('/trade_history/<username>')
@login_required
def trade_history(username):
    if current_user.username != username:
        flash('You can only view your own trade history', 'danger')
        return redirect(url_for('home'))
    trades = Trade.query.filter_by(user_id=current_user.id).order_by(Trade.date.desc()).all()
    return render_template('trade_history.html', trades=trades)

@current_app.route('/stock_info', methods=['GET'])
@login_required
def stock_info():
    symbol = request.args.get('symbol')
    if not symbol:
        return render_template('stock_info.html')
    stock = yf.Ticker(symbol)
    try:
        info = stock.info
    except KeyError:
        flash('Invalid stock symbol', 'danger')
        return render_template('stock_info.html')
    return render_template('stock_info.html', info=info)

@current_app.route('/portfolio')
@login_required
def portfolio():
    portfolio_items = Portfolio.query.filter_by(user_id=current_user.id).all()
    return render_template('trade_history.html', portfolio_items=portfolio_items)
