"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.generateArchivePayload = void 0;
const generateArchiveInfo_1 = require("./commands/generateArchiveInfo");
const getUrls_1 = require("./commands/getUrls");
const generateArchivePayload = (message) => ({
    author: message.author,
    authorAvatar: message.author.displayAvatarURL(),
    authorURL: message.url,
    attachments: message.attachments,
    URLs: getUrls_1.getUrls(message.content),
    archiveTitle: generateArchiveInfo_1.generateArchiveTitle(message.content),
    archiveColor: generateArchiveInfo_1.generateArchiveColor()
});
exports.generateArchivePayload = generateArchivePayload;
//# sourceMappingURL=generateArchivePayload.js.map