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
exports.sendToArchiveChannel = void 0;
const config_json_1 = __importDefault(require("../../../config.json"));
const copyMessageToChannel_1 = require("../copyMessageToChannel");
const generateArchivePayload_1 = require("../generateArchivePayload");
const cleanContent_1 = require("./cleanContent");
const findArchiveMessage_1 = require("./findArchiveMessage");
const getArchiveInfo_1 = require("./getArchiveInfo");
const archive = config_json_1.default.command.archive;
const prefix = config_json_1.default.command.prefix;
const sendToArchiveChannel = (client, currentMessage, commandType, aliases) => __awaiter(void 0, void 0, void 0, function* () {
    let commandList;
    let cleanedContent = '';
    let message = commandType === 'command'
        ? currentMessage
        : currentMessage.message;
    const content = message.content.trim();
    if (commandType === 'command') {
        commandList = cleanContent_1.getCommandList(aliases, 'archive');
        cleanedContent = cleanContent_1.cleanContent(commandList, content, prefix);
    }
    const { archiveChannel, archiveName, archiveId } = getArchiveInfo_1.getArchiveInfo(archive, message);
    if (!archiveName && commandType === 'command') {
        return message.reply('That command is not available in this channel');
    }
    const messageChannel = message.channel;
    if (!archiveChannel) {
        console.debug(`[DEBUG] Channel name ${messageChannel.name} is NOT included in ${archive.channels}`);
        return;
    }
    if (!archiveId) {
        console.log(`[DEBUG] Unable to find ID for channel ${archiveName}`);
        return;
    }
    const targetArchiveChannel = client.channels.cache.get(archiveId);
    const archiveMessages = yield findArchiveMessage_1.getArchiveMessages(targetArchiveChannel);
    const duplicateArchiveMessage = findArchiveMessage_1.findDuplicateArchiveMessage(archiveMessages, commandType === 'command' ? cleanedContent : content);
    if (duplicateArchiveMessage)
        return;
    const archivePayload = generateArchivePayload_1.generateArchivePayload(message);
    return copyMessageToChannel_1.copyMessageToChannel(commandType === 'command' ? cleanedContent : content, targetArchiveChannel, archivePayload);
});
exports.sendToArchiveChannel = sendToArchiveChannel;
//# sourceMappingURL=sendToArchiveChannel.js.map