from flask import Flask
from structs import ShardStatus, ShardNode, ShardPool

app = Flask(__name__)

pool = ShardPool(5)

@app.get("/status")
def get_status():
    return "", 200
