const { Client, GatewayIntentBits, SlashCommandBuilder, REST, Routes } = require('discord.js');
require('dotenv').config();

const client = new Client({ intents: [GatewayIntentBits.Guilds] });

// Register a simple slash command: /ping
const commands = [
  new SlashCommandBuilder()
    .setName('ping')
    .setDescription('Replies with pong!'),
  new SlashCommandBuilder()
    .setName('rate')
    .setDescription('Rate a Genshin artifact')
    .addStringOption(option =>
      option.setName('substats')
        .setDescription('Enter substats like: crit rate 10.5, crit dmg 21, atk% 5.8')
        .setRequired(true)),
].map(command => command.toJSON());

// Deploy slash commands once
const rest = new REST({ version: '10' }).setToken(process.env.TOKEN);
rest.put(Routes.applicationCommands(process.env.CLIENT_ID), { body: commands })
  .then(() => console.log('Commands registered.'))
  .catch(console.error);

client.on('ready', () => {
  console.log(`Logged in as ${client.user.tag}`);
});

function rateArtifact(substats) {
  const maxValues = {
    'crit rate': 23.4,
    'crit dmg': 46.8,
    'atk%': 34.8,
    'hp%': 34.8,
    'def%': 43.8
  };

  let total = 0;
  let count = 0;
  let details = [];

  for (let [stat, value] of Object.entries(substats)) {
    stat = stat.toLowerCase();
    if (maxValues[stat]) {
      let eff = (value / maxValues[stat]) * 100;
      total += eff;
      count++;
      details.push(`${stat}: ${eff.toFixed(1)}%`);
    }
  }

  let avg = count > 0 ? total / count : 0;
  let tier = avg >= 90 ? "S" : avg >= 75 ? "A" : avg >= 50 ? "B" : "C";

  return { avg: avg.toFixed(1), tier, details };
}


client.on('interactionCreate', async interaction => {
  if (!interaction.isChatInputCommand()) return;

  if (interaction.commandName === 'ping') {
    await interaction.reply('pong!');
  }

  if (interaction.commandName === 'rate') {
    const input = interaction.options.getString('substats');

    // Parse input like: "crit rate 10.5, crit dmg 21, atk% 5.8"
    const parts = input.split(',');
    let substats = {};

    for (let part of parts) {
        const match = part.trim().match(/([a-zA-Z% ]+)\s+([\d.]+)/);
        if (match) {
        const stat = match[1].toLowerCase().trim();
        const value = parseFloat(match[2]);
        substats[stat] = value;
        }
    }

    // Call the rating function
    const result = rateArtifact(substats);

    await interaction.reply(
        `📊 Artifact Score: **${result.avg}%** → Tier **${result.tier}**\n` +
        result.details.join('\n')
    );
    }

});

client.login(process.env.TOKEN);
