import { MessageReaction } from 'discord.js';

export const getEmojiToRemove = (
  messageReaction: MessageReaction,
  emoji: string
) =>
  messageReaction.message.reactions.cache.find(
    (reaction) => reaction.emoji.name === emoji
  );

export const removeEmojiFromMessage = async (
  messageReaction: MessageReaction,
  reactingUserId: string,
  emoji: string
) => {
  const emojiToRemove = getEmojiToRemove(messageReaction, emoji);
  await emojiToRemove?.users.remove(reactingUserId);
  return;
};
