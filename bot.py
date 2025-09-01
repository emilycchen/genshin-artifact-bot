import os
import re
import discord
from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("TOKEN")
GUILD_ID = os.getenv("GUILD_ID")  # idk what this is...for faster slash command sync or smth

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

def rate_artifact_dps(substats: dict, is_four_liner: bool = True, alloc_weight: float = 0.7):

    # per_roll_max = {
    #     "crit rate": 3.9,
    #     "crit dmg": 7.8,
    #     "atk%": 5.8,
    #     "hp%": 5.8,
    #     "def%": 7.3,
    #     "elemental mastery": 23,
    #     "energy recharge": 6.5,
    # }

    # ceiling_6 = {
    #     "crit rate": 23.3,
    #     "crit dmg": 46.6,
    #     "atk%": 35.0,
    #     "elemental mastery": 140,
    #     "energy recharge": 38.9,
    # }

    """
    DPS-first rating that finds the best integer allocation of rolls to Crit Rate / Crit DMG.
    Returns a detailed dict including estimated rolls, allocation%, quality%, CV, and score.
    """

    per_roll = {"crit rate": 3.9, "crit dmg": 7.8}  # per-roll maxes used to estimate allocated maxima
    crit_rate_val = substats.get("crit rate", 0.0)
    crit_dmg_val = substats.get("crit dmg", 0.0)
    available_rolls = 6 if is_four_liner else 5
    quality_weight = 1.0 - alloc_weight

    best = None

    # try all possible integer allocations where roll_cr + roll_cd <= available_rolls
    for roll_cr in range(0, available_rolls + 1):
        for roll_cd in range(0, available_rolls - roll_cr + 1):
            if roll_cr == 0 and roll_cd == 0:
                continue

            alloc_max_cr = roll_cr * per_roll["crit rate"]
            alloc_max_cd = roll_cd * per_roll["crit dmg"]

            qualities = []
            if roll_cr > 0:
                qualities.append(min(crit_rate_val / max(alloc_max_cr, 1e-9), 1.0))
            if roll_cd > 0:
                qualities.append(min(crit_dmg_val / max(alloc_max_cd, 1e-9), 1.0))

            quality_frac = sum(qualities) / len(qualities) if qualities else 0.0
            allocation_frac = (roll_cr + roll_cd) / available_rolls

            score = (alloc_weight * allocation_frac) + (quality_weight * quality_frac)

            entry = {
                "roll_cr": roll_cr,
                "roll_cd": roll_cd,
                "allocation_frac": allocation_frac,
                "quality_frac": quality_frac,
                "score": score,
                "alloc_max_cr": alloc_max_cr,
                "alloc_max_cd": alloc_max_cd,
            }

            if best is None:
                best = entry
            else:
                if (entry["score"], entry["allocation_frac"], entry["quality_frac"]) > (
                    best["score"],
                    best["allocation_frac"],
                    best["quality_frac"],
                ):
                    best = entry

    dps_score_pct = round(best["score"] * 100, 1)
    crit_allocation_pct = round(best["allocation_frac"] * 100, 1)
    crit_quality_pct = round(best["quality_frac"] * 100, 1)
    cv = round((crit_rate_val * 2.0) + crit_dmg_val, 1)

    if dps_score_pct >= 90:
        tier = "S"
    elif dps_score_pct >= 75:
        tier = "A"
    elif dps_score_pct >= 60:
        tier = "B"
    elif dps_score_pct >= 45:
        tier = "C"
    else:
        tier = "D"

    return {
        "dps_score": dps_score_pct,
        "tier": tier,
        "cv": cv,
        "crit_allocation_pct": crit_allocation_pct,
        "crit_quality_pct": crit_quality_pct,
        "estimated_rolls": (best["roll_cr"], best["roll_cd"]),
    }

print(f"GUILD_ID from .env: '{GUILD_ID}' type: {type(GUILD_ID)}")

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")

    print("Local commands before sync:")
    for cmd in bot.tree.get_commands():
        print(f"- {cmd.name}: {cmd.description}")

    try:
        synced = await bot.tree.sync()
        print(f"Global sync: {len(synced)} command(s)")

        for cmd in synced:
            print(f"- {cmd.name}: {cmd.description}")

    except Exception as e:
        print(f"Error syncing commands: {e}")


@bot.tree.command(name="sybau", description="twin")
async def sybau(interaction: discord.Interaction):
    await interaction.response.send_message("bum")


@bot.tree.command(name="rate", description="Rate a Genshin artifact for DPS efficiency")
@app_commands.describe(
    substats="Enter substats like: crit rate 10.5, crit dmg 21, atk% 5.8",
    four_liner="Does this artifact start with 4 substats? (True/False)"
)
async def rate(interaction: discord.Interaction, substats: str, four_liner: bool = True):
    parts = substats.split(",")
    stats = {}

    for part in parts:
        match = re.match(r"([a-zA-Z% ]+)\s+([\d.]+)", part.strip())
        if match:
            stat, val = match.groups()
            stats[stat.lower().strip()] = float(val)

    result = rate_artifact_dps(stats, is_four_liner=four_liner)

    liner_type = "4-liner" if four_liner else "3-liner"

    msg = (
        f"DPS Efficiency: **{result['dps_score']}**\n"
        f"Tier: **{result['tier']}**\n"
        f"Crit Value (CV): **{result['cv']}**\n"
        f"Crit Allocation Percentage: **{result['crit_allocation_pct']}**\n"
        f"Crit Quality Percentage: **{result['crit_quality_pct']}**\n"
        f"Estimated Rolls: Crit Rate: **{result['estimated_rolls'][0]}**, Crit Damage: **{result['estimated_rolls'][1]}**\n"
        f"Artifact type: {liner_type}\n\n"
    )

    # "dps_score": dps_score_pct,
    # "tier": tier,
    # "cv": cv,
    # "crit_allocation_pct": crit_allocation_pct,
    # "crit_quality_pct": crit_quality_pct,
    # "estimated_rolls": (best["roll_cr"], best["roll_cd"]),
    # "details": details,

    await interaction.response.send_message(msg)


bot.run(TOKEN)