from flask import Flask, request
from structs import ShardStatus, ShardNode, ShardPool
from exceptions import ShardUUIDMismatchError, MissingShardError

app = Flask(__name__)
pool = ShardPool(max_size=2)


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
    finally:
        pool.cull()
    return "", 200


@app.get("/status")
def get_status():
    pool.cull()
    if "application/json" in request.accept_mimetypes:
        nodes = pool.nodes_as_dict()
        resp_dict = {
            "nodes": nodes,
            "summary": pool.summary().value,
            "size": pool.max_size
        }
        return resp_dict, 200
    else:
        # TODO return http version
        return "<p>ok</p>", 200


@app.post("/join")
def join_pool():
    pool.cull()
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


@app.post("/leave")
def leave_pool():
    json = request.json
    if "uuid" not in json:
        return "UUID not specified", 400
    if "shard_id" not in json:
        return "shard ID not specified", 400
    shard = pool.shards[json["shard_id"]]
    if shard is None:
        return "slot already empty", 409
    if shard.uuid != json["uuid"]:
        return "uuid mismatch", 403
    pool.free(json["shard_id"])
    pool.cull()
    return "", 200
