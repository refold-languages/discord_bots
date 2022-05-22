import { Client, Message, TextChannel } from 'discord.js';
import config from '../../config.json';
import { cleanContent, getCommandList } from '../helpers/commands/cleanContent';
import { copyMessageToChannel } from '../helpers/copyMessageToChannel';
import { generateArchivePayload } from '../helpers/generateArchivePayload';
import { determineIsExcludeChannel } from './../helpers/determineIsExcludedChannel';

export const name: string = 'question';
export const aliases: string[] = ['question', 'q'];
export const emojis: string[] = ['❓'];
export const cooldown = 10;
export const description: string =
  'Clones a message and makes a custom embed in another channel';

export const run = async (client: Client, message: Message) => {
  const hasExcludedChannels =
    config.questionCommand.excludedChannels.length >= 1;
  if (hasExcludedChannels) {
    const isExcludedChannel = determineIsExcludeChannel(
      'questionCommand',
      message
    );
    if (isExcludedChannel) return;
  }
  const questionLogChannel = await client.channels.fetch(
    // if bot gets hosted on server, remove question channel from config
    process.env.QUESTION_LOG_CHANNEL_ID || config.questionLogChannelId
  );

  if (!questionLogChannel) {
    console.error(
      `Could not find question log channel with ID of ${
        process.env.QUESTION_LOG_CHANNEL_ID || config.questionLogChannelId
      }`
    );
    return;
  }

  let content = message.content.trim();

  // create a list of all commands, including aliases
  const commandList = getCommandList(aliases, name);
  // remove command content from message
  const cleanedContent = cleanContent(commandList, content);

  const archivePayload = generateArchivePayload(message);

  return copyMessageToChannel(
    cleanedContent,
    questionLogChannel as TextChannel,
    archivePayload
  );
};
