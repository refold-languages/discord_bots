"use strict";
var __awaiter = (this && this.__awaiter) || function (thisArg, _arguments, P, generator) {
    function adopt(value) { return value instanceof P ? value : new P(function (resolve) { resolve(value); }); }
    return new (P || (P = Promise))(function (resolve, reject) {
        function fulfilled(value) { try { step(generator.next(value)); } catch (e) { reject(e); } }
        function rejected(value) { try { step(generator["throw"](value)); } catch (e) { reject(e); } }
        function step(result) { result.done ? resolve(result.value) : adopt(result.value).then(fulfilled, rejected); }
        step((generator = generator.apply(thisArg, _arguments || [])).next());
    });
};
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.setupOnMessage = void 0;
const config_json_1 = __importDefault(require("../config.json"));
const constants_1 = require("./constants");
const copyMessageToChannel_1 = require("./helpers/copyMessageToChannel");
const determineIsExcludedChannel_1 = require("./helpers/determineIsExcludedChannel");
const generateArchivePayload_1 = require("./helpers/generateArchivePayload");
const isProfane_1 = require("./helpers/setupOnMessage/isProfane");
const sendToJail_1 = require("./helpers/setupOnMessage/sendToJail");
const setupCooldown_1 = require("./helpers/setupOnMessage/setupCooldown");
const prefix = config_json_1.default.command.prefix;
const { blacklist, watchlist } = constants_1.listTypes;
const setupOnMessage = (client) => client.on('message', (message) => __awaiter(void 0, void 0, void 0, function* () {
    var _a, _b, _c;
    const hasExcludedChannels = config_json_1.default.wordListFilter.excludedChannels.length >= 1;
    if (hasExcludedChannels) {
        const isExcludedChannel = determineIsExcludedChannel_1.determineIsExcludeChannel('wordListFilter', message);
        if (isExcludedChannel)
            return;
    }
    const { content, author } = message;
    if (author.bot)
        return;
    const profane = isProfane_1.isProfane(content);
    const watchlistChannel = yield client.channels.fetch(process.env.WATCHLIST_CHANNEL_ID || config_json_1.default.watchlistChannelId);
    const jailChannel = yield client.channels.fetch(process.env.JAIL_CHANNEL_ID || config_json_1.default.jailChannelId);
    if (profane === null || profane === void 0 ? void 0 : profane.matchedWord) {
        switch (profane.listType) {
            case blacklist:
                message.delete();
                return sendToJail_1.sendToJail(message, jailChannel, profane.matchedWord);
            case watchlist:
                const archivePayload = generateArchivePayload_1.generateArchivePayload(message);
                return copyMessageToChannel_1.copyMessageToChannel(message, watchlistChannel, archivePayload, true, profane.matchedWord);
            default:
                return;
        }
    }
    const member = (_a = message.guild) === null || _a === void 0 ? void 0 : _a.member(message.author.id);
    if (!member) {
        console.log('[WARN] Unable to find member in guild: ', message.author);
        return;
    }
    const singleCommandRegex = new RegExp(prefix + '[\\w-]+', 'i');
    const messageHasCommand = singleCommandRegex.test(message.content);
    if (!messageHasCommand)
        return;
    let commandName = message.content
        .match(singleCommandRegex)[0]
        .toLowerCase()
        .replace(prefix, '');
    const command = ((_b = client.commands) === null || _b === void 0 ? void 0 : _b.get(commandName)) ||
        ((_c = client.commands) === null || _c === void 0 ? void 0 : _c.find((cmd) => cmd.aliases && cmd.aliases.includes(commandName)));
    message.content = message.content.replace(singleCommandRegex, '').trim();
    if (!command) {
        console.debug('[DEBUG] Command not present: ', commandName);
        return;
    }
    setupCooldown_1.setupCooldown(client, command, message);
}));
exports.setupOnMessage = setupOnMessage;
//# sourceMappingURL=setupOnMessage.js.map