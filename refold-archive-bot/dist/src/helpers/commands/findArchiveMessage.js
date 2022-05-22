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
Object.defineProperty(exports, "__esModule", { value: true });
exports.findDuplicateArchiveMessage = exports.getArchiveMessages = void 0;
const getArchiveMessages = (archiveChannel) => __awaiter(void 0, void 0, void 0, function* () {
    const messages = yield archiveChannel.messages.fetch({ limit: 100 });
    const archiveMessages = messages.map((message) => message.embeds).flat();
    return archiveMessages;
});
exports.getArchiveMessages = getArchiveMessages;
const findDuplicateArchiveMessage = (messageEmbeds, cleanedContent) => {
    let messageExists = null;
    for (let embed of messageEmbeds) {
        if (embed.title === cleanedContent) {
            messageExists = true;
        }
    }
    return messageExists;
};
exports.findDuplicateArchiveMessage = findDuplicateArchiveMessage;
//# sourceMappingURL=findArchiveMessage.js.map