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
exports.removeEmojiFromMessage = exports.getEmojiToRemove = void 0;
const getEmojiToRemove = (messageReaction, emoji) => messageReaction.message.reactions.cache.find((reaction) => reaction.emoji.name === emoji);
exports.getEmojiToRemove = getEmojiToRemove;
const removeEmojiFromMessage = (messageReaction, reactingUserId, emoji) => __awaiter(void 0, void 0, void 0, function* () {
    const emojiToRemove = exports.getEmojiToRemove(messageReaction, emoji);
    yield (emojiToRemove === null || emojiToRemove === void 0 ? void 0 : emojiToRemove.users.remove(reactingUserId));
    return;
});
exports.removeEmojiFromMessage = removeEmojiFromMessage;
//# sourceMappingURL=removeEmojiFromMessage.js.map