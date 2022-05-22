import { Channel, Message, TextChannel } from 'discord.js';
import { copyMessageToChannel } from '../copyMessageToChannel';
import { generateArchivePayload } from '../generateArchivePayload';

export const sendToJail = async (
  message: Message,
  jailChannel: Channel,
  matchedWord: string | undefined
) => {
  const jailRole = message?.member?.guild.roles.cache.find(
    (role) => role.name === 'Jailed'
  );

  const botHasArchiverPermissions =
    message?.guild?.me?.hasPermission('MANAGE_ROLES');

  if (!botHasArchiverPermissions) {
    console.error('Bot does not have sufficient permissions');
    return;
  }

  if (jailRole) {
    const currentUser = message?.guild?.members.cache.get(message.author.id);
    const hasPatreonRole = currentUser?.roles.cache.find(
      (role) => role.name === 'Refolder'
    );

    const hasServerBoosterRole = currentUser?.roles.cache.find(
      (role) => role.name === 'Server Booster'
    );

    if (hasPatreonRole && hasServerBoosterRole) {
      await currentUser?.roles.set([
        hasServerBoosterRole,
        hasPatreonRole,
        jailRole
      ]);
    } else if (hasPatreonRole) {
      await currentUser?.roles.set([hasPatreonRole, jailRole]);
    } else if (hasServerBoosterRole) {
      await currentUser?.roles.set([hasServerBoosterRole, jailRole]);
    } else {
      await currentUser?.roles.set([jailRole]);
    }

    const archivePayload = generateArchivePayload(message);

    return copyMessageToChannel(
      message,
      jailChannel as TextChannel,
      archivePayload,
      true,
      matchedWord
    );
  }
  console.log('Jail role not found');
};
