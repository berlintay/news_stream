# rss.py

from flask import Flask, jsonify

app = Flask(__name__)

@app.route('/')
def index():
    return "RSS Scraper is running!"

@app.route('/scrape')
def scrape():
    # Implement your scraping logic here
    return jsonify({"message": "Scraping completed!"})

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
