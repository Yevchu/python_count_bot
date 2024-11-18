import redis.asyncio as redis 
import json
from typing import Optional, Set

class RedisCacheManager:
    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis_url = redis_url
        self.redis = None

    async def connect(self):
        self.redis = await redis.from_url(self.redis_url)

    async def close(self):
        if self.redis:
            await self.redis.close()

    async def get_group(self, group_id: int) -> Optional[dict]:
        group_data = await self.redis.get(f'group:{group_id}')
        if group_data:
            return json.loads(group_data)
        return None
    
    async def set_group(self, group_id: int, group_data: dict, ttl: int = 3600):
        await self.redis.set(f'group{group_id}', json.dumps(group_data), ex=ttl)
    
    async def add_user_to_group(self, group_id: int, user_id: int):
        key = f"group:{group_id}:users"
        await self.redis.sadd(key, user_id)
    
    async def get_user_to_group(self, group_id: int, user_id: int):
        key = f"group:{group_id}:users"
        return await self.redis.sismember(key, user_id)

    async def clear_group_cache(self, group_id: int):
        await self.redis.delete(f'group:{group_id}', f'group_users{group_id}')
    
    