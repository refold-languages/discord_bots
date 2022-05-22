export const getCommandList = (aliases: string[], name: string): string[] => {
  let commandList: string[] = Array.from(aliases);
  commandList.unshift(name);
  return commandList;
};

export const cleanContent = (
  commandList: string[],
  messageContent: string,
  prefix?: string
): string => {
  let cleanedMessage: string = '';
  for (let command of commandList) {
    cleanedMessage = messageContent.replace(prefix + command, '');
  }
  return cleanedMessage;
};
