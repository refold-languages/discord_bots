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
exports.setupOnMessageReactionAdd = exports.aliases = exports.name = void 0;
const config_json_1 = __importDefault(require("../config.json"));
const sendToArchiveChannel_1 = require("./helpers/commands/sendToArchiveChannel");
const determineIsExcludedChannel_1 = require("./helpers/determineIsExcludedChannel");
const archiveToModHelperLog_1 = require("./helpers/setupOnMessage/archiveToModHelperLog");
const archiveToQuestionLog_1 = require("./helpers/setupOnMessage/archiveToQuestionLog");
const emojis = config_json_1.default.command.emojis;
const getRemainingEmoji = (messageReaction) => emojis.filter((emoji) => {
    return emoji !== messageReaction.emoji.name;
});
const getCacheEmoji = (messageReaction, remainingEmoji) => messageReaction.message.reactions.cache.some((_, reactionEmoji) => {
    return remainingEmoji.includes(reactionEmoji);
});
const determineEmojiPermissions = (messageReaction, reactingUser) => {
    var _a, _b;
    const currentUserInfo = (_b = (_a = messageReaction === null || messageReaction === void 0 ? void 0 : messageReaction.message) === null || _a === void 0 ? void 0 : _a.guild) === null || _b === void 0 ? void 0 : _b.members.cache.get(reactingUser.id);
    const hasEmojiPermissions = currentUserInfo === null || currentUserInfo === void 0 ? void 0 : currentUserInfo.roles.cache.find((role) => role.name === 'Helper' || role.name === 'Mod' || role.name === 'Admin');
    return hasEmojiPermissions;
};
exports.name = 'archive';
exports.aliases = ['share', 'save', 's'];
const setupOnMessageReactionAdd = (client) => __awaiter(void 0, void 0, void 0, function* () {
    return client.on('messageReactionAdd', (messageReaction, reactingUser) => __awaiter(void 0, void 0, void 0, function* () {
        const isBot = messageReaction.message.author.bot;
        if (isBot)
            return;
        const logMessageEmoji = '🪱';
        const paperclipEmoji = '📎';
        const questionMarkEmoji = '❓';
        const commandPath = config_json_1.default.emojiCommands[messageReaction.emoji.name];
        if (commandPath) {
            const hasExcludedChannels = commandPath.excludedChannels.length >= 1;
            if (hasExcludedChannels) {
                const isExcludedChannel = determineIsExcludedChannel_1.determineIsExcludeChannel(messageReaction.emoji.name, messageReaction.message, true);
                if (isExcludedChannel)
                    return;
            }
        }
        const hasLogMessageEmoji = messageReaction.emoji.name === logMessageEmoji;
        const hasPaperclipEmoji = messageReaction.emoji.name === paperclipEmoji;
        const hasQuestionMarkEmoji = messageReaction.emoji.name === questionMarkEmoji;
        const hasEmojiOnList = paperclipEmoji || logMessageEmoji;
        if (!hasEmojiOnList) {
            console.log(`[DEBUG] Reaction emoji ${messageReaction.emoji.name} is NOT in emoji list ${emojis}`);
            return;
        }
        let hasTooManyEmojis = false;
        const emojiName = messageReaction.message.reactions.cache.get(messageReaction.emoji.name);
        if (emojiName) {
            hasTooManyEmojis = emojiName.count > 1;
        }
        if (hasTooManyEmojis) {
            console.log(`[DEBUG] ${messageReaction.emoji.name} count is greater than 1`);
            return;
        }
        const remainingEmoji = getRemainingEmoji(messageReaction);
        const reactionCacheHasEmoji = getCacheEmoji(messageReaction, remainingEmoji);
        if (reactionCacheHasEmoji) {
            console.log('[DEBUG] Other emojis are already present');
            return;
        }
        const hasEmojiPermissions = determineEmojiPermissions(messageReaction, reactingUser);
        if (hasEmojiPermissions) {
            if (hasLogMessageEmoji) {
                return yield archiveToModHelperLog_1.archiveToModHelperLog(client, messageReaction, reactingUser.id);
            }
            else if (hasPaperclipEmoji) {
                return yield sendToArchiveChannel_1.sendToArchiveChannel(client, messageReaction, 'emoji');
            }
            else if (hasQuestionMarkEmoji) {
                return yield archiveToQuestionLog_1.archiveToQuestionLog(client, messageReaction);
            }
        }
        return;
    }));
});
exports.setupOnMessageReactionAdd = setupOnMessageReactionAdd;
//# sourceMappingURL=setupMessageReactionAdd.js.map