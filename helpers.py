import csv
import datetime
import pytz
import requests
import subprocess
import urllib
import uuid
import requests
from flask import redirect, render_template, session
from functools import wraps
import yfinance as yf

api_key = "sk_fe623fe48b2146298aed76f537378995" # get your API key from https://iexcloud.io/

def get_name(ticker):
    url = f"https://cloud.iexapis.com/stable/stock/{ticker}/company?token={api_key}" # construct the API URL
    response = requests.get(url) # send a GET request to the API URL
    company_name = response.json()["companyName"] # get the company name from the JSON response
    return company_name

def get_name2(ticker):
    url = f"https://finance.google.com/finance?q={ticker}"
    res = requests.get(url)
    content = res.content.decode('utf-8')
    start_location = content.find('<title>') + len('<title>')
    end_location = content.find('</title>')
    title = content[start_location:end_location]
    company_name = title.split(':')[0]
    positionRemove = company_name.find('(')
    company_name=company_name[:positionRemove]
    return company_name
    # Output = 'Microsoft Corporation'
def apology(message, code=400):
    """Render message as an apology to user."""
    def escape(s):
        """
        Escape special characters.

        https://github.com/jacebrowning/memegen#special-characters
        """
        for old, new in [("-", "--"), (" ", "-"), ("_", "__"), ("?", "~q"),
                         ("%", "~p"), ("#", "~h"), ("/", "~s"), ("\"", "''")]:
            s = s.replace(old, new)
        return s
    return render_template("apology.html", top=code, bottom=escape(message)), code


def login_required(f):
    """
    Decorate routes to require login.

    http://flask.pocoo.org/docs/0.12/patterns/viewdecorators/
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function



def lookup(symbol):
    """Look up quote for symbol."""

    # Prepare API request
    symbol = symbol.upper()
    end = datetime.datetime.now(pytz.timezone("US/Eastern"))
    start = end - datetime.timedelta(days=7)

    # Yahoo Finance API
    url = (
        f"https://query1.finance.yahoo.com/v7/finance/download/{urllib.parse.quote_plus(symbol)}"
        f"?period1={int(start.timestamp())}"
        f"&period2={int(end.timestamp())}"
        f"&interval=1d&events=history&includeAdjustedClose=true"
    )

    # Query API
    try:
        response = requests.get(url, cookies={"session": str(uuid.uuid4())}, headers={"User-Agent": "python-requests", "Accept": "*/*"})
        response.raise_for_status()

        # CSV header: Date,Open,High,Low,Close,Adj Close,Volume
        quotes = list(csv.DictReader(response.content.decode("utf-8").splitlines()))
        quotes.reverse()
        price = round(float(quotes[0]["Adj Close"]), 2)
        name=get_name2(symbol)
        return {
            "name": name,
            "price": price,
            "symbol": symbol
        }
    except (requests.RequestException, ValueError, KeyError, IndexError):
        return None


def usd(value):
    """Format value as USD."""
    return f"${value:,.2f}"


def get_symbol(symbol):
    url = "http://d.yimg.com/autoc.finance.yahoo.com/autoc?query={}&region=1&lang=en".format(symbol)

    result = requests.get(url).json()

    for x in result['ResultSet']['Result']:
        if x['symbol'] == symbol:
            return x['name']

