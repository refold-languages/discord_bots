import { Client, Message } from 'discord.js';
import config from '../../config.json';
import { determineIsExcludeChannel } from '../helpers/determineIsExcludedChannel';
import { sendToArchiveChannel } from './../helpers/commands/sendToArchiveChannel';

export const name: string = 'archive';
export const aliases: string[] = ['share', 'save', 's'];
export const emojis: string[] = ['📎', '🪱'];
export const cooldown = 10;
export const description: string =
  'Clones a message and makes a custom embed in another channel';

export const run = async (client: Client, message: Message) => {
  const hasExcludedChannels =
    config.archiveCommand.excludedChannels.length >= 1;
  if (hasExcludedChannels) {
    const isExcludedChannel = determineIsExcludeChannel(
      'archiveCommand',
      message
    );
    if (isExcludedChannel) return;
  }
  await sendToArchiveChannel(client, message, 'command', aliases);
};
