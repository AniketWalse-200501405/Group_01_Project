from flask import Flask, render_template, request
import yfinance as yf
import time
import sqlite3
import threading

app = Flask(__name__)
db_path = "stocks.db"

def create_table():
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS stocks
                 (ticker text, date text, open real, close real)''')
    conn.commit()
    conn.close()

def insert_data(ticker_data):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    for data in ticker_data:
        c.execute("INSERT INTO stocks (ticker, date, open, close) VALUES (?, ?, ?, ?)",
                  (data['ticker'], data['date'], data['open'], data['close']))
    conn.commit()
    conn.close()

def fetch_data(ticker, start_date, end_date):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("SELECT date, open, close FROM stocks WHERE ticker = ? AND date BETWEEN ? AND ?", (ticker, start_date, end_date))
    data = c.fetchall()
    conn.close()
    return [{"date": row[0], "open": row[1], "close": row[2]} for row in data]

def batch_process():
    while True:
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        c.execute("SELECT DISTINCT ticker FROM stocks")
        tickers = [row[0] for row in c.fetchall()]
        conn.close()

        for ticker in tickers:
            ticker_data = fetch_data(ticker, "2000-01-01", "2030-12-31")

            if not ticker_data:
                ticker_data = ['AAPL']
                ticker_obj = yf.Ticker(ticker)
                hist = ticker_obj.history(start="2000-01-01", end="2030-12-31")
                for index, row in hist.iterrows():
                    ticker_data.append({"ticker": ticker, "date": index.strftime("%Y-%m-%d"), "open": row["Open"], "close": row["Close"]})
                insert_data(ticker_data)
        time.sleep(86400)

@app.route("/", methods=["GET", "POST"])
def home():
    # Get the ticker and date range from the form or use default values
    if request.method == "POST":
        ticker = request.form["ticker"]
        start_date = request.form["start_date"]
        end_date = request.form["end_date"]
    else:
        ticker = "AAPL"
        start_date = "2010-01-01"
        end_date = "2023-04-16"

    # Check if data is already in the database
    ticker_data = fetch_data(ticker, start_date, end_date)

    if not ticker_data:
        # Fetch the data for the specified ticker and date range from Yahoo Finance API
        ticker_data = []
        ticker_obj = yf.Ticker(ticker)
        hist = ticker_obj.history(start=start_date, end=end_date)
        for index, row in hist.iterrows():
            ticker_data.append({"ticker": ticker, "date": index.strftime("%Y-%m-%d"), "open": row["Open"], "close": row["Close"]})
        # Insert the data into the database
        insert_data(ticker_data)

    # Render the template with the data
    return render_template("index.html", ticker=ticker, start_date=start_date, end_date=end_date, data=ticker_data)
    

if __name__ == "__main__":
    create_table()
    threading.Thread(target=batch_process).start()
    app.run(debug=True)
