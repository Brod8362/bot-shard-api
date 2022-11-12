from flask import Flask, request
from structs import ShardStatus, ShardNode, ShardPool
from exceptions import ShardUUIDMismatchError, MissingShardError

app = Flask(__name__)
pool = ShardPool(2)


@app.post("/ping")
def shard_ping():
    json = request.json
    if "shard_id" not in json:
        return "shard ID not specified", 400
    if "uuid" not in json:
        return "UUID not specified", 400

    try:
        pool.update_seen(json["shard_id"], json["uuid"])
    except IndexError:
        return "shard ID out of bounds", 403
    except MissingShardError:
        return "no shard allocated for given ID", 403
    except ShardUUIDMismatchError:
        return "UUID does not match allocated", 409
    return "", 200


@app.get("/status")
def get_status():
    if "application/json" in request.accept_mimetypes:
        return pool.nodes_as_dict(), 200
    else:
        # TODO return http version
        return "<p>ok</p>", 200


@app.post("/join")
def join_pool():
    json = request.json
    if "uuid" not in json:
        return "UUID not specified", 400
    if "version" not in json:
        return "version not specified", 400
    slot = pool.request()
    if slot == -1:
        return "pool full", 409
    pool.allocate(shard_id=slot, uuid=json["uuid"], origin=request.origin, version=json["version"])
    response = {
        "shard_id": slot,
        "max_shards": pool.max_size
    }
    return response, 200
