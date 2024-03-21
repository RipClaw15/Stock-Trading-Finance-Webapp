import os
import plotly.express as px
import requests

from datetime import datetime, timedelta
from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")

# Make sure API key is set
#if not os.environ.get("API_KEY"):
 #   raise RuntimeError("API_KEY not set")


@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""
    money = db.execute("select cash from users where id = ?",session["user_id"])
    portfolio = db.execute("select * from portfolio where id = ?",session["user_id"])
    sum = db.execute("select sum(total) from portfolio where id = ?",session["user_id"])
    if sum[0]["sum(total)"] is not None:
        return render_template("index.html", portfolio = portfolio, sum = '%.2f' %sum[0]["sum(total)"], money = '%.2f' %money[0]['cash'])
    else :
        return render_template("index.html",money = '%.2f' %money[0]['cash'])

@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    if request.method == "POST":
        symbol = request.form.get("symbol")
        symbol = symbol.upper()
        shares = request.form.get("shares")

        # Ensure symbol and shares are provided
        if not symbol or not shares or not shares.isdigit() or int(shares) < 1:
            return apology("Invalid input", 400)

        quote = lookup(symbol)

        # Ensure the stock symbol is valid
        if quote is None:
            return apology("Stock not found", 400)

        # Calculate total cost
        total_cost = int(shares) * quote["price"]

        # Check if user has sufficient funds
        rows = db.execute("SELECT cash FROM users WHERE id = ?", session["user_id"])
        if rows[0]["cash"] < total_cost:
            return apology("Insufficient funds", 400)

        # Check if the stock is already in the portfolio
        portfolio_rows = db.execute("SELECT * FROM portfolio WHERE id = ? AND symbol = ?", session["user_id"], symbol)
        if portfolio_rows:
            # Update existing entry
            new_shares = int(shares) + portfolio_rows[0]['shares']
            new_total = new_shares * quote["price"]
            db.execute("UPDATE portfolio SET shares = ?, total = ?, transacted = ? WHERE id = ? AND symbol = ?",
                       new_shares, new_total, datetime.now(), session["user_id"], symbol)
        else:
            # Insert new entry
            db.execute("INSERT INTO portfolio (id, name, symbol, shares, price, total, transacted) VALUES (?, ?, ?, ?, ?, ?, ?)",
                       session["user_id"], quote["name"], symbol, int(shares), quote["price"], total_cost, datetime.now())

        # Update user's cash
        db.execute("UPDATE users SET cash = ? WHERE id = ?", rows[0]["cash"] - total_cost, session["user_id"])

        return redirect("/")
    else:
        return render_template("buy.html")


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    return apology("TODOhistory")


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 400)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 400)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 400)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""


    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        symbol = request.form.get("symbol")
        symbol = symbol.lower()
        quote = lookup(symbol)

        if not request.form.get("symbol"):

            return apology("Please enter a stock", 400)
        elif quote is None:

            return apology("Stock not found", 400)

        message="A share of " + quote["name"] +" ("+ quote["symbol"] +") "+ "costs $" +str(quote["price"])+"."

        base_url = f"https://api.tiingo.com/tiingo/daily/{symbol}/prices"

        # Your Tiingo API token
        api_token = "get your own"

        # Set the start date for the last 6 months
        start_date = (datetime.now() - timedelta(days=180)).strftime('%Y-%m-%d')

        # Make a request to the Tiingo API
        params = {'startDate': start_date, 'token': api_token}
        response = requests.get(base_url, params=params)
        print(params)
        # Check if the request was successful (status code 200)
        if response.status_code == 200:
            # Extract relevant data from the JSON response
            data = response.json()
            print("response status 200")
            # Extract dates and close prices
            dates = [entry['date'] for entry in data]
            close_prices = [entry['close'] for entry in data]

            # Create a Plotly figure
            fig = px.line(x=dates, y=close_prices, labels={"x": "Date", "y": "Close Price"}, title= symbol.upper() + " Stock Prices - Last 6 Months")

            # Convert the figure to a JSON string
            chart_json = fig.to_json()

            return render_template("quote.html", message = message, chart_json=chart_json, start_date = start_date)
        return render_template("quote.html", message = message)
    else:

        return render_template("quote.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 400)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 400)

        # Ensure confirm-password was submitted
        elif not request.form.get("confirmation"):
            return apology("must confirm the password", 400)

        # Ensure confirm-password is the same
        elif request.form.get("password") != request.form.get("confirmation"):

            return apology("must enter the same password twice", 400)

        elif len(db.execute("SELECT username FROM users WHERE username = ?",request.form.get("username"))) != 0:

            return apology("username already taken", 400)

        # Query database for username

        db.execute("insert into users (username, hash) VALUES(?, ?)",request.form.get("username"), generate_password_hash(request.form.get("password")))

        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("register.html")

    return apology("TODO")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""\

    if request.method == "POST":
        quote = lookup(request.form.get("symbol"))
        rows = db.execute("SELECT cash FROM users WHERE id = ?",session["user_id"])
        rowp = db.execute("SELECT * from portfolio where id = ? and symbol = ?", session["user_id"], request.form.get("symbol"))

        if int(request.form.get("shares")) > rowp[0]["shares"]:

            return apology("You don't have enough shares of this stock", 400)

        elif request.form.get("symbol") != rowp[0]["symbol"]:

            return apology("You don't have this kind of stock", 400)

        elif not request.form.get("shares"):

            return apology("Must provide quantity", 400)

        elif int(request.form.get("shares")) < 1:

            return apology("Must provide correct quantity", 400)

        if int(request.form.get("shares")) == rowp[0]["shares"]:

            db.execute("delete from portfolio where id = ? and symbol = ?",session["user_id"],request.form.get("symbol"))
            db.execute("update users set cash = ? where id = ?",int(request.form.get("shares")) * float(quote["price"]) + int(rows[0]['cash']),session["user_id"])
        elif  len(db.execute("SELECT symbol from portfolio where id = ? and symbol = ?", session["user_id"], request.form.get("symbol"))) != 0:
            db.execute("update portfolio set shares = ?, price = ?, total = ?, transacted = ? where id = ? and symbol = ?", int(rowp[0]['shares']) - int(request.form.get("shares")),
            float(quote["price"]), (int(rowp[0]['shares']) - int(request.form.get("shares"))) * float(quote["price"]), datetime.now(), session["user_id"], rowp[0]["symbol"])
            db.execute("update users set cash = ? where id = ?",int(request.form.get("shares")) * float(quote["price"]) + int(rows[0]['cash']),session["user_id"])
        else :
            db.execute("insert into portfolio (id, name, symbol, shares, price, total, transacted) VALUES(?, ?, ?, ?, ?, ?, ?)",
            session["user_id"], quote["name"], quote["symbol"], int(request.form.get("shares")), quote["price"],
            int(request.form.get("shares")) * float(quote["price"]), datetime.now())

        return redirect("/")
    else:

        return render_template("sell.html",portfolio = db.execute("select * from portfolio where id = ?",session["user_id"]))
