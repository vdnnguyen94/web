import os
from datetime import datetime
from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")

# Function to remove existing index
def remove_existing_index():
    db.execute("DROP INDEX IF EXISTS idx_username;")

# Function to create a new index for registration
def create_index_for_registration():
    db.execute("CREATE INDEX IF NOT EXISTS idx_username_register ON users (username);")
@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Buy shares of stock"""
    id=session.get("user_id")
    rows = db.execute("SELECT * FROM users WHERE id= ?", id)
    cash=rows[0]["cash"]
    if len(rows) != 1:
        return apology("invalid username and/or password", 400)
    stocks = db.execute("SELECT * FROM stocks WHERE user_id= ?",id)
    if request.method == "GET":
        return render_template("sell.html",cash=usd(cash),stocks=stocks)
    else:
        symbol=request.form.get("symbol")
        try:
            shares=float(request.form.get("shares"))
        except:
            error_message="INVALID DATA TYPE OF SHARES"
            return render_template("sell.html",cash=usd(cash),stocks=stocks,error_message=error_message)
        #Ensure symbol and numbers of shared
        if not symbol:
            error_message="Must provide a stock symbol"
            return render_template("sell.html",cash=usd(cash),stocks=stocks,error_message=error_message)
        if not shares:
            error_message="Must provide number of shares"
            return render_template("sell.html",cash=usd(cash),stocks=stocks,error_message=error_message)
        if shares - int(shares) > 0:
            error_message="hares must be a positive integer"
            return render_template("sell.html",cash=usd(cash),stocks=stocks,error_message=error_message)
        if not  (shares >= 1):
            error_message="Invalid Number of Shares"
            return render_template("sell.html",cash=usd(cash),stocks=stocks,error_message=error_message)
        symbols = lookup(symbol)
        if not (symbols):
            #return apology(symbols["name"] + " " + str(symbols["price"]) + str(symbols["symbol"]),403)
            error_message="Symbol Not Found"
            return render_template("sell.html",cash=usd(cash),stocks=stocks,error_message=error_message)
        else:
            price=symbols["price"]
            salevalues=round(price*shares,2)
            if(salevalues <= 0):
                return apology("INVALID MARKET PRICE, SYSTEM CANNOT PROCEED THE TRANSACTION", 400)
            else:
                stocks = db.execute("SELECT * FROM stocks WHERE user_id= ? AND symbol= ?",id,symbols["symbol"])
                if len(stocks) != 1:
                    error_message="There is no stock symbols in your account"
                    return render_template("sell.html",cash=usd(cash),stocks=stocks,error_message=error_message)
                elif len(stocks) == 1:
                    newshares=stocks[0]["shares"]-shares
                    if newshares < 0:
                        error_message="Your account doesn't have enough shares to sell"
                        return render_template("sell.html",cash=usd(cash),stocks=stocks,error_message=error_message)
                    db.execute("UPDATE stocks SET shares=? WHERE user_id= ? AND symbol= ?",newshares,id,symbols["symbol"])
                #update cash
                cash=cash+salevalues
                db.execute("UPDATE users SET cash=? WHERE id=?",cash,id)
                #delete row if shares = 0
                db.execute("DELETE FROM stocks WHERE user_id = ? AND shares = 0",id)
                transtime=datetime.now()
                db.execute("INSERT INTO transactionx (users_id,symbol,name,shares,share_value,totalvalues,type,trans_time) VALUES (?,?,?,?,?,?,?,datetime(?))",id,symbols["symbol"],symbols["name"],shares,price,salevalues,"Sell",transtime)
                symbols["price"]=usd(symbols["price"])
                stocks = db.execute("SELECT * FROM stocks WHERE user_id= ?",id)
                return render_template("sell.html", stocks=stocks, symbols=symbols, cash=usd(cash), shares=shares, salevalues=usd(salevalues))

@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""
    id=session.get("user_id")
    rows = db.execute("SELECT * FROM users WHERE id= ?", id)
    if len(rows) != 1:
        return apology("invalid username and/or password", 400)
    cash=rows[0]["cash"]
    stocks = db.execute("SELECT * FROM stocks WHERE user_id= ?",id)
    totalassets=cash
    totalvalues=0
    totalvalue=0
    if stocks:
        for stock in stocks:
            symbol=lookup(stock["symbol"])
            if symbol is not None:
                totalvalue=stock["shares"]*symbol["price"]
                totalvalues = totalvalues + totalvalue
                stock.update({"price":usd(symbol["price"])})
                stock.update({"totalvalue":usd(totalvalue)})
        totalassets=totalassets+totalvalues
        totalvalues=usd(totalvalues)
    return render_template("portfolio.html",cash=usd(cash), stocks=stocks, totalassets=usd(totalassets), totalvalues=totalvalues)


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    id=session.get("user_id")
    rows = db.execute("SELECT * FROM users WHERE id= ?", id)
    cash=rows[0]["cash"]
    if len(rows) != 1:
        return apology("invalid username and/or password", 400)
    if request.method == "GET":
        return render_template("buy.html",cash=usd(cash))
    else:
        symbol=request.form.get("symbol")
        try:
            shares=float(request.form.get("shares"))
        except:
            error_message="INVALID DATA TYPE of SHARES"
            return render_template("buy.html",cash=usd(cash),error_message=error_message)
        id=session.get("user_id")
        #Ensure symbol and numbers of shared
        if not symbol:
            error_message="Must provide stock symbol"
            return render_template("buy.html",cash=usd(cash),error_message=error_message)
        if not shares:
            error_message="Must provide number of shares"
            return render_template("buy.html",cash=usd(cash),error_message=error_message)
        if shares - round(shares) != 0:
            error_message="Invalid Number of Shares"
            return render_template("buy.html",cash=usd(cash),error_message=error_message)
        if shares < 0:
            error_message="Shares cannot be less than 0"
            return render_template("buy.html",cash=usd(cash),error_message=error_message)
        symbols = lookup(symbol)
        if not (symbols):
            #return apology(symbols["name"] + " " + str(symbols["price"]) + str(symbols["symbol"]),403)
            error_message=symbol + " not found"
            return render_template("buy.html",cash=usd(cash),error_message=error_message)
        else:
            price=float(symbols["price"])
            shares=float(shares)
            totalcost=(round(price*shares,2))
            if(totalcost > cash):
                error_message="INSUFFICIENT FUND"
                return render_template("buy.html",cash=usd(cash),error_message=error_message)
            else:
                cash=cash-totalcost
                stocks = db.execute("SELECT * FROM stocks WHERE user_id= ? AND symbol= ?",id,symbols["symbol"])
                if len(stocks) == 1:
                    newshares=stocks[0]["shares"]+shares
                    db.execute("UPDATE stocks SET shares=? WHERE user_id= ? AND symbol= ?",newshares,id,symbols["symbol"])
                else:
                    db.execute("INSERT INTO stocks (symbol,user_id,name,shares) VALUES (?,?,?,?)",symbols["symbol"],id,symbols["name"],shares)
                #update cash
                db.execute("UPDATE users SET cash=? WHERE id=?",cash,id)
                transtime=datetime.now()
                db.execute("INSERT INTO transactionx (users_id,symbol,name,shares,share_value,totalvalues,type,trans_time) VALUES (?,?,?,?,?,?,?,datetime(?))",id,symbols["symbol"],symbols["name"],shares,price,totalcost,"Buy",transtime)
                symbols["price"]=usd(symbols["price"])
                return render_template("buy.html", symbols=symbols,cash=usd(cash),shares=shares,totalcost=usd(totalcost))



@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    id=session.get("user_id")
    transactions = db.execute("SELECT * FROM transactionx WHERE users_id= ?",id)
    rows = db.execute("SELECT * FROM users WHERE id= ?", id)
    if len(rows) != 1:
        return apology("invalid username and/or password", 400)
    cash=rows[0]["cash"]
    return render_template("history.html",transactions=transactions,cash=usd(cash))



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
    if request.method == "POST":
        symbol = request.form.get("symbol")
        # Ensure SYMBOL was submitted
        if not request.form.get("symbol"):
            error_message=symbol + "Must Provide a Stock Symbol"
            return render_template("quote.html", error_message=error_message)
        symbols = lookup(symbol)
        if not (symbols):
            error_message=symbol + " not found"
            return render_template("quote.html", error_message=error_message)
        else:
            symbols["price"]=usd(symbols["price"])
            return render_template("quote.html", symbols=symbols)

    else:
        return render_template("quote.html")

@app.route("/search")
def search():
    q = request.args.get("q")
    if q:
        symbols = lookup(q)
        if (symbols):
            symbols["price"]=usd(symbols["price"])
    else:
        error_message= "Symbol not found"
        return render_template("search.html", error_message=error_message)

    return render_template("search.html", symbols=symbols)
@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        username=request.form.get("username")
        password=request.form.get("password")
        confirmation=request.form.get("confirmation")

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 400)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 400)
        # Ensure password was submitted
        elif not request.form.get("confirmation"):
            return apology("must provide confirmation password", 400)
        elif not (password == confirmation):
            return apology("passwords do not match", 400)


        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = ?", username)
        # Ensure username does not exist
        if len(rows) >= 1:
            return apology("username already exists", 400)
        # Remove existing index
        remove_existing_index()
        # INSERT table into USER table & generate hash password
        db.execute("INSERT INTO users (username, hash) VALUES (?, ?)",username,generate_password_hash(password,method='pbkdf2', salt_length=16))
        # Create a new index for registration
        create_index_for_registration()
        # Redirect user to login page
        return redirect("/login")
    else:
        return render_template("register.html")






