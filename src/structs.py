import time
from enum import Enum
from dataclasses import dataclass


class ShardStatus(Enum):
    ONLINE = 1
    OFFLINE = 2
    UNKNOWN = 3


@dataclass
class ShardNode:
    uuid: str
    origin: str
    shard_id: int
    last_seen: float = -1
    version: str = None


class ShardPool:
    max_size: int
    shards: list[ShardNode]
    offline_timeout: int

    def __init__(self, max_size: int, offline_timeout: int = 30):
        self.max_size = max_size
        self.offline_timeout = offline_timeout
        self.shards = [None for _ in range(max_size)]

    def request(self) -> int:
        """
        Request a free shard ID.
        :return: -1 if no shard slots are available, otherwise, the shard slot.
        """
        for index, shard in enumerate(self.shards):
            if shard is None or self.status(index) != ShardStatus.ONLINE:
                return index

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
            # TODO raise exception
            return
        if shard.uuid != uuid:
            # TODO raise exception
            return
        shard.last_seen = time.time()

    def status(self, shard_id: int, uuid: str = None) -> ShardStatus:
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
            raise RuntimeError("shard UUID is not what was expected")

        if shard.last_seen < 0:
            return ShardStatus.UNKNOWN

        return ShardStatus.ONLINE if time.time() - shard.last_seen < self.offline_timeout else ShardStatus.OFFLINE
