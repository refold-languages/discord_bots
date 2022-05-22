import { Client, Message, MessageReaction, TextChannel } from 'discord.js';
import config from '../../../config.json';
import { copyMessageToChannel } from '../copyMessageToChannel';
import { generateArchivePayload } from '../generateArchivePayload';
import { cleanContent, getCommandList } from './cleanContent';
import {
  findDuplicateArchiveMessage,
  getArchiveMessages
} from './findArchiveMessage';
import { getArchiveInfo } from './getArchiveInfo';

const archive = config.command.archive;
const prefix = config.command.prefix;

export const sendToArchiveChannel = async (
  client: Client,
  currentMessage: MessageReaction | Message,
  commandType: string,
  aliases?: string[]
) => {
  let commandList: string[];
  let cleanedContent: string = '';
  let message: Message | string =
    commandType === 'command'
      ? (currentMessage as Message)
      : (currentMessage as MessageReaction).message;
  const content = message.content.trim();

  if (commandType === 'command') {
    commandList = getCommandList(aliases!!, 'archive');
    cleanedContent = cleanContent(commandList, content, prefix);
  }

  const { archiveChannel, archiveName, archiveId } = getArchiveInfo(
    archive,
    message
  );

  if (!archiveName && commandType === 'command') {
    return message.reply('That command is not available in this channel');
  }

  const messageChannel = message.channel as TextChannel;

  if (!archiveChannel) {
    console.debug(
      `[DEBUG] Channel name ${messageChannel.name} is NOT included in ${archive.channels}`
    );
    return;
  }

  if (!archiveId) {
    console.log(`[DEBUG] Unable to find ID for channel ${archiveName}`);
    return;
  }

  const targetArchiveChannel = client.channels.cache.get(archiveId);

  const archiveMessages = await getArchiveMessages(
    targetArchiveChannel as TextChannel
  );
  const duplicateArchiveMessage = findDuplicateArchiveMessage(
    archiveMessages,
    commandType === 'command' ? cleanedContent : content
  );

  if (duplicateArchiveMessage) return;

  const archivePayload = generateArchivePayload(message);

  return copyMessageToChannel(
    commandType === 'command' ? cleanedContent : content,
    targetArchiveChannel as TextChannel,
    archivePayload
  );
};
