from flask import Flask, render_template, request
import matplotlib.pyplot as plt
import base64
from io import BytesIO
import math
import numpy as np
# import requests
# import json
# from bs4 import BeautifulSoup

app = Flask(__name__)


@app.route("/")
def home():
    return render_template('home.html')


@app.route("/auto")
def login_signup():
    return render_template('login_signup.html')


@app.route("/flights")
def flights():
    return render_template('flights.html')


@app.route("/result", methods=['POST'])
def result():

    # if request.method == 'POST':

    return render_template('result.html')


if __name__ == '__main__':
    app.run(debug=True, port=3000)