import { GuildChannel, Message, TextChannel } from 'discord.js';
export const getArchiveChannel = (archive, message) => {
  return archive.channels.some(
    (channel) => channel['from'] === message.channel.name
  );
};

export const getArchiveName = (archive: any, message: Message) => {
  const messageChannel: TextChannel = message.channel as TextChannel;
  return archive.channels.find(
    (channel: TextChannel) => channel['from'] === messageChannel.name
  );
};

export const getArchiveId = (archiveName: any, message: Message) =>
  message?.guild?.channels?.cache?.find(
    (channel: GuildChannel) => channel!!.name === archiveName!!.to
  )!!.id;

export const getArchiveInfo = (archive: any, message: Message) => {
  const archiveChannel = getArchiveChannel(archive, message);
  const archiveName = getArchiveName(archive, message);
  if (archiveName) {
    const archiveId = getArchiveId(archiveName, message);
    return { archiveChannel, archiveName, archiveId };
  }
  return { archiveChannel, archiveName };
};
