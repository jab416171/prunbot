import discord
from discord import option
from discord.ext import commands, tasks
from discord.commands import  slash_command
import aiohttp
import os
import sqlalchemy
from sqlalchemy import text, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.orm import sessionmaker
from google.cloud import storage
from datetime import datetime, timedelta
from models import *

class SimpleCog(commands.Cog):
    is_running = False
    def __init__(self, bot):
        self.bot = bot

    apikey = os.environ['PRUN_APIKEY']
    # inventory_base_url = f'https://rest.fnar.net/csv/inventory?apikey={apikey}&username=USERNAME'
    warehouses_url = 'https://rest.fnar.net/sites/warehouses/USERNAME'
    inventory_url = 'https://rest.fnar.net/storage/USERNAME/ID'


    async def save(self, item, bot=None, engine=None):
        if not engine:
            if bot:
                engine = await bot.db.getEngine()
            else:
                raise Exception("You must provide either a bot or an engine")
        async_session = sessionmaker(
            engine, expire_on_commit=False, class_=AsyncSession
        )
        async with async_session() as session:
            async with session.begin():
                session.add(item)
                await session.commit()

    async def delete(self, item, bot=None, engine=None):
        if not engine:
            if bot:
                engine = await bot.db.getEngine()
            else:
                raise Exception("You must provide either a bot or an engine")
        async_session = sessionmaker(
            engine, expire_on_commit=False, class_=AsyncSession
        )
        async with async_session() as session:
            async with session.begin():
                await session.delete(item)
                # make_transient(item)
                await session.commit()

    @commands.Cog.listener()
    async def on_ready(self):
        try:
            self.update_storefronts_timer.start()
            self.backup_db_timer.start()
            self.update_inventory_timer.start()
        except Exception as e:
            print(f"Error starting tasks: {e}")
            self.update_storefronts_timer.restart()
            self.backup_db_timer.restart()
            self.update_inventory_timer.restart()
        if not self.is_running:
            await self.download_db()
            self.is_running = True
        print(f"Logged in as {self.bot.user.name} - {self.bot.user.id}")

    async def download_db(self):
        client = storage.Client()
        bucket = client.bucket('discord_bots_db_backup')
        blobs = list(bucket.list_blobs(prefix=''))
        for blob in blobs:
            if blob.name == self.bot.db.dbname:
                blob.download_to_filename(self.bot.db.dbname)
                print(f"Downloaded {blob.name}")
                break
        else:
            print(f"File {self.bot.db.dbname} not found in bucket {bucket.name}")
            return

    @tasks.loop(minutes=10)
    async def update_storefronts_timer(self):
        print("Updating storefronts")
        for guild in self.bot.guilds:
            await self.update_storefronts(guild)

    @tasks.loop(minutes=10)
    async def update_inventory_timer(self):

        print("Updating inventory")
        try:
            users = await self.get_prun_users(None)
            users_ids = {}
            engine = await self.bot.db.getEngine()
            async with engine.begin() as conn:
                for user in users:
                        c = await conn.execute(text("select id from users where prun_user=:prun_user"),
                                            [{"prun_user": user}]
                                            )
                        user_id = c.fetchone()
                        if user_id:
                            users_ids[user] = user_id[0]
                for user, user_id in users_ids.items():
                    url = self.warehouses_url.replace("USERNAME", user)
                    headers = {
                        "accept": "application/json",
                        "Authorization": self.apikey
                    }
                    async with aiohttp.ClientSession() as session:
                        async with session.get(url, headers=headers) as response:
                            warehouses = await response.json()
                            for warehouse in warehouses:
                                warehouse_id = warehouse['WarehouseId']
                                store_id = warehouse['StoreId']
                                location_name = warehouse['LocationNaturalId']
                                warehouse_timestamp = warehouse['Timestamp']
                                # 2025-04-26T02:27:13.72626
                                warehouse_timestamp = datetime.strptime(warehouse_timestamp, "%Y-%m-%dT%H:%M:%S.%f")
                                url = self.inventory_url.replace("USERNAME", user).replace("ID", store_id)
                                async with session.get(url, headers=headers) as response:
                                    inventory = await response.json()
                                    for item in inventory['StorageItems']:
                                        item_ticker = item['MaterialTicker']
                                        item_amount = item['MaterialAmount']
                                        item_location = location_name
                                        item_weight = item['MaterialWeight']
                                        item_volume = item['MaterialVolume']
                                        item_value = item['MaterialValue']
                                        item_value_currency = item['MaterialValueCurrency']
                                        inventory = Inventory(
                                            user_id=user_id,
                                            item_ticker=item_ticker,
                                            item_location=item_location,
                                            item_quantity=item_amount,
                                            item_age=warehouse_timestamp
                                        )
                                        inventory_existing = None
                                        inventory_existing = await conn.execute(
                                            sqlalchemy.select(Inventory).where(
                                                Inventory.user_id == user_id,
                                                Inventory.item_ticker == item_ticker,
                                                Inventory.item_location == item_location
                                            )
                                        )
                                        inventory_existing = list(inventory_existing.all())
                                        # print(inventory_existing)
                                        if len(inventory_existing) > 1:
                                            raise Exception("more than one inventory item found")
                                        if inventory_existing and len(inventory_existing) > 0:
                                            inventory.id = inventory_existing[0].id
                                            try:
                                                stmt = update(Inventory).where(
                                                    Inventory.id == inventory.id,
                                                    Inventory.user_id == user_id,
                                                    Inventory.item_ticker == item_ticker,
                                                    Inventory.item_location == item_location
                                                ).values(
                                                    item_quantity=item_amount,
                                                    item_age=warehouse_timestamp
                                                )
                                                await conn.execute(stmt)
                                            except sqlalchemy.exc.IntegrityError:
                                                print(f"Item {item_ticker} already exists in inventory")
                                                continue
                                        else:
                                            try:
                                                await self.save(inventory, engine=engine)
                                            except sqlalchemy.exc.IntegrityError:
                                                print(f"Item {item_ticker} already exists in inventory")
                                                continue
            self.backup_db()
        except Exception as e:
            print(f"Error updating inventory: {e}")
            raise e

    @tasks.loop(minutes=60)
    async def backup_db_timer(self):
        print("Backing up db")
        self.backup_db()

    def backup_db(self):
        try:
            client = storage.Client()
            bucket = client.get_bucket('discord_bots_db_backup')
            blob = bucket.blob(self.bot.db.dbname)
            blob.upload_from_filename(self.bot.db.dbname)
            print(f"Uploaded {self.bot.db.dbname} to bucket {bucket.name}")
        except Exception as e:
            raise e

