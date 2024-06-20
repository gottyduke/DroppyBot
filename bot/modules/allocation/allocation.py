from typing import Optional
import common.config as config
import common.helper as helper
import discord
import os

from .models.usage import Usage
from common.exception import DroppyBotError
from common.cog import DroppyCog
from discord.ext import commands
from datetime import datetime, timezone, timedelta


class DroppyAllocationManager(DroppyCog):
    def __init__(self):
        self.usage: dict[str, list[Usage]] = self.load_usage()

    def load_usage(self):
        usage_path = os.path.join(self.cwd, self.config.bot.usage_path)
        flat_json = config.load_json(usage_path)
        usage = {a: [Usage(**u) for u in us] for a, us in flat_json.items()}

        for usages in usage.values():
            for stat in usages:
                stat.cycle = stat.cycle.replace(tzinfo=timezone.utc)
        return usage

    def save_usage(self):
        usage_path = os.path.join(self.cwd, self.config.bot.usage_path)
        flat_json = {a: [u.model_dump() for u in us] for a, us in self.usage.items()}
        config.save_json(usage_path, flat_json)

    def set_allocation(self, action_type: str, new_limit: float):
        """
        Temporarily set a limit for an action

        Only valid through this session
        """

        limit = helper.first_if(
            self.config.allocations, lambda a: a.action == action_type
        )
        if limit:
            limit.allocated = new_limit

    def get_allocation(self, action_type: str):
        """
        Query the allocated limit for an action
        """

        limit = helper.first_if(
            self.config.allocations, lambda a: a.action == action_type
        )
        return limit if limit else None

    def get_user_stat(self, user_id: int, action_type: str):
        usages = self.usage.setdefault(action_type, [])
        return helper.first_if(usages, lambda u: u.user_id == user_id)

    def get_action_stat(self, action_type: str):
        """
        Tally an allocated action
        """
        allocation = self.get_allocation(action_type)
        if not allocation:
            return 0
        return sum([u.used for u in self.usage.setdefault(action_type, [])])

    def get_cycle_remain(self, user_id: int, action_type: str):
        allocation = self.get_allocation(action_type)
        user_stat = self.get_user_stat(user_id, action_type)

        cycle_left = 0
        if allocation and user_stat:
            now = datetime.now(timezone.utc)
            reset_interval = timedelta(days=allocation.reset_interval)
            cycle_spent = now - user_stat.cycle
            cycle_left = (reset_interval - cycle_spent).days
        return cycle_left

    def cycle_reset(self, user: discord.User, action_type: str):
        if action_type not in [a.action for a in self.config.allocations]:
            return

        now = datetime.now(timezone.utc)
        user_stat = self.get_user_stat(user.id, action_type)
        if user_stat:
            user_stat.used = 0.0
            user_stat.cycle = now

    def check_limit(self, user: discord.User, action_type: str):
        """
        Whether an action from an user is allowed to execute

        Returns 0 if not limited, else return days left till reset
        """

        # dev get a free use
        if user.bot or str(user.id) == os.environ["DEV_ID"]:
            return 0

        # not an allocated resource
        if action_type not in [a.action for a in self.config.allocations]:
            return 0

        user_stat = self.get_user_stat(user.id, action_type)
        # first time user
        if not user_stat:
            return 0

        allocation = self.get_allocation(action_type)
        # free resource
        if (
            not allocation
            or allocation.allocated_user < 0.0
            or allocation.allocated_pool < 0.0
        ):
            return 0

        cycle_remain = self.get_cycle_remain(user.id, action_type)
        if cycle_remain < 0:
            self.cycle_reset(user, action_type)
            cycle_remain = 0

        shared_pool = self.get_action_stat(action_type)
        if shared_pool > allocation.allocated_pool:
            return cycle_remain

        if user_stat < allocation.allocated_user:
            return 0
        else:
            return cycle_remain

    def commit(self, user: discord.User, action_type: str, usage: float = 1.0):
        """
        Commit the user's usage for an action
        """

        if not isinstance(usage, int) and not isinstance(usage, float):
            raise DroppyBotError("Can't commit with non-numeric value")

        usages = self.usage.setdefault(action_type, [])

        now = datetime.now(timezone.utc)
        user_stat = self.get_user_stat(user.id, action_type)

        if not user_stat:
            usages.append(Usage(user_id=user.id, used=0.0, count=0, cycle=now))
            user_stat = usages[-1]

        user_stat.used += usage
        user_stat.count += 1
        self.save_usage()

    async def get_usage_detail(self, usage: Usage, action_type: str):
        allocation = self.get_allocation(action_type)
        remain = self.get_cycle_remain(usage.user_id, action_type)
        detail = f"- count: {usage.count:,}\n"
        detail += f"- usage: {usage.used:,} / {allocation.allocated_user:,}\n"
        detail += f"- cycle: {usage.cycle}\n"
        detail += f"- reset: {remain} / {allocation.reset_interval}"
        return detail

    async def as_action_embed(self, action_type: str):
        """
        Generate embed informations about an action's allocation usage
        """

        allocation = self.get_allocation(action_type)
        tally = self.get_action_stat(action_type)

        details = []
        deleter = []
        for usage in self.usage.setdefault(action_type, []):
            try:
                user = await self.bot.fetch_user(usage.user_id)
                details.append((user, await self.get_usage_detail(usage, action_type)))
            except:
                deleter.append(usage)
                continue

        self.usage[action_type] = [
            u for u in self.usage[action_type] if u not in deleter
        ]

        embed = helper.as_embed("")
        for user, stat in details:
            embed.add_field(
                name=f"{user.display_name} # {user.id}", value=stat, inline=True
            )

        embed.title = f"{action_type} usage"
        embed.description = f"- user allocated: {allocation.allocated_user:,}\n"
        embed.description += f"- pool allocated: {allocation.allocated_pool:,}\n"
        embed.description += f"- pool used: {tally:,}\n"
        embed.description += f"- cycle reset: {allocation.reset_interval}\n"

        return embed

    async def as_user_embed(self, user_id: int):
        """
        Generate user information for all allocations
        """

        user = await self.bot.fetch_user(user_id)
        embed = helper.as_embed("", user)
        for action in self.usage.keys():
            usage = self.get_user_stat(user_id, action)
            if not usage:
                continue

            embed.add_field(
                name=action,
                value=await self.get_usage_detail(usage, action),
                inline=False,
            )
        return embed

    @commands.command()
    @commands.check(DroppyCog.is_dev)
    @DroppyCog.failsafe_ref(force_ephemeral=False)
    async def allocset(self, ctx: commands.Context, *, details: Optional[str]):
        pass

    @commands.command()
    @commands.check(DroppyCog.is_dev)
    @helper.sanitize
    @DroppyCog.failsafe_ref()
    async def allocget(self, ctx: commands.Context, *, details: Optional[str]):
        ref = await self.get_ctx_ref(ctx)

        if not details:
            embeds = [await self.as_action_embed(a) for a in self.usage.keys()]
            await ref.edit(embeds=embeds)
            return

        if details.isnumeric():
            await ref.edit(embed=await self.as_user_embed(int(details)))
            return

        await ref.edit(embed=await self.as_action_embed(details))
