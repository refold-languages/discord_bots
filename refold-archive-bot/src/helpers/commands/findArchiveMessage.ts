import { TextChannel } from 'discord.js';
export const getArchiveMessages = async (archiveChannel: TextChannel) => {
  const messages = await archiveChannel.messages.fetch({ limit: 100 });
  const archiveMessages = messages.map((message) => message.embeds).flat();
  return archiveMessages;
};

export const findDuplicateArchiveMessage = (
  messageEmbeds: any,
  cleanedContent: string
) => {
  let messageExists: null | boolean = null;
  for (let embed of messageEmbeds) {
    if (embed.title === cleanedContent) {
      messageExists = true;
    }
  }
  return messageExists;
};
