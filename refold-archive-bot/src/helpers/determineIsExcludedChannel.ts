import { Message, TextChannel } from 'discord.js';
import config from '../../config.json';

export const determineIsExcludeChannel = (
  command: string,
  message: Message,
  isEmojiCommand: boolean = false
): boolean => {
  const currentChannel = message.channel as TextChannel;
  const formattedChannelName =
    currentChannel.name && currentChannel.name.toLowerCase();
  let isExcludedChannel: boolean;
  if (isEmojiCommand) {
    isExcludedChannel =
      config.emojiCommands[command].excludedChannels.includes(
        formattedChannelName
      );
    if (isExcludedChannel) return true;
    return false;
  }
  isExcludedChannel =
    config[command].excludedChannels.includes(formattedChannelName);
  if (isExcludedChannel) return true;
  return false;
};