# Username	NaturalId	Name	StorageType	Ticker	Amount
# JAB416171	ANT	Antares Station	WAREHOUSE_STORE	ABH	11

    @slash_command(name="register", integration_types={discord.IntegrationType.user_install, discord.IntegrationType.guild_install})
    @option("prun_user", description="prun user")
    async def register(self, ctx: discord.ApplicationContext, prun_user: str):
        engine = await self.bot.db.getEngine()
        user = User(
            id=ctx.author.id,
            prun_user=prun_user
        )
        try:
            await self.save(user, engine=engine)
        except sqlalchemy.exc.IntegrityError:
            await ctx.respond("User already registered", ephemeral=True)
            return
        self.backup_db()
        await ctx.respond(f"User {prun_user} registered", ephemeral=True)

    async def is_registered(self, ctx: discord.ApplicationContext):
        engine = await self.bot.db.getEngine()
        async with engine.begin() as conn:
            c = await conn.execute(text("select * from users where id=:id"),
                                    [{"id": ctx.author.id}]
                                   )
            user = c.fetchone()
            if not user:
                await ctx.respond("User not registered", ephemeral=True)
                return False
        return True

    @slash_command(name="add_item", integration_types={discord.IntegrationType.user_install, discord.IntegrationType.guild_install})
    @option("item_ticker", description="material")
    @option("item_location", description="location")
    @option("item_price", description="price")
    @option("item_reserve", description="reserve", default=0)
    @option("item_reserve_percent", description="reserve percent", default=1)
    async def add_item(self, ctx: discord.ApplicationContext, item_ticker: str, item_location: str, item_price: int, item_reserve: int = 0, item_reserve_percent: float = 1):
        if not await self.is_registered(ctx):
            await ctx.respond("Please register first with /register", ephemeral=True)
            return
        engine = await self.bot.db.getEngine()
        item = Offer(
            id=ctx.author.id,
            guild_id=ctx.guild.id,
            item_ticker=item_ticker,
            item_price=item_price,
            item_location=item_location,
            item_reserve_percent=item_reserve_percent,
            item_reserve=item_reserve
        )
        try:
            await self.save(item, engine=engine)
        except sqlalchemy.exc.IntegrityError:
            await ctx.respond("Item already exists", ephemeral=True)
            return
        self.backup_db()
        await ctx.respond(f"Item {item_ticker} added", ephemeral=True)

    @slash_command(name="remove_item", integration_types={discord.IntegrationType.user_install, discord.IntegrationType.guild_install})
    @option("item_ticker", description="material")
    @option("item_location", description="location")
    async def remove_item(self, ctx: discord.ApplicationContext, item_ticker: str, item_location: str):
        if not await self.is_registered(ctx):
            await ctx.respond("Please register first with /register", ephemeral=True)
            return
        engine = await self.bot.db.getEngine()
        async with engine.begin() as conn:
            c = await conn.execute(text("delete from offers where id=:id and guild_id=:guild_id and item_ticker=:item_ticker and item_location=:item_location"),
                                   [{"id": ctx.author.id,
                                     "guild_id": ctx.guild.id,
                                     "item_ticker": item_ticker,
                                     "item_location": item_location
                                    }]
                                   )
        self.backup_db()
        await ctx.respond("Item removed", ephemeral=True)

    @slash_command(name="update_item", integration_types={discord.IntegrationType.user_install, discord.IntegrationType.guild_install})
    @option("item_ticker", description="material")
    @option("item_location", description="location")
    @option("item_price", description="price")
    @option("item_reserve", description="reserve", default=0)
    @option("item_reserve_percent", description="reserve percent", default=0)
    @option("display_if_zero", description="display if zero", default=True)
    async def update_item(self, ctx: discord.ApplicationContext, item_ticker: str, item_location: str, item_price: int, item_reserve: int = 0, item_reserve_percent: float = 0, display_if_zero: bool = True):
        if not await self.is_registered(ctx):
            await ctx.respond("Please register first with /register", ephemeral=True)
            return
        engine = await self.bot.db.getEngine()
        async with engine.begin() as conn:
            c = await conn.execute(text("update offers set item_price=:item_price, item_reserve=:item_reserve, item_reserve_percent=:item_reserve_percent, display_if_zero=:display_if_zero where id=:id and guild_id=:guild_id and item_ticker=:item_ticker and item_location=:item_location"),
                                   [{"id": ctx.author.id,
                                     "guild_id": ctx.guild.id,
                                     "item_ticker": item_ticker,
                                     "item_price": item_price,
                                     "item_location": item_location,
                                     "item_reserve_percent": item_reserve_percent,
                                     "item_reserve": item_reserve,
                                     "display_if_zero": display_if_zero
                                    }]
                                   )
        self.backup_db()
        await ctx.respond("Item updated", ephemeral=True)

    async def get_prun_users(self, ctx: discord.AutocompleteContext):
        ret = []
        engine = await self.bot.db.getEngine()
        async with engine.begin() as conn:
            c = await conn.execute(text("select distinct prun_user from users"))
            prun_users = c.fetchall()
            for row in prun_users:
                ret.append(row[0])
        return ret

    def get_oldest_timestamp(self, timestamps):
        oldest = None
        for timestamp in timestamps:
            if not oldest or timestamp < oldest:
                oldest = timestamp
        print(type(oldest))
        return oldest

    @slash_command(name="post_storefront", integration_types={discord.IntegrationType.guild_install})
    @option("user", description="user", autocomplete=get_prun_users)
    async def post_storefront(self, ctx: discord.ApplicationContext, user: str):
        if not await self.is_registered(ctx):
            await ctx.respond("Please register first with /register", ephemeral=True)
            return
        embeds, timestamps = await self.generate_storefront_embeds(ctx.guild, ctx.author)
        oldest_timestamp = self.get_oldest_timestamp(timestamps)
        oldest_timestamp = discord.utils.format_dt(oldest_timestamp)
        response = await ctx.respond(f"Last updated at {oldest_timestamp}", embeds=embeds)
        msg = await response.original_response()
        engine = await self.bot.db.getEngine()
        async with engine.begin() as session:
            # delete any existing storefront message for this user
            existing_message = await session.execute(
                sqlalchemy.select(StorefrontMessages).where(
                    StorefrontMessages.id == ctx.author.id,
                    StorefrontMessages.guild_id == ctx.guild.id
                )
            )
            existing_message = existing_message.scalars().first()
            if existing_message:
                await self.delete(existing_message, engine=engine)
            # Save the message to the database
            storefront_message = StorefrontMessages(
                id=ctx.author.id,
                guild_id=ctx.guild.id,
                channel_id=ctx.channel.id,
                message_id=msg.id
            )
            await self.save(storefront_message, engine=engine)
            await session.commit()

    async def generate_storefront_embeds(self, guild, user):
        print(f"Generating storefront embeds for user {user}")
        engine = await self.bot.db.getEngine()
        async with engine.begin() as session:
            # Fetch offers for the user
            offers = await session.execute(
                sqlalchemy.select(Offer).where(Offer.id == user.id)
            )
            offers = offers.all()

            # Fetch inventory for the user
            user_inventory = await session.execute(
                sqlalchemy.select(Inventory).where(Inventory.user_id == user.id)
            )
            user_inventory = user_inventory.all()
            prun_user = await session.execute(
                sqlalchemy.select(User).where(User.id == user.id)
            )
            prun_user = prun_user.first()
            prun_user_name = prun_user.prun_user if prun_user else "Unknown User"

        notes = ""
        locations = set()
        embeds = []
        timestamps = []
        for offer in offers:
            locations.add(offer.item_location)
            print(f"Found offer for location {offer.item_location}")
        for location in locations:
            embed = discord.Embed()
            embed.set_author(name=f"{location} Storefront for {prun_user_name}")
            # embed.set_footer(text=user)
            fields = []
            for offer in offers:
                print(offer)
                if guild and offer.guild_id != guild.id:
                    print(f"Skipping offer for guild {offer.guild_id}")
                    continue
                location = offer.item_location
                ticker = offer.item_ticker
                price = offer.item_price
                reserve = offer.item_reserve
                reserve_percent = 1 - offer.item_reserve_percent
                if hasattr(offer, 'notes'):
                    notes = offer.notes
                inventory = 0
                for item in user_inventory:
                    print(ticker, location)
                    print(item.item_ticker, item.item_location)
                    if item.item_ticker == ticker and item.item_location == location:
                        print(f"Found item in inventory: {item}")
                        inventory = item.item_quantity
                        timestamps.append(item.item_age)
                        print(item, inventory)
                        break
                stock = inventory - reserve
                stock = int(stock * reserve_percent)
                if stock <= 0 and offer.item_location == location and not offer.display_if_zero:
                    fields.append((f"{ticker} - ${price}", "Out of Stock"))
                else:
                    fields.append((f"{ticker} - ${price}", f"{stock} In Stock, ${stock * price} to buy all"))

            if not fields:
                continue
            for name, value in fields:
                embed.add_field(name=name, value=value, inline=False)
            if notes:
                embed.add_field(name="Notes", value=notes)
            embeds.append(embed)
        return embeds, timestamps

    async def update_storefronts(self, guild):
        engine = await self.bot.db.getEngine()
        async with engine.begin() as session:
            # Fetch all storefront messages for the guild using direct ID lookup
            storefront_messages_query = await session.execute(
                sqlalchemy.select(StorefrontMessages.id, StorefrontMessages.guild_id, StorefrontMessages.channel_id, StorefrontMessages.message_id).where(
                    StorefrontMessages.guild_id == guild.id
                )
            )
            storefront_messages = storefront_messages_query.all()

            print(len(storefront_messages))
            for row in storefront_messages:
                print(f"Working on message {row}")
                user_id = row[0]
                guild_id = row[1]
                channel_id = row[2]
                discord_message_id = row[3]

                # Fetch the message from the channel
                channel = guild.get_channel(channel_id)
                user = await self.bot.fetch_user(user_id)
                if channel:
                    try:
                        msg = await channel.fetch_message(discord_message_id)
                        print(f"Found message {msg}")
                        if msg:
                            # Regenerate the embeds and edit the message
                            print(f"Regenerating embeds for message {discord_message_id}")
                            embeds, timestamps = await self.generate_storefront_embeds(guild, user)
                            oldest_timestamp = self.get_oldest_timestamp(timestamps)
                            oldest_timestamp = discord.utils.format_dt(oldest_timestamp)
                            await msg.edit(content=f"Last updated at {oldest_timestamp}", embeds=embeds)

                    except discord.NotFound:
                        print(f"Message {discord_message_id} not found in channel {channel_id}")
                        # Delete using SQL directly since we don't have an ORM object
                        await session.execute(
                            sqlalchemy.delete(StorefrontMessages).where(
                                StorefrontMessages.id == user_id,
                                StorefrontMessages.guild_id == guild_id
                            )
                        )
                        await session.commit()
                else:
                    print(f"Channel {channel_id} not found in guild {guild.id}")

    @slash_command(name="invite", integration_types={discord.IntegrationType.user_install, discord.IntegrationType.guild_install})
    async def invite(self, ctx: discord.ApplicationContext):
        await ctx.respond(f"Invite link is https://discord.com/api/oauth2/authorize?client_id={self.bot.user.id}&permissions=8&scope=bot%20applications.commands")

def setup(bot):
    bot.add_cog(SimpleCog(bot))