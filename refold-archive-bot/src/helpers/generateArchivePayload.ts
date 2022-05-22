import { Collection, Message, MessageAttachment, User } from 'discord.js';
import {
  generateArchiveColor,
  generateArchiveTitle
} from './commands/generateArchiveInfo';
import { getUrls } from './commands/getUrls';

export interface ArchivePayloadInterface {
  author: User;
  authorAvatar: string;
  authorURL: string;
  attachments: Collection<string, MessageAttachment>;
  URLs: string[] | RegExpMatchArray | null;
  archiveTitle: string;
  archiveColor: string;
}

export const generateArchivePayload = (
  message: Message
): ArchivePayloadInterface => ({
  author: message.author,
  authorAvatar: message.author.displayAvatarURL(),
  authorURL: message.url,
  attachments: message.attachments,
  URLs: getUrls(message.content),
  archiveTitle: generateArchiveTitle(message.content),
  archiveColor: generateArchiveColor()
});
