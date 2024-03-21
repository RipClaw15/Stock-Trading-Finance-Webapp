import csv
import datetime
import pytz
import requests
import subprocess
import urllib
import uuid
import json

from flask import redirect, render_template, session
from functools import wraps


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
    symbol = symbol.lower()
    end = datetime.datetime.now(pytz.timezone("US/Eastern"))
    start = end - datetime.timedelta(days=7)

    # Tiingo API base URL
    base_url = "https://api.tiingo.com/tiingo/daily/{}"

    # Your Tiingo API token
    api_token = "2e458eff1fc1371dd111fc9362670fd4b7731d23"

    # Tiingo API URLs
    urlprice = base_url.format(f"{symbol}/prices?token={api_token}")

    urlsymbol = base_url.format(f"{symbol}?token={api_token}")


    print(urlsymbol)
    print(urlprice)

    # Query API for price information
    try:
        responseprice = requests.get(urlprice)
        responseprice.raise_for_status()
        json_responseprice = responseprice.json()
        first_data_point = json_responseprice[0]
        close_price = first_data_point.get("close")
        print("Close Price:", close_price)
    except (requests.RequestException, ValueError, KeyError, IndexError) as e:
        print("Error fetching price information:", e)
        return None

    # Query API for symbol information
    try:
        responsesymbol = requests.get(urlsymbol)
        responsesymbol.raise_for_status()
        json_responsesymbol = responsesymbol.json()

        # Check if the list is not empty before accessing its elements

        symbol_name = json_responsesymbol.get("name")
        print("Symbol Name:", symbol_name)


    except requests.RequestException as e:
        print("Error fetching symbol information:", e)
        return None
    except ValueError as e:
        print("Error decoding JSON response:", e)
        return None
    except KeyError as e:
        print("Error accessing key in JSON response:", e)
        return None
    except IndexError as e:
        print("Error accessing index in JSON response:", e)
        return None


    return {
        "name": symbol_name,
        "price": close_price,
        "symbol": symbol.upper()
    }


def usd(value):
    """Format value as USD."""
    return f"${value:,.2f}"
