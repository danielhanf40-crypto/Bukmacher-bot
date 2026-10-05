import os
import requests
import json
import discord
from discord.ext import commands

DISCORD_TOKEN = os.environ.get("DISCORD_TOKEN")
ROBLOX_API_KEY = os.environ.get("ROBLOX_API_KEY")
UNIVERSE_ID = os.environ.get("UNIVERSE_ID")
DATASTORE_NAME = "PlayerData"

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

powiazane_konta = {}
mecze = {}
zaklady = []

def get_roblox_data(roblox_id):
    url = f"https://apis.roblox.com/datastores/v1/universes/{UNIVERSE_ID}/standard-datastores/datastore/entries/entry"
    params = {"datastoreName": DATASTORE_NAME, "entryKey": f"Player_{roblox_id}"}
    headers = {"x-api-key": ROBLOX_API_KEY}
    res = requests.get(url, params=params, headers=headers)
    return res.json() if res.status_code == 200 else None

def update_roblox_coins(roblox_id, kwota_zmiany):
    data = get_roblox_data(roblox_id)
    if data is None:
        return False
    current_coins = data.get("Coins", 0)
    if current_coins + kwota_zmiany < 0:
        return False
    data["Coins"] += kwota_zmiany
    url = f"https://apis.roblox.com/datastores/v1/universes/{UNIVERSE_ID}/standard-datastores/datastore/entries/entry"
    params = {"datastoreName": DATASTORE_NAME, "entryKey": f"Player_{roblox_id}"}
    headers = {"x-api-key": ROBLOX_API_KEY, "Content-Type": "application/json"}
    res = requests.post(url, params=params, headers=headers, data=json.dumps(data))
    return res.status_code == 200

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"✅ Bot zalogowany jako {bot.user}")

@bot.tree.command(name="polacz", description="Połącz konto Discord z Roblosem")
async def polacz(interaction: discord.Interaction, roblox_id: str):
    powiazane_konta[interaction.user.id] = roblox_id
    await interaction.response.send_message(f"✅ Połączono konto z Roblox ID: `{roblox_id}`", ephemeral=True)

@bot.tree.command(name="dodaj_mecz", description="Dodaj mecz do oferty")
async def dodaj_mecz(interaction: discord.Interaction, nazwa: str, kurs_1: float, kurs_2: float):
    mecze[nazwa] = {"kurs_1": kurs_1, "kurs_2": kurs_2, "aktywny": True}
    await interaction.response.send_message(f"⚽ Dodano mecz: **{nazwa}** | Kurs 1: `{kurs_1}` | Kurs 2: `{kurs_2}`")

@bot.tree.command(name="obstaw", description="Postaw kupon na mecz")
async def obstaw(interaction: discord.Interaction, mecz: str, typ: int, stawka: int):
    discord_id = interaction.user.id
    if discord_id not in powiazane_konta:
        return await interaction.response.send_message("❌ Najpierw połącz konto komendą `/polacz [Roblox_ID]`!", ephemeral=True)
    if mecz not in mecze or not mecze[mecz]["aktywny"]:
        return await interaction.response.send_message("❌ Mecz nie istnieje lub jest zamknięty!", ephemeral=True)
    roblox_id = powiazane_konta[discord_id]
    if not update_roblox_coins(roblox_id, -stawka):
        return await interaction.response.send_message("❌ Brak kasy w grze lub błąd połączenia z Robloxem!", ephemeral=True)
    kurs = mecze[mecz]["kurs_1"] if typ == 1 else mecze[mecz]["kurs_2"]
    zaklady.append({"user_id": discord_id, "roblox_id": roblox_id, "mecz": mecz, "typ": typ, "stawka": stawka, "kurs": kurs})
    await interaction.response.send_message(f"🎟️ **Postawiono kupon!** Mecz: `{mecz}` | Typ: `{typ}` | Stawka: `{stawka}$`")

@bot.tree.command(name="rozlicz", description="Rozlicz mecz i wypłać wygrane")
async def rozlicz(interaction: discord.Interaction, mecz: str, wygrani: int):
    if mecz not in mecze:
        return await interaction.response.send_message("❌ Brak takiego meczu.", ephemeral=True)
    mecze[mecz]["aktywny"] = False
    for z in list(zaklady):
        if z["mecz"] == mecz:
            if z["typ"] == wygrani:
                wygrana = int(z["stawka"] * z["kurs"])
                update_roblox_coins(z["roblox_id"], wygrana)
            zaklady.remove(z)
    await interaction.response.send_message(f"🏆 Mecz **{mecz}** rozliczony! Wygrana opcja: `{wygrani}`.")

if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)
