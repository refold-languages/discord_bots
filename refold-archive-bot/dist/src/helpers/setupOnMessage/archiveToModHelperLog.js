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
exports.archiveToModHelperLog = void 0;
const config_json_1 = __importDefault(require("../../../config.json"));
const copyMessageToChannel_1 = require("../copyMessageToChannel");
const generateArchivePayload_1 = require("../generateArchivePayload");
const removeEmojiFromMessage_1 = require("./removeEmojiFromMessage");
const archiveToModHelperLog = (client, messageReaction, reactingUserId) => __awaiter(void 0, void 0, void 0, function* () {
    const archiveToModHelperLogEmoji = '🪱';
    const helperFlagChannel = yield client.channels.fetch(process.env.HELPER_FLAG_CHANNEL_ID || config_json_1.default.helperFlagChannelId);
    const { message } = messageReaction;
    const archivePayload = generateArchivePayload_1.generateArchivePayload(message);
    yield copyMessageToChannel_1.copyMessageToChannel(message, helperFlagChannel, archivePayload, true);
    removeEmojiFromMessage_1.getEmojiToRemove(messageReaction, archiveToModHelperLogEmoji);
    yield removeEmojiFromMessage_1.removeEmojiFromMessage(messageReaction, reactingUserId, archiveToModHelperLogEmoji);
    return;
});
exports.archiveToModHelperLog = archiveToModHelperLog;
//# sourceMappingURL=archiveToModHelperLog.js.map