from flask import Flask, render_template

app = Flask(__name__)

@app.route("/")
def index():
    return render_template('index.html')

@app.route("/publications")
def publications():
    return render_template('publications.html')

@app.route("/cv")
def cv():
    return render_template('cv.html')

@app.route("/algo")
def algo():
    return render_template('algo.html')
