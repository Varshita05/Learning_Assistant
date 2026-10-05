import assert from "node:assert/strict";
import test from "node:test";
import { getStudyItems, isCorrectAnswer } from "../src/study.js";

test("reads items from the backend study response", () => {
  const items = [{ q: "Question", options: ["A", "B", "C", "D"], answer_index: 1 }];

  assert.deepEqual(getStudyItems({ items }), items);
});

test("rejects a response without the documented items array", () => {
  assert.throws(() => getStudyItems({ questions: [] }), /Unexpected study response/);
});

test("scores quiz answers by option index", () => {
  assert.equal(isCorrectAnswer(2, 2), true);
  assert.equal(isCorrectAnswer(1, 2), false);
  assert.equal(isCorrectAnswer(null, 2), false);
});