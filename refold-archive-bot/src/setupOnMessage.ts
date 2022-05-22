import { TextChannel } from 'discord.js';
import config from '../config.json';
import { listTypes } from './constants';
import { copyMessageToChannel } from './helpers/copyMessageToChannel';
import { determineIsExcludeChannel } from './helpers/determineIsExcludedChannel';
import { generateArchivePayload } from './helpers/generateArchivePayload';
import { isProfane } from './helpers/setupOnMessage/isProfane';
import { sendToJail } from './helpers/setupOnMessage/sendToJail';
import { setupCooldown } from './helpers/setupOnMessage/setupCooldown';
import { MyClient } from './index';
const prefix = config.command.prefix;

const { blacklist, watchlist } = listTypes;

export const setupOnMessage = (client: MyClient) =>
  client.on('message', async (message) => {
    const hasExcludedChannels =
      config.wordListFilter.excludedChannels.length >= 1;
    if (hasExcludedChannels) {
      const isExcludedChannel = determineIsExcludeChannel(
        'wordListFilter',
        message
      );
      if (isExcludedChannel) return;
    }
    // skip if the author is a bot
    const { content, author } = message;
    if (author.bot) return;

    const profane = isProfane(content);

    const watchlistChannel = await client.channels.fetch(
      // if bot gets hosted on server, remove jail channel from config
      process.env.WATCHLIST_CHANNEL_ID || config.watchlistChannelId
    );

    const jailChannel = await client.channels.fetch(
      // if bot gets hosted on server, remove jail channel from config
      process.env.JAIL_CHANNEL_ID || config.jailChannelId
    );

    if (profane?.matchedWord) {
      // TODO: If mod says any non prohibited blacklist word, log it to console
      switch (profane.listType) {
        case blacklist:
          message.delete();
          return sendToJail(message, jailChannel, profane.matchedWord);
        case watchlist:
          const archivePayload = generateArchivePayload(message);

          return copyMessageToChannel(
            message,
            watchlistChannel as TextChannel,
            archivePayload,
            true,
            profane.matchedWord
          );
        default:
          return;
      }
    }

    // get guild member details from the author's ID
    const member = message.guild?.member(message.author.id);

    // skip if not a member
    if (!member) {
      console.log('[WARN] Unable to find member in guild: ', message.author);
      return;
    }

    // regular expression to match a single command pattern
    const singleCommandRegex = new RegExp(prefix + '[\\w-]+', 'i');

    const messageHasCommand = singleCommandRegex.test(message.content);
    if (!messageHasCommand) return;

    // extract command name from message content
    let commandName = (message as any).content
      .match(singleCommandRegex)[0]
      .toLowerCase()
      .replace(prefix, '');

    // find command from commands collection or from aliases
    const command: any =
      client.commands?.get(commandName) ||
      client.commands?.find(
        (cmd: any) => cmd.aliases && cmd.aliases.includes(commandName)
      );

    // remove command from message content and trim whitespace
    message.content = message.content.replace(singleCommandRegex, '').trim();

    if (!command) {
      console.debug('[DEBUG] Command not present: ', commandName);
      return;
    }

    setupCooldown(client, command, message);
  });
