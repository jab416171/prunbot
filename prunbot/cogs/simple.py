import discord
from discord import option
from discord.ext import commands, pages
from discord.commands import Option, slash_command
from discord.ui import InputText
from datetime import datetime
import aiohttp
import os

class SimpleCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    apikey = os.environ['PRUN_APIKEY']
    inventory_base_url = f'https://rest.fnar.net/csv/inventory?apikey={apikey}&username=USERNAME'
    posts = [
        {
            "JAB416171": {
                "ANT":[
                        {"item": "COF", "price": 650, "reserve": 846, "reserve_percent": 0.5},
                        # {"item": "FIM", "price": 1500, "reserve": 0, "reserve_percent": 0.5},
                        # {"item": "MEA", "price": 4000, "reserve": 0, "reserve_percent": 0.5},
                        {"item": "C", "price": 600, "reserve": 0, "reserve_percent": 0.5},
                        {"item": "BBH", "price": 1800, "reserve": 300, "reserve_percent": 0.5},
                        {"item": "BSE", "price": 1200, "reserve": 300, "reserve_percent": 0.5},

                ],
                "HRT": [
                        {"item": "COF", "price": 650, "reserve": 595, "reserve_percent": 0.5},
                        {"item": "FIM", "price": 1500, "reserve": 0, "reserve_percent": 0.5},
                        {"item": "MEA", "price": 4000, "reserve": 0, "reserve_percent": 0.5},
                        {"item": "ALE", "price": 900, "reserve": 0, "reserve_percent": 0.5},
                ]
            }
        },
        {
            "JCHEUNG9941": {
                "ANT":[
                        {"item": "SC", "price": 1000, "reserve": 100},
                        {"item": "MED", "price": 1100, "reserve": 100},
                        {"item": "NL", "price": 4000, "reserve": 100},
                        {"item": "TRU", "price": 350, "reserve": 100},
                        {"item": "PSL", "price": 3000, "reserve": 50},
                        {"item": "MCG", "price": 33, "reserve": 1000},
                ],
                "ZV-759d":[
                        {"item": "SC", "price": 1000, "reserve": 100},
                        {"item": "MED", "price": 1100, "reserve": 100},
                ],
                "ZV-307c":[
                        {"item": "NL", "price": 4000, "reserve": 100},
                        {"item": "MCG", "price": 33, "reserve": 1000},
                ],
                "ZV-194a":[
                        {"item": "TRU", "price": 350, "reserve": 100},
                        {"item": "NL", "price": 4000, "reserve": 100},
                ],
                "ZV-307e":[
                        {"item": "NL", "price": 4000, "reserve": 100},
                ],
                "notes": "taking orders for SC/MED even if out of stock"
            }
        }
    ]

# Username	NaturalId	Name	StorageType	Ticker	Amount
# JAB416171	ANT	Antares Station	WAREHOUSE_STORE	ABH	11

    @slash_command(name="post_storefront", integration_types={discord.IntegrationType.user_install, discord.IntegrationType.guild_install})
    @option("user", description="user", choices=[list(p.keys())[0] for p in posts])
    async def post_storefront(self, ctx: discord.ApplicationContext, user: str):
        await ctx.respond("WIP", ephemeral=True)

    @slash_command(name="post_embed", integration_types={discord.IntegrationType.user_install, discord.IntegrationType.guild_install})
    @option("user", description="user", choices=[list(p.keys())[0] for p in posts])
    async def post_embed(self, ctx: discord.ApplicationContext, user: str):
        embeds = []
        notes = ""
        for i in self.posts:
            for username, posts in i.items():
                if username != user:
                    continue
                url = self.inventory_base_url.replace("USERNAME", username)
                async with aiohttp.ClientSession() as session:
                    async with session.get(url) as response:
                        data = await response.text()
                        for location, items in posts.items():
                            if location == "notes":
                                notes = items
                                continue
                            # embed = discord.Embed(title=f"Available at {location}:")
                            # embed.set_author(name=username)
                            embed = discord.Embed()
                            embed.set_author(name=f"Available at {location}:")
                            embed.set_footer(text=username)
                            fields = []
                            for item in items:
                                inventory = 0
                                for row in data.split("\n"):
                                    if row.split(",")[0] == username and row.split(",")[4] == item['item'] and row.split(",")[1] == location:
                                        inventory = int(row.split(',')[5])
                                        break
                                stock = inventory - item.get('reserve', 0)
                                stock = int(stock * item.get("reserve_percent", 1))
                                if stock <= 0:
                                    fields.append((f"{item['item']} - ${item['price']}", "Out of Stock"))
                                else:
                                    fields.append((f"{item['item']} - ${item['price']}", f"{stock} In Stock, ${stock*item['price']} to buy all"))
                            for name, value in fields:
                                embed.add_field(name=name, value=value, inline=False)
                            embeds.append(embed)
                        if notes:
                            for embed in embeds:
                                embed.add_field(name="Notes", value=notes)
                        await ctx.respond(embeds=embeds)
        if not embeds:
            await ctx.respond("User not found", ephemeral=True)
    @slash_command(name="invite", integration_types={discord.IntegrationType.user_install, discord.IntegrationType.guild_install})
    async def invite(self, ctx: discord.ApplicationContext):
        await ctx.respond(f"Invite link is https://discord.com/api/oauth2/authorize?client_id={self.bot.user.id}&permissions=8&scope=bot%20applications.commands")

def setup(bot):
    bot.add_cog(SimpleCog(bot))