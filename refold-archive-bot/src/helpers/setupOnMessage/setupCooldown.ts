import Discord, { Client, Message } from 'discord.js';

const cooldowns = new Discord.Collection();
const config = require('../../../config.json');
const prefix = config.command.prefix;

interface Command {
  name: string;
  cooldown: any;
  execute: any;
}

export const setupCooldown = (
  client: Client,
  command: Command,
  message: Message
) => {
  const hasCoolDown = cooldowns.has(command.name);
  if (!hasCoolDown) {
    cooldowns.set(command.name, new Discord.Collection());
  }

  const now = Date.now();
  const timestamps: any = cooldowns.get(command.name);
  const threeSeconds = 3;
  const cooldownAmount = (command.cooldown || threeSeconds) * 1000;

  const cooldownHasAuthor = timestamps.has(message.author.id);
  if (cooldownHasAuthor) {
    const expirationTime = timestamps.get(message.author.id) + cooldownAmount;
    if (now < expirationTime) {
      const timeLeft = (expirationTime - now) / 1000;
      return message.reply(
        `\`[COOLDOWN]\` Please wait ${timeLeft.toFixed(
          1
        )} second(s) before trying \`${prefix}${command.name}\` again.`
      );
    }
  }

  // set latest timestamp for the author
  timestamps.set(message.author.id, now);

  // remove the timestamp after the cooldown time has passed
  setTimeout(() => timestamps.delete(message.author.id), cooldownAmount);

  // try executing the command or catch its error
  try {
    return (command as any).run(client, message);
  } catch (error) {
    console.log('[ERROR] Unable to execute command: ', command);
    console.error(error);
  }
};
