import Discord from 'discord.js';
import 'dotenv/config';
import config from '../config.json';
import { setClientCommands } from './helpers/index/setClientCommands';
import { setupOnMessageReactionAdd } from './setupMessageReactionAdd';
import { setupOnGuildMemberAdd } from './setupOnGuildMemberAdd';
import { setupOnMessage } from './setupOnMessage';

export interface MyClient extends Discord.Client {
  commands?: Discord.Collection<unknown, unknown>;
}

let client: MyClient = new Discord.Client();
client.commands = new Discord.Collection();

(async () => {
  const token = process.env.TOKEN || config.token;
  await client.login(token).catch((error) => {
    console.error(error);
    process.exit(0);
  });

  console.info('Bot logged in using token');

  setClientCommands(client);

  client.once('ready', () => {
    console.info('Bot is ready!');
  });

  await setupOnGuildMemberAdd(client);
  await setupOnMessageReactionAdd(client);
  await setupOnMessage(client);
})();
