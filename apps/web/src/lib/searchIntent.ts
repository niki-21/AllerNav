const CUISINE_INTENTS: Array<[RegExp, string]> = [
  [/\bsushi\b/i, "sushi restaurants"],
  [/\bbrunch\b/i, "brunch restaurants"],
  [/\bfrench\b/i, "French restaurants"],
  [/\bitalian\b/i, "Italian restaurants"],
  [/\bthai\b/i, "Thai restaurants"],
  [/\bindian\b/i, "Indian restaurants"],
  [/\bchinese\b/i, "Chinese restaurants"],
  [/\bjapanese\b/i, "Japanese restaurants"],
  [/\bkorean\b/i, "Korean restaurants"],
  [/\bmexican\b/i, "Mexican restaurants"],
  [/\bmediterranean\b/i, "Mediterranean restaurants"],
  [/\bmiddle eastern\b/i, "Middle Eastern restaurants"],
  [/\bvegan\b/i, "Vegan restaurants"],
  [/\bvegetarian\b/i, "Vegetarian restaurants"],
];

const GENERIC_SEARCH_QUERIES = new Set(["", "restaurant", "restaurants", "nearby restaurants"]);

function locationSuffix(question: string): string {
  const match = question.match(/\b(?:going to|near|around)\s+([A-Z][\w'-]*(?:\s+[A-Z][\w'-]*){0,3})/);
  return match?.[1] ? ` near ${match[1].replace(/\s+(?:I|we)$/i, "").trim()}` : "";
}

export function extractSearchIntent(question: string, currentSearchQuery: string): string {
  const normalizedQuestion = question.trim();
  const normalizedCurrentQuery = currentSearchQuery.trim();
  if (normalizedCurrentQuery && !GENERIC_SEARCH_QUERIES.has(normalizedCurrentQuery.toLowerCase())) {
    return normalizedCurrentQuery;
  }
  const location = locationSuffix(normalizedQuestion);

  const cafeMatch = normalizedQuestion.match(/\b((?:cute|cozy|quiet|cheap)\s+)?caf(?:e|é)s?\b/i);
  if (cafeMatch) {
    return `${cafeMatch[1]?.trim().toLowerCase() ? `${cafeMatch[1].trim().toLowerCase()} ` : ""}cafes${location}`;
  }

  const burgerMatch = normalizedQuestion.match(/\b((?:cheap|casual|quick)\s+)?burger(?:\s+restaurants?)?\b/i);
  if (burgerMatch) {
    const modifier = burgerMatch[1]?.trim().toLowerCase();
    return `${modifier ? `${modifier} ` : ""}burger restaurants${location}`;
  }

  for (const [pattern, query] of CUISINE_INTENTS) {
    if (pattern.test(normalizedQuestion)) {
      return `${query}${location}`;
    }
  }

  const explicitRestaurant = normalizedQuestion.match(
    /\b([a-z][a-z\s'-]{1,30}?)\s+restaurants?\b/i,
  );
  if (explicitRestaurant) {
    const descriptor = explicitRestaurant[1]
      .replace(/^(?:i want|find|show me|suggest|a|an|some)\s+/i, "")
      .trim();
    if (descriptor && !/^(?:nearby|the|good)$/i.test(descriptor)) {
      return `${descriptor.toLowerCase()} restaurants${location}`;
    }
  }

  return currentSearchQuery.trim() || "restaurants";
}
