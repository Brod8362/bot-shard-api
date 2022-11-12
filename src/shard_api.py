from flask import Flask

app = Flask(__name__)


@app.get("/status")
def get_status():
    return "", 200
