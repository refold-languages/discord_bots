import fs from 'fs';
import path from 'path';
import { MyClient } from './../../index';

const dev = process.env.NODE_ENV === 'dev';

const getCommandFiles = () => {
  const commandFiles = fs
    .readdirSync(path.join(__dirname, '../../../src/commands'))
    .filter((file: string) => file.endsWith(`${dev ? '.ts' : '.js'}`));
  return commandFiles;
};

export const setClientCommands = (client: MyClient) => {
  const commandFiles = getCommandFiles();
  for (const file of commandFiles) {
    const command = require(`../../../src/commands/${file}`);
    client.commands?.set(command.name, command);
  }
};
