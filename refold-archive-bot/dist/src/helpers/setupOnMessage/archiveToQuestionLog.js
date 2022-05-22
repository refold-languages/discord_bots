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
exports.archiveToQuestionLog = void 0;
const config_json_1 = __importDefault(require("../../../config.json"));
const copyMessageToChannel_1 = require("../copyMessageToChannel");
const generateArchivePayload_1 = require("../generateArchivePayload");
const archiveToQuestionLog = (client, messageReaction) => __awaiter(void 0, void 0, void 0, function* () {
    const questionLogChannel = yield client.channels.fetch(process.env.QUESTION_LOG_CHANNEL_ID || config_json_1.default.questionLogChannelId);
    const { message } = messageReaction;
    const archivePayload = generateArchivePayload_1.generateArchivePayload(message);
    yield copyMessageToChannel_1.copyMessageToChannel(message, questionLogChannel, archivePayload);
});
exports.archiveToQuestionLog = archiveToQuestionLog;
//# sourceMappingURL=archiveToQuestionLog.js.map