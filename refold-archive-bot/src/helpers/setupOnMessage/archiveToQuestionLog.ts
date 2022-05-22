import { Client, MessageReaction, TextChannel } from 'discord.js';
import config from '../../../config.json';
import { copyMessageToChannel } from '../copyMessageToChannel';
import { generateArchivePayload } from '../generateArchivePayload';

export const archiveToQuestionLog = async (
  client: Client,
  messageReaction: MessageReaction
) => {
  const questionLogChannel = await client.channels.fetch(
    // if bot gets hosted on server, remove jail channel from config
    process.env.QUESTION_LOG_CHANNEL_ID || config.questionLogChannelId
  );

  const { message } = messageReaction;

  const archivePayload = generateArchivePayload(message);

  await copyMessageToChannel(
    message,
    questionLogChannel as TextChannel,
    archivePayload
  );
};
