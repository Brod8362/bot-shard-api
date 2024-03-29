import time
from enum import Enum
from dataclasses import dataclass
import exceptions


class ShardStatus(Enum):
    ONLINE = "online"
    OFFLINE = "offline"
    UNKNOWN = "unknown"


class PoolStatus(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    OFFLINE = "offline"
    UNKNOWN = "unknown"


@dataclass
class ShardNode:
    uuid: str
    origin: str
    shard_id: int
    last_seen: float = -1
    version: str = None

    def as_dict(self, pool) -> dict[str, any]:
        return {
            "uuid": self.uuid,
            "origin": self.origin,
            "shard_id": self.shard_id,
            "last_seen": self.last_seen,
            "version": self.version,
            "status": pool.node_status(self.shard_id).value
        }


class ShardPool:
    max_size: int
    shards: list[ShardNode]
    offline_timeout: int
    evict_timeout: int

    def __init__(self, max_size: int, offline_timeout: int = 30, evict_timeout: int = 60):
        self.max_size = max_size
        self.offline_timeout = offline_timeout
        self.evict_timeout = evict_timeout
        self.shards = [None for _ in range(max_size)]

    def request(self) -> int:
        """
        Request a free shard ID.
        :return: -1 if no shard slots are available, otherwise, the shard slot.
        """
        # TODO: have a uuid check?
        for index, shard in enumerate(self.shards):
            if shard is None:
                return index
        return -1

    def allocate(self, shard_id: int, uuid: str, origin: str, version: str) -> None:
        """
        Allocate a given node to a shard id.
        :param shard_id: ID/index to allocate
        :param uuid: UUID of the node
        :param origin: Origin IP address of the node
        :param version: Version the node is running
        :return:
        """
        if shard_id < 0 or shard_id >= self.max_size:
            raise RuntimeError("illegal shard ID")
        if self.shards[shard_id] is not None:
            raise RuntimeError("shard ID already in use")
        self.shards[shard_id] = ShardNode(uuid=uuid,
                                          origin=origin,
                                          shard_id=shard_id,
                                          last_seen=time.time(),
                                          version=version)

    def free(self, shard_id: int):
        """
        Free a given shard, emptying the slot and allowing a new shard to take it's place.
        :param shard_id: Shard ID to free
        :return: None
        """
        self.shards[shard_id] = None

    def update_seen(self, shard_id: int, uuid: str):
        """
        Update the last seem time of a shard.
        :param shard_id: Shard ID to update
        :param uuid: UUID of the shard. Must match the shard ID stored in the pool
        :return: None
        """
        shard: ShardNode = self.shards[shard_id]
        if shard is None:
            raise exceptions.MissingShardError()
        if shard.uuid != uuid:
            raise exceptions.ShardUUIDMismatchError()
        shard.last_seen = time.time()

    def node_status(self, shard_id: int, uuid: str = None) -> ShardStatus:
        """
        Get the status of the given shard ID.
        :param shard_id: Shard ID to check status of
        :param uuid: Specify to check UUID. If the UUID does not match, a RuntimeError will be raised.
        :return: status of the shard
        """
        shard: ShardNode = self.shards[shard_id]
        if shard is None:
            return ShardStatus.UNKNOWN

        if uuid is not None and shard.uuid != uuid:
            raise exceptions.ShardUUIDMismatchError()

        if shard.last_seen < 0:
            return ShardStatus.UNKNOWN

        return ShardStatus.ONLINE if time.time() - shard.last_seen < self.offline_timeout else ShardStatus.OFFLINE

    def nodes_as_dict(self):
        return list(map(lambda node: None if node is None else node.as_dict(self), self.shards))

    def cull(self):
        current_time = time.time()
        for index, shard in enumerate(self.shards):
            if shard is not None and current_time - shard.last_seen > self.evict_timeout:
                # cull shards that are considered dead
                self.shards[index] = None

    def summary(self):
        num_unavailable = 0
        for index, shard in enumerate(self.shards):
            if shard is None or self.node_status(shard_id=index) != ShardStatus.ONLINE:
                num_unavailable += 1
        if num_unavailable == 0:
            return PoolStatus.HEALTHY
        elif 0 < num_unavailable < self.max_size:
            return PoolStatus.DEGRADED
        elif num_unavailable == self.max_size:
            return PoolStatus.OFFLINE
        else:
            return PoolStatus.UNKNOWN
