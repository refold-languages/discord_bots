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
exports.run = exports.description = exports.cooldown = exports.emojis = exports.aliases = exports.name = void 0;
const config_json_1 = __importDefault(require("../../config.json"));
const cleanContent_1 = require("../helpers/commands/cleanContent");
const copyMessageToChannel_1 = require("../helpers/copyMessageToChannel");
const generateArchivePayload_1 = require("../helpers/generateArchivePayload");
const determineIsExcludedChannel_1 = require("./../helpers/determineIsExcludedChannel");
exports.name = 'question';
exports.aliases = ['question', 'q'];
exports.emojis = ['❓'];
exports.cooldown = 10;
exports.description = 'Clones a message and makes a custom embed in another channel';
const run = (client, message) => __awaiter(void 0, void 0, void 0, function* () {
    const hasExcludedChannels = config_json_1.default.questionCommand.excludedChannels.length >= 1;
    if (hasExcludedChannels) {
        const isExcludedChannel = determineIsExcludedChannel_1.determineIsExcludeChannel('questionCommand', message);
        if (isExcludedChannel)
            return;
    }
    const questionLogChannel = yield client.channels.fetch(process.env.QUESTION_LOG_CHANNEL_ID || config_json_1.default.questionLogChannelId);
    if (!questionLogChannel) {
        console.error(`Could not find question log channel with ID of ${process.env.QUESTION_LOG_CHANNEL_ID || config_json_1.default.questionLogChannelId}`);
        return;
    }
    let content = message.content.trim();
    const commandList = cleanContent_1.getCommandList(exports.aliases, exports.name);
    const cleanedContent = cleanContent_1.cleanContent(commandList, content);
    const archivePayload = generateArchivePayload_1.generateArchivePayload(message);
    return copyMessageToChannel_1.copyMessageToChannel(cleanedContent, questionLogChannel, archivePayload);
});
exports.run = run;
//# sourceMappingURL=question.js.map