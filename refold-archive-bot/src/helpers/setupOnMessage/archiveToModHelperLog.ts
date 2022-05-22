import { Client, MessageReaction, TextChannel } from 'discord.js';
import config from '../../../config.json';
import { copyMessageToChannel } from '../copyMessageToChannel';
import { generateArchivePayload } from '../generateArchivePayload';
import {
  getEmojiToRemove,
  removeEmojiFromMessage
} from './removeEmojiFromMessage';

export const archiveToModHelperLog = async (
  client: Client,
  messageReaction: MessageReaction,
  reactingUserId: string
) => {
  const archiveToModHelperLogEmoji = '🪱';
  const helperFlagChannel = await client.channels.fetch(
    // if bot gets hosted on server, remove jail channel from config
    process.env.HELPER_FLAG_CHANNEL_ID || config.helperFlagChannelId
  );

  const { message } = messageReaction;

  const archivePayload = generateArchivePayload(message);

  await copyMessageToChannel(
    message,
    helperFlagChannel as TextChannel,
    archivePayload,
    true
  );
  getEmojiToRemove(messageReaction, archiveToModHelperLogEmoji);
  await removeEmojiFromMessage(
    messageReaction,
    reactingUserId,
    archiveToModHelperLogEmoji
  );
  return;
};
