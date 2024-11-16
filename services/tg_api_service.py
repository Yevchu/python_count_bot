from telegram import Bot

class TelegramAPI:
    def __init__(self, bot: Bot):
        self.bot = bot

    async def get_member_count(self, group_id: int) -> int:
        return await self.bot.get_chat_member_count(group_id)
    
    async def get_members(self, group_id: int) -> list:
        member_count = await self.get_member_count(group_id)
        members = []
        for i in range(member_count):
            members.append(await self.bot.get_chat_member(group_id, i))
        return members