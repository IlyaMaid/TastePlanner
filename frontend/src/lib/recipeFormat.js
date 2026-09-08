function formatIngredientQuantity(ingredient) {
  const quantity =
    ingredient.quantity != null && ingredient.unit === "g"
      ? `${Number(ingredient.quantity).toLocaleString("ru-RU", {
          maximumFractionDigits: 0,
        })} г`
      : null;

  return quantity;
}

function formatIngredientListItem(ingredient) {
  const name = ingredient.name_ru || ingredient.raw_text;
  const quantity = formatIngredientQuantity(ingredient);

  return `${name}${quantity ? ` - ${quantity}` : ""}`;
}

function formatProductDetail(ingredient) {
  const name = ingredient.name_ru || ingredient.raw_text;
  const quantity = formatIngredientQuantity(ingredient);
  const calories =
    ingredient.calories_total != null
      ? `${Math.round(Number(ingredient.calories_total))} ккал`
      : ingredient.calories_per_100g != null
        ? `${Math.round(Number(ingredient.calories_per_100g))} ккал/100 г`
        : "ккал нет";
  const price =
    ingredient.estimated_cost_rub != null
      ? `≈ ${Number(ingredient.estimated_cost_rub).toLocaleString("ru-RU", {
          maximumFractionDigits: 1,
        })} ₽`
      : ingredient.price_per_100g_rub != null
        ? `${Number(ingredient.price_per_100g_rub).toLocaleString("ru-RU", {
            maximumFractionDigits: 1,
          })} ₽/100 г`
        : "цены нет";

  return `${name}${quantity ? `, ${quantity}` : ""}: ${calories}, ${price}`;
}

export function formatRecipe(recipe) {
  const cleanedDescription =
    recipe.source === "povarenok" && typeof recipe.description === "string"
      ? recipe.description.replace(/^Источник:\s*https?:\/\/\S+\s*$/i, "").trim()
      : recipe.description;
  const ingredientDetails = Array.isArray(recipe.ingredient_details)
    ? recipe.ingredient_details
    : [];

  return {
    ...recipe,
    description:
      cleanedDescription || "Описание для этого рецепта пока не добавлено.",
    calories:
      typeof recipe.calories === "number" ? Math.round(recipe.calories) : null,
    metaLabel:
      recipe.total_minutes != null
        ? `${recipe.total_minutes} мин`
        : "Время не указано",
    predictedRating:
      typeof recipe.predicted_rating === "number"
        ? recipe.predicted_rating.toFixed(2)
        : null,
    contentSimilarity:
      typeof recipe.content_similarity === "number"
        ? recipe.content_similarity
        : null,
    predictedScore:
      typeof recipe.predicted_score === "number"
        ? recipe.predicted_score
        : null,
    finalScore:
      typeof recipe.final_score === "number" ? recipe.final_score : null,
    estimatedCostRub:
      typeof recipe.estimated_cost_rub === "number"
        ? recipe.estimated_cost_rub
        : null,
    ingredientsPreview:
      ingredientDetails.length > 0
        ? ingredientDetails.slice(0, 4).map(formatIngredientListItem)
        : Array.isArray(recipe.ingredients)
          ? recipe.ingredients.slice(0, 4)
          : [],
    ingredientsList:
      ingredientDetails.length > 0
        ? ingredientDetails.map(formatIngredientListItem)
        : Array.isArray(recipe.ingredients)
          ? recipe.ingredients
          : [],
    cookingSteps: Array.isArray(recipe.cooking_steps) ? recipe.cooking_steps : [],
    cookingStepsPreview: Array.isArray(recipe.cooking_steps)
      ? recipe.cooking_steps.slice(0, 4)
      : [],
    productDetails: ingredientDetails.map(formatProductDetail),
    productDetailsPreview: ingredientDetails.slice(0, 4).map(formatProductDetail),
    recommendationReasons: Array.isArray(recipe.recommendation_reasons)
      ? recipe.recommendation_reasons
      : [],
  };
}
