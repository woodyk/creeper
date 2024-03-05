#!/usr/bin/env python3
#
# plugins/connection_pool.py

import asyncio

class ConnectionPool:
    def __init__(self, size=10):
        self.size = size
        self.connections = {i: None for i in range(size)}

    async def acquire(self):
        task = asyncio.create_task(self._acquire())
        conn = await task
        return conn

    async def release(self, conn):
        await self._release(conn)

    async def _acquire(self):
        for conn in self.connections.values():
            if conn is None:
                self.connections[next(iter(self.connections))] = asyncio.create_stream(readable=False, writable=False)
                return self.connections[next(iter(self.connections))]

        raise ValueError("No available connections.")

    async def _release(self, conn):
        index = list(self.connections).index(conn)
        del self.connections[index]
        await conn.drain()
        conn.close()
