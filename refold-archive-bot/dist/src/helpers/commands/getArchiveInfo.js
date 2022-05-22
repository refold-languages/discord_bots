"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.getArchiveInfo = exports.getArchiveId = exports.getArchiveName = exports.getArchiveChannel = void 0;
const getArchiveChannel = (archive, message) => {
    return archive.channels.some((channel) => channel['from'] === message.channel.name);
};
exports.getArchiveChannel = getArchiveChannel;
const getArchiveName = (archive, message) => {
    const messageChannel = message.channel;
    return archive.channels.find((channel) => channel['from'] === messageChannel.name);
};
exports.getArchiveName = getArchiveName;
const getArchiveId = (archiveName, message) => {
    var _a, _b, _c;
    return (_c = (_b = (_a = message === null || message === void 0 ? void 0 : message.guild) === null || _a === void 0 ? void 0 : _a.channels) === null || _b === void 0 ? void 0 : _b.cache) === null || _c === void 0 ? void 0 : _c.find((channel) => channel.name === archiveName.to).id;
};
exports.getArchiveId = getArchiveId;
const getArchiveInfo = (archive, message) => {
    const archiveChannel = exports.getArchiveChannel(archive, message);
    const archiveName = exports.getArchiveName(archive, message);
    if (archiveName) {
        const archiveId = exports.getArchiveId(archiveName, message);
        return { archiveChannel, archiveName, archiveId };
    }
    return { archiveChannel, archiveName };
};
exports.getArchiveInfo = getArchiveInfo;
//# sourceMappingURL=getArchiveInfo.js.map