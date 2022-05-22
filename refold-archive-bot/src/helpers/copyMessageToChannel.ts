import Discord, { Message, MessageEmbed, TextChannel } from 'discord.js';
import { ArchivePayloadInterface } from './generateArchivePayload';

export const copyMessageToChannel = async (
  message: Message | string,
  channel: TextChannel,
  archivePayload: ArchivePayloadInterface,
  provideMessageInfo?: boolean,
  matchedWord?: string
) => {
  // create an embed to share the content with attribution to the user
  const archiveEmbed: MessageEmbed = new Discord.MessageEmbed()
    .setColor(archivePayload.archiveColor)
    .setTitle(archivePayload.archiveTitle)
    .setDescription(message)
    .setTimestamp()
    .setFooter(
      `Shared by: ${archivePayload.author.username}`,
      archivePayload.authorAvatar
    );

  // verify there are attachments in the message
  if (archivePayload.attachments) {
    // general purpose function for human readible file sizes
    // see: https://stackoverflow.com/a/61505697
    const hFileSize = function (bytes, si = false) {
      let u,
        b = bytes,
        t = si ? 1000 : 1024;
      ['', si ? 'k' : 'K', ...'MGTPEZY'].find(
        (x) => ((u = x), (b /= t), b ** 2 < 1)
      );
      return `${u ? (t * b).toFixed(1) : bytes} ${u}${!si && u ? 'i' : ''}B`;
    };

    // iterate over each attachment
    archivePayload.attachments.forEach((attachment) => {
      // set the thumbnail of the embed to the URL of any image
      if (attachment.url.match(/.(jpg|jpeg|png|gif|bmp|ico)$/i)) {
        archiveEmbed.setImage(attachment.url);
      } else {
        // get filesize in human readible format
        const fileSize = hFileSize(attachment.size);

        // add a link to each file
        archiveEmbed.addFields({
          name: 'Attachment',
          value: `[${attachment.name}](${attachment.url}) \`${fileSize}\``
        });
      }
    });
  }

  // set URL if one was found
  if (archivePayload.URLs) {
    archiveEmbed.setURL(archivePayload.URLs[0]);
  }

  // add link back to original post
  archiveEmbed.addFields({
    name: '\u200B',
    value: `[Original Post](${archivePayload.authorURL})`
  });

  if (matchedWord) {
    archiveEmbed.addFields({
      name: 'Flagged Word',
      value: matchedWord
    });
  }

  if (provideMessageInfo) {
    archiveEmbed.addFields(
      {
        name: 'Flagged User ID',
        value: archivePayload.author.id,
        inline: true
      },
      {
        name: 'Flagged Message ID',
        value: (message as Message).id,
        inline: true
      }
    );
  }

  await channel.send(archiveEmbed);

  // create additional embeds for any/all URLs in message content
  if (archivePayload.URLs) {
    // get total number of URLs
    const numURLs = archivePayload.URLs.length;
    // send each URL as a separate post
    archivePayload.URLs.forEach((URL, index) => {
      channel.send(`\`[URL ${index + 1}/${numURLs}]\` ${URL}`);
    });
    // to send all URLs in a single post
    //archiveChannel.send(URLs.join('\n'));
  }
};
