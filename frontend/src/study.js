export function getStudyItems(response) {
  if (!Array.isArray(response?.items)) {
    throw new Error("Unexpected study response");
  }

  return response.items;
}

export function isCorrectAnswer(selectedIndex, answerIndex) {
  return Number.isInteger(selectedIndex) && selectedIndex === answerIndex;
}