import { wordList } from '../../wordList';

interface MatchPayloadInterface {
  matchedWord: string | undefined;
  listType: string | null;
}

export const isProfane = (message: string) => {
  let matchPayload: MatchPayloadInterface | null = null;

  for (let word of wordList) {
    const wordExp = new RegExp(
      `\\b${word.text.replace(/(\W)/g, '\\$1')}\\b`,
      'gi'
    );

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
