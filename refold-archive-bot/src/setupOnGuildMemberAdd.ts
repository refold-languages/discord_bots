import { Channel, Client, GuildMember } from 'discord.js';
import config from '../config.json';

const userIdBanList = new Set(config.banList);

export const setupOnGuildMemberAdd = async (client: Client) =>
  client.on('guildMemberAdd', async (member: GuildMember) => {
    const membersModLogChannel: Channel = await client.channels.fetch(
      process.env.MEMBERS_MOD_LOG_CHANNEL_ID || config.membersModLogChannelId
    );

    if (member.user.bot) return;
    const userHasBannableId: boolean = userIdBanList.has(member.id);

    if (userHasBannableId && membersModLogChannel.isText()) {
      await member.send(
        'We have a moderator network that reports known trolls and troublemakers. You were reported in another server and so we preemptively removed you from Refold.'
      );
      await member.ban().catch((error) => console.error(error));
      return membersModLogChannel.send(
        `${member.user} was automatically banned from the auto ban watch-list`
      );
    }
    return;
  });
