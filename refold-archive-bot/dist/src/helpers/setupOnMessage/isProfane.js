"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.isProfane = void 0;
const wordList_1 = require("../../wordList");
const isProfane = (message) => {
    let matchPayload = null;
    for (let word of wordList_1.wordList) {
        const wordExp = new RegExp(`\\b${word.text.replace(/(\W)/g, '\\$1')}\\b`, 'gi');
        let isMatch;
        switch (word.filterType) {
            case 'exact':
                isMatch = wordExp.test(message);
                break;
            case 'includes':
                isMatch = message.toLowerCase().includes(word.text.toLowerCase());
                break;
            default:
                isMatch = false;
                break;
        }
        if (isMatch) {
            matchPayload = { matchedWord: word.text, listType: word.listType };
            return matchPayload;
        }
        matchPayload = { matchedWord: undefined, listType: null };
    }
    return matchPayload;
};
exports.isProfane = isProfane;
//# sourceMappingURL=isProfane.js.map