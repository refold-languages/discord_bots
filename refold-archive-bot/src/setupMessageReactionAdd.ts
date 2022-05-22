import { MessageReaction, PartialUser, User } from 'discord.js';
import config from '../config.json';
import { sendToArchiveChannel } from './helpers/commands/sendToArchiveChannel';
import { determineIsExcludeChannel } from './helpers/determineIsExcludedChannel';
import { archiveToModHelperLog } from './helpers/setupOnMessage/archiveToModHelperLog';
import { archiveToQuestionLog } from './helpers/setupOnMessage/archiveToQuestionLog';
import { MyClient } from './index';

const emojis = config.command.emojis;

const getRemainingEmoji = (messageReaction: MessageReaction) =>
  emojis.filter((emoji) => {
    return emoji !== messageReaction.emoji.name;
  });

const getCacheEmoji = (
  messageReaction: MessageReaction,
  remainingEmoji: string[]
) =>
  messageReaction.message.reactions.cache.some((_, reactionEmoji) => {
    return remainingEmoji.includes(reactionEmoji);
  });

const determineEmojiPermissions = (
  messageReaction: MessageReaction,
  reactingUser: User | PartialUser
) => {
  const currentUserInfo = messageReaction?.message?.guild?.members.cache.get(
    reactingUser.id
  );

  const hasEmojiPermissions = currentUserInfo?.roles.cache.find(
    (role) =>
      role.name === 'Helper' || role.name === 'Mod' || role.name === 'Admin'
  );

  return hasEmojiPermissions;
};

export const name: string = 'archive';
export const aliases: string[] = ['share', 'save', 's'];

interface CommandPath {
  excludedChannels: string[];
}

export const setupOnMessageReactionAdd = async (client: MyClient) =>
  client.on('messageReactionAdd', async (messageReaction, reactingUser) => {
    const isBot = messageReaction.message.author.bot;
    if (isBot) return;

    const logMessageEmoji: string = '🪱';
    const paperclipEmoji: string = '📎';
    const questionMarkEmoji: string = '❓';

    const commandPath: CommandPath =
      config.emojiCommands[messageReaction.emoji.name];

    if (commandPath) {
      const hasExcludedChannels = commandPath.excludedChannels.length >= 1;
      if (hasExcludedChannels) {
        const isExcludedChannel: boolean = determineIsExcludeChannel(
          messageReaction.emoji.name,
          messageReaction.message,
          true
        );
        if (isExcludedChannel) return;
      }
    }

    const hasLogMessageEmoji = messageReaction.emoji.name === logMessageEmoji;
    const hasPaperclipEmoji = messageReaction.emoji.name === paperclipEmoji;
    const hasQuestionMarkEmoji =
      messageReaction.emoji.name === questionMarkEmoji;

    const hasEmojiOnList = paperclipEmoji || logMessageEmoji;
    if (!hasEmojiOnList) {
      console.log(
        `[DEBUG] Reaction emoji ${messageReaction.emoji.name} is NOT in emoji list ${emojis}`
      );
      return;
    }

    // check if the current emoji is in the cache with a count > 1,
    // if it is, skip it
    let hasTooManyEmojis: boolean = false;

    const emojiName: MessageReaction | undefined =
      messageReaction.message.reactions.cache.get(messageReaction.emoji.name);

    if (emojiName) {
      hasTooManyEmojis = emojiName.count!! > 1;
    }

    if (hasTooManyEmojis) {
      console.log(
        `[DEBUG] ${messageReaction.emoji.name} count is greater than 1`
      );
      return;
    }

    const remainingEmoji = getRemainingEmoji(messageReaction);

    // assume that current emoji was just added with a count of 1
    // get emoji list (sans current emoji), and check the cache to see if any
    //  of them are in the cache
    // if so, skip here
    const reactionCacheHasEmoji = getCacheEmoji(
      messageReaction,
      remainingEmoji
    );

    if (reactionCacheHasEmoji) {
      console.log('[DEBUG] Other emojis are already present');
      return;
    }

    const hasEmojiPermissions = determineEmojiPermissions(
      messageReaction,
      reactingUser
    );

    if (hasEmojiPermissions) {
      if (hasLogMessageEmoji) {
        return await archiveToModHelperLog(
          client,
          messageReaction,
          reactingUser.id
        );
      } else if (hasPaperclipEmoji) {
        return await sendToArchiveChannel(client, messageReaction, 'emoji');
      } else if (hasQuestionMarkEmoji) {
        return await archiveToQuestionLog(client, messageReaction);
      }
    }

    return;
  });
